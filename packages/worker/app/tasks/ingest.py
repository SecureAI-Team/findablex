"""Data ingestion tasks."""
import asyncio
import csv
import json
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select

from app.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.ingest.parse_import")
def parse_import(
    self,
    run_id: str,
    input_data: str,
    input_format: str,
) -> Dict[str, Any]:
    """Parse imported data (CSV, JSON, or paste) and save to database."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_parse_import(run_id, input_data, input_format))
        return result
    finally:
        loop.close()


async def _parse_import(run_id: str, input_data: str, input_format: str) -> Dict[str, Any]:
    """Async implementation of import parsing."""
    from app.db import get_db_session
    from app.models import Run, QueryItem
    
    try:
        if input_format == "csv":
            items = parse_csv(input_data)
        elif input_format == "json":
            items = parse_json(input_data)
        else:  # paste
            items = parse_paste(input_data)
        
        if not items:
            return {
                "run_id": run_id,
                "status": "error",
                "error": "No valid items found in input data",
            }
        
        # Save items to database
        async with get_db_session() as db:
            run_uuid = UUID(run_id)
            
            # Get run
            run_result = await db.execute(
                select(Run).where(Run.id == run_uuid)
            )
            run = run_result.scalar_one_or_none()
            
            if not run:
                return {"error": f"Run {run_id} not found"}
            
            # Update run status
            run.status = "processing"
            run.started_at = datetime.now(timezone.utc)
            run.total_queries = len(items)
            
            # Create query items
            for item in items:
                query_item = QueryItem(
                    run_id=run_uuid,
                    query_text=item.get("query_text", ""),
                    response_text=item.get("response_text", ""),
                    engine=item.get("engine", "import"),
                    metadata_json={
                        "citations": item.get("citations", []),
                        **item.get("metadata", {}),
                    },
                )
                db.add(query_item)
            
            await db.commit()
        
        # Trigger extraction pipeline
        from app.tasks.extract import extract_citations
        extract_citations.delay(run_id)
        
        return {
            "run_id": run_id,
            "status": "success",
            "items_count": len(items),
            "total": len(items),
        }
    except Exception as e:
        # Update run with error
        try:
            async with get_db_session() as db:
                run_uuid = UUID(run_id)
                run_result = await db.execute(
                    select(Run).where(Run.id == run_uuid)
                )
                run = run_result.scalar_one_or_none()
                if run:
                    run.status = "failed"
                    run.error_message = str(e)
                    await db.commit()
        except Exception:
            pass
        
        return {
            "run_id": run_id,
            "status": "error",
            "error": str(e),
        }


def parse_csv(data: str) -> List[Dict[str, Any]]:
    """Parse CSV data."""
    reader = csv.DictReader(StringIO(data))
    items = []
    for row in reader:
        items.append({
            "query_text": row.get("query", row.get("question", "")),
            "response_text": row.get("response", row.get("answer", "")),
            "citations": [],
            "metadata": {k: v for k, v in row.items() if k not in ("query", "question", "response", "answer")},
        })
    return items


def parse_json(data: str) -> List[Dict[str, Any]]:
    """Parse JSON data."""
    parsed = json.loads(data)
    if isinstance(parsed, list):
        return parsed
    elif isinstance(parsed, dict) and "items" in parsed:
        return parsed["items"]
    else:
        return [parsed]


def parse_paste(data: str) -> List[Dict[str, Any]]:
    """Parse pasted text data."""
    # Split by double newlines to separate Q&A pairs
    blocks = data.strip().split("\n\n")
    items = []
    
    current_query = None
    current_response = []
    
    for block in blocks:
        lines = block.strip().split("\n")
        if not lines:
            continue
        
        # Check if this is a query line
        first_line = lines[0].strip()
        if first_line.startswith("Q:") or first_line.startswith("Query:") or first_line.startswith("问:"):
            # Save previous item
            if current_query:
                items.append({
                    "query_text": current_query,
                    "response_text": "\n".join(current_response),
                    "citations": [],
                    "metadata": {},
                })
            
            # Start new item
            current_query = first_line.split(":", 1)[1].strip() if ":" in first_line else first_line
            current_response = lines[1:] if len(lines) > 1 else []
        else:
            # This is response content
            if current_query:
                current_response.extend(lines)
    
    # Save last item
    if current_query:
        items.append({
            "query_text": current_query,
            "response_text": "\n".join(current_response),
            "citations": [],
            "metadata": {},
        })
    
    return items


@celery_app.task(bind=True, name="app.tasks.ingest.process_run")
def process_run(self, run_id: str) -> Dict[str, Any]:
    """
    Process a complete run through the pipeline.
    
    This orchestrates the entire processing pipeline:
    1. Extract citations from query items
    2. Calculate metrics
    3. Generate report
    
    Each step triggers the next when complete.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_start_processing(run_id))
        return result
    finally:
        loop.close()


async def _start_processing(run_id: str) -> Dict[str, Any]:
    """Start processing pipeline for a run."""
    from app.db import get_db_session
    from app.models import Run
    
    async with get_db_session() as db:
        run_uuid = UUID(run_id)
        
        # Get run
        run_result = await db.execute(
            select(Run).where(Run.id == run_uuid)
        )
        run = run_result.scalar_one_or_none()
        
        if not run:
            return {"error": f"Run {run_id} not found"}
        
        # Update status
        run.status = "processing"
        run.started_at = datetime.now(timezone.utc)
        await db.commit()
    
    # Start extraction (which will chain to scoring and reporting)
    from app.tasks.extract import extract_citations
    extract_citations.delay(run_id)
    
    return {
        "run_id": run_id,
        "status": "processing",
        "message": "Pipeline started",
    }


@celery_app.task(bind=True, name="app.tasks.ingest.handle_pipeline_error")
def handle_pipeline_error(self, run_id: str, error_message: str) -> Dict[str, Any]:
    """Handle pipeline error and update run status."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_handle_error(run_id, error_message))
        return result
    finally:
        loop.close()


async def _handle_error(run_id: str, error_message: str) -> Dict[str, Any]:
    """Mark run as failed."""
    from app.db import get_db_session
    from app.models import Run
    
    async with get_db_session() as db:
        run_uuid = UUID(run_id)
        
        run_result = await db.execute(
            select(Run).where(Run.id == run_uuid)
        )
        run = run_result.scalar_one_or_none()
        
        if run:
            run.status = "failed"
            run.error_message = error_message
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
    
    return {
        "run_id": run_id,
        "status": "failed",
        "error": error_message,
    }
