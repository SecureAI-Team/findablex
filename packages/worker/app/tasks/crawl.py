"""Web crawling tasks (restricted to researchers)."""
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select

from app.celery_app import celery_app
from app.config import settings

import redis


def get_redis_client():
    """Get Redis client for task communication."""
    return redis.from_url(settings.redis_url)


@celery_app.task(bind=True, name="app.tasks.crawl.process_crawl_task")
def process_crawl_task(self, task_id: str, run_id: str, engine: str, queries: List[Dict]) -> Dict[str, Any]:
    """
    Queue a crawl task for the crawler service.
    
    The crawler service polls Redis for tasks and processes them.
    """
    r = get_redis_client()
    
    # Queue task for crawler
    task_data = {
        "id": task_id,
        "run_id": run_id,
        "engine": engine,
        "queries": queries,
        "config": {
            "take_screenshot": True,
        },
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    
    r.rpush("crawler:tasks", json.dumps(task_data))
    
    return {
        "task_id": task_id,
        "run_id": run_id,
        "status": "queued",
        "message": "Task queued for crawler service",
    }


@celery_app.task(bind=True, name="app.tasks.crawl.consume_crawl_results")
def consume_crawl_results(self, task_id: str, run_id: str) -> Dict[str, Any]:
    """
    Consume crawl results from Redis and process them.
    
    This task polls for results from the crawler service and saves them to DB.
    """
    r = get_redis_client()
    results_key = f"crawler:results:{task_id}"
    status_key = f"crawler:status:{task_id}"
    
    # Check if task is completed
    status = r.get(status_key)
    if status and status.decode() == "completed":
        # Get all results
        results = []
        while True:
            result_data = r.lpop(results_key)
            if not result_data:
                break
            results.append(json.loads(result_data))
        
        # Save results to database
        if results:
            save_crawl_results_to_db.delay(run_id, results)
        
        # Clean up Redis keys
        r.delete(results_key)
        r.delete(status_key)
        
        return {
            "task_id": task_id,
            "run_id": run_id,
            "status": "completed",
            "results_count": len(results),
        }
    
    # Task not completed yet, retry later
    self.retry(countdown=5, max_retries=120)  # Retry for up to 10 minutes


@celery_app.task(bind=True, name="app.tasks.crawl.save_crawl_results_to_db")
def save_crawl_results_to_db(self, run_id: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Save crawl results to database."""
    # Run async code in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_save_crawl_results(run_id, results))
        return result
    finally:
        loop.close()


async def _save_crawl_results(run_id: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Async implementation of saving crawl results."""
    from app.db import get_db_session
    from app.models import Run, QueryItem
    
    async with get_db_session() as db:
        # Get the run
        run_uuid = UUID(run_id)
        run_result = await db.execute(select(Run).where(Run.id == run_uuid))
        run = run_result.scalar_one_or_none()
        
        if not run:
            return {"error": f"Run {run_id} not found"}
        
        # Update run status to processing
        run.status = "processing"
        run.started_at = datetime.now(timezone.utc)
        
        # Save each query result
        query_items_created = 0
        for result in results:
            if result.get("error"):
                continue
            
            query_item = QueryItem(
                run_id=run_uuid,
                query_text=result.get("query", ""),
                response_text=result.get("response_text", ""),
                engine=result.get("engine", ""),
                metadata_json={
                    "citations": result.get("citations", []),
                    "screenshot_path": result.get("screenshot_path", ""),
                    "crawled_at": result.get("crawled_at", ""),
                },
            )
            db.add(query_item)
            query_items_created += 1
        
        run.total_queries = query_items_created
        await db.commit()
        
        # Trigger extraction pipeline
        from app.tasks.extract import extract_citations
        extract_citations.delay(run_id)
        
        return {
            "run_id": run_id,
            "status": "saved",
            "query_items_created": query_items_created,
        }


@celery_app.task(bind=True, name="app.tasks.crawl.crawl_single_query")
def crawl_single_query(
    self,
    task_id: str,
    query_id: str,
    query_text: str,
    engine: str,
) -> Dict[str, Any]:
    """Crawl a single query on a specific engine."""
    r = get_redis_client()
    
    # Queue single query for crawler
    task_data = {
        "id": task_id,
        "engine": engine,
        "queries": [{"query_id": query_id, "query_text": query_text}],
        "config": {"take_screenshot": True},
    }
    
    r.rpush("crawler:tasks", json.dumps(task_data))
    
    return {
        "task_id": task_id,
        "query_id": query_id,
        "engine": engine,
        "status": "queued",
    }
