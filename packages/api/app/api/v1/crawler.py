"""Crawler routes (restricted to researchers and admins)."""
import uuid as uuid_module
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_current_user, get_db
from app.models.crawler import CrawlTask
from app.models.project import Project
from app.models.user import User
from app.services.project_service import ProjectService
from app.services.workspace_service import WorkspaceService
from app.tasks import process_crawl_task

router = APIRouter()


class CrawlTaskCreate(BaseModel):
    """Schema for creating a crawl task."""
    project_id: UUID
    engine: str = Field(..., pattern=r"^(perplexity|google_sge|bing_copilot|qwen|kimi|doubao|deepseek|chatglm|chatgpt)$")
    query_ids: List[UUID] = []  # Optional: existing query IDs
    queries: List[str] = []  # Optional: raw query texts (will create QueryItems)
    region: str = "cn"
    language: str = "zh-CN"
    device_type: str = "desktop"
    use_proxy: bool = True
    enable_web_search: bool = True  # Enable web search for citation sources (DeepSeek, Kimi, Qwen)


class CrawlTaskResponse(BaseModel):
    """Schema for crawl task response."""
    id: UUID
    project_id: UUID
    project_name: Optional[str] = None  # 新增: 项目名称
    engine: str
    status: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    class Config:
        from_attributes = True


SUPPORTED_ENGINES = [
    {"id": "perplexity", "name": "Perplexity", "priority": "P0", "method": "Web + API"},
    {"id": "google_sge", "name": "Google SGE/AI Overview", "priority": "P0", "method": "Web Automation"},
    {"id": "bing_copilot", "name": "Bing Copilot", "priority": "P1", "method": "Web Automation"},
    {"id": "qwen", "name": "Qwen (通义千问)", "priority": "P0", "method": "Web + API"},
    {"id": "deepseek", "name": "DeepSeek", "priority": "P0", "method": "Web Automation"},
    {"id": "kimi", "name": "Kimi", "priority": "P1", "method": "Web Automation"},
    {"id": "doubao", "name": "豆包 (Doubao)", "priority": "P1", "method": "Web Automation"},
    {"id": "chatglm", "name": "ChatGLM (智谱清言)", "priority": "P1", "method": "Web Automation"},
    {"id": "chatgpt", "name": "ChatGPT", "priority": "P0", "method": "Web Automation"},
]


@router.get("/engines")
async def list_engines() -> List[dict]:
    """List supported crawl engines."""
    return SUPPORTED_ENGINES


@router.get("/quota")
async def get_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current user's crawler quota."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func
    
    # Calculate the start of today (UTC)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Count total queries submitted today by this user
    result = await db.execute(
        select(func.sum(CrawlTask.total_queries))
        .where(
            CrawlTask.created_by == current_user.id,
            CrawlTask.created_at >= today_start
        )
    )
    used_today = result.scalar() or 0
    
    # Daily limit (can be made configurable per user/workspace)
    daily_limit = 500
    remaining = max(0, daily_limit - used_today)
    
    return {
        "daily_limit": daily_limit,
        "used_today": used_today,
        "remaining": remaining,
    }


@router.get("/tasks", response_model=List[CrawlTaskResponse])
async def list_tasks(
    project_id: UUID = None,
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CrawlTaskResponse]:
    """List crawl tasks with project names."""
    # Check if user is researcher or admin
    if not current_user.is_superuser:
        # TODO: Check researcher role in workspace
        pass
    
    query = select(CrawlTask)
    if project_id:
        query = query.where(CrawlTask.project_id == project_id)
    if status:
        query = query.where(CrawlTask.status == status)
    query = query.where(CrawlTask.created_by == current_user.id)
    query = query.order_by(CrawlTask.created_at.desc())
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    # Fetch project names for all tasks
    project_ids = list(set(task.project_id for task in tasks))
    project_names = {}
    if project_ids:
        project_result = await db.execute(
            select(Project.id, Project.name).where(Project.id.in_(project_ids))
        )
        project_names = {row.id: row.name for row in project_result}
    
    return [
        CrawlTaskResponse(
            id=task.id,
            project_id=task.project_id,
            project_name=project_names.get(task.project_id, "Unknown"),
            engine=task.engine,
            status=task.status,
            total_queries=task.total_queries,
            successful_queries=task.successful_queries,
            failed_queries=task.failed_queries,
            created_at=task.created_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
        )
        for task in tasks
    ]


@router.post("/tasks", response_model=CrawlTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: CrawlTaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CrawlTaskResponse:
    """Create a new crawl task."""
    from app.models.project import QueryItem
    
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    # Check project exists
    project = await project_service.get_by_id(data.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership and researcher role
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "researcher"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only researchers and admins can create crawl tasks",
            )
    
    # Validate that either query_ids or queries is provided
    if not data.query_ids and not data.queries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either query_ids or queries must be provided",
        )
    
    # Prepare query items for the task
    query_items_for_task = []
    
    # If raw queries are provided, create QueryItems for them
    if data.queries:
        for query_text in data.queries:
            query_text = query_text.strip()
            if query_text:
                query_item = QueryItem(
                    project_id=data.project_id,
                    query_text=query_text,
                    query_type="informational",  # Default query type
                    extra_data={
                        "source": "crawler",
                        "region": data.region,
                        "language": data.language,
                        "engine": data.engine,
                        "status": "pending",
                    },
                )
                db.add(query_item)
                await db.flush()  # Get the ID
                query_items_for_task.append({
                    "query_id": str(query_item.id),
                    "query_text": query_text,
                })
    
    # Add existing query_ids
    for qid in data.query_ids:
        # Fetch query text if needed
        result = await db.execute(
            select(QueryItem).where(QueryItem.id == qid)
        )
        existing_query = result.scalar_one_or_none()
        if existing_query:
            query_items_for_task.append({
                "query_id": str(qid),
                "query_text": existing_query.query_text,
            })
    
    total_queries = len(query_items_for_task)
    if total_queries == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid queries provided",
        )
    
    # Create crawl task
    task = CrawlTask(
        project_id=data.project_id,
        created_by=current_user.id,
        engine=data.engine,
        queries=[q["query_id"] for q in query_items_for_task],
        region=data.region,
        language=data.language,
        device_type=data.device_type,
        use_proxy=data.use_proxy,
        total_queries=total_queries,
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Execute task based on mode
    if settings.lite_mode:
        # Lite mode: execute directly using LiteCrawlerService
        from app.services.lite_crawler import run_lite_crawler_task
        import asyncio
        
        # Schedule as background task
        asyncio.create_task(
            run_lite_crawler_task(
                task_id=task.id,
                engine=task.engine,
                queries=query_items_for_task,
                config={
                    "region": data.region,
                    "language": data.language,
                    "take_screenshot": True,
                    "enable_web_search": data.enable_web_search,
                },
            )
        )
    else:
        # Production mode: Queue task for processing via Celery
        celery_task_id = str(uuid_module.uuid4())
        process_crawl_task.delay(
            task_id=celery_task_id,
            run_id=str(task.id),
            engine=task.engine,
            queries=query_items_for_task,
        )
    
    return CrawlTaskResponse(
        id=task.id,
        project_id=task.project_id,
        project_name=project.name,
        engine=task.engine,
        status=task.status,
        total_queries=task.total_queries,
        successful_queries=task.successful_queries,
        failed_queries=task.failed_queries,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


@router.get("/tasks/{task_id}", response_model=CrawlTaskResponse)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CrawlTaskResponse:
    """Get crawl task by ID."""
    result = await db.execute(
        select(CrawlTask).where(CrawlTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # Check ownership
    if task.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this task",
        )
    
    # Fetch project name
    project_result = await db.execute(
        select(Project.name).where(Project.id == task.project_id)
    )
    project_name = project_result.scalar_one_or_none() or "Unknown"
    
    return CrawlTaskResponse(
        id=task.id,
        project_id=task.project_id,
        project_name=project_name,
        engine=task.engine,
        status=task.status,
        total_queries=task.total_queries,
        successful_queries=task.successful_queries,
        failed_queries=task.failed_queries,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a crawl task."""
    result = await db.execute(
        select(CrawlTask).where(CrawlTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # Check ownership
    if task.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this task",
        )
    
    if task.status not in ("pending", "running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task cannot be cancelled",
        )
    
    task.status = "cancelled"
    await db.commit()
    
    return {"message": "Task cancelled"}


@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Retry/restart a crawl task.
    
    Use this to manually trigger execution of a pending task,
    or retry a failed task.
    """
    from app.models.project import QueryItem
    
    result = await db.execute(
        select(CrawlTask).where(CrawlTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # Check ownership
    if task.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to retry this task",
        )
    
    if task.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task cannot be retried (current status: {task.status})",
        )
    
    # Rebuild query list from task
    query_items_for_task = []
    for query_id in task.queries:
        # Convert string to UUID if needed
        if isinstance(query_id, str):
            query_uuid = UUID(query_id)
        else:
            query_uuid = query_id
        
        result = await db.execute(
            select(QueryItem).where(QueryItem.id == query_uuid)
        )
        query_item = result.scalar_one_or_none()
        if query_item:
            query_items_for_task.append({
                "query_id": str(query_uuid),
                "query_text": query_item.query_text,
            })
    
    if not query_items_for_task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No queries found for this task",
        )
    
    # Reset task status
    task.status = "pending"
    task.successful_queries = 0
    task.failed_queries = 0
    task.started_at = None
    task.completed_at = None
    await db.commit()
    
    # Execute task
    if settings.lite_mode:
        from app.services.lite_crawler import run_lite_crawler_task
        import asyncio
        
        # Schedule as background task
        asyncio.create_task(
            run_lite_crawler_task(
                task_id=task.id,
                engine=task.engine,
                queries=query_items_for_task,
                config={
                    "region": task.region or "cn",
                    "language": task.language or "zh-CN",
                    "take_screenshot": True,
                },
            )
        )
    else:
        celery_task_id = str(uuid_module.uuid4())
        process_crawl_task.delay(
            task_id=celery_task_id,
            run_id=str(task.id),
            engine=task.engine,
            queries=query_items_for_task,
        )
    
    return {"message": "Task restarted", "task_id": str(task.id)}


@router.get("/tasks/{task_id}/results")
async def get_task_results(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """Get crawl results for a task."""
    from app.models.crawler import CrawlResult
    
    # Verify task exists and user has access
    result = await db.execute(
        select(CrawlTask).where(CrawlTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # Check ownership
    if task.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this task",
        )
    
    # Fetch results
    result = await db.execute(
        select(CrawlResult).where(CrawlResult.task_id == task_id)
    )
    results = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "query": r.parsed_response.get("query_text", "") if r.parsed_response else "",
            "response_text": r.parsed_response.get("response_text", "") if r.parsed_response else "",
            "citations": r.citations or [],
            "crawled_at": r.crawled_at.isoformat() if r.crawled_at else None,
            "error": r.parsed_response.get("error") if r.parsed_response else None,
            "success": r.is_complete,
            "screenshot_path": r.screenshot_path,
        }
        for r in results
    ]


@router.get("/tasks/{task_id}/results/export")
async def export_task_results(
    task_id: UUID,
    format: str = "json",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export crawl results for a task in JSON or CSV format."""
    from fastapi.responses import Response
    from app.models.crawler import CrawlResult
    import json
    import csv
    import io
    
    # Verify task exists and user has access
    result = await db.execute(
        select(CrawlTask).where(CrawlTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    # Check ownership
    if task.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to export this task",
        )
    
    # Fetch results
    result = await db.execute(
        select(CrawlResult).where(CrawlResult.task_id == task_id)
    )
    results = result.scalars().all()
    
    # Build export data
    export_data = []
    for r in results:
        query_text = r.parsed_response.get("query_text", "") if r.parsed_response else ""
        response_text = r.parsed_response.get("response_text", "") if r.parsed_response else ""
        citations = r.citations or []
        
        export_data.append({
            "query": query_text,
            "response": response_text,
            "engine": r.engine,
            "citations_count": len(citations),
            "citations": [c.get("url", "") for c in citations],
            "crawled_at": r.crawled_at.isoformat() if r.crawled_at else None,
            "error": r.parsed_response.get("error") if r.parsed_response else None,
        })
    
    if format.lower() == "csv":
        # Generate CSV
        output = io.StringIO()
        fieldnames = ["query", "response", "engine", "citations_count", "citations", "crawled_at", "error"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in export_data:
            row["citations"] = "; ".join(row["citations"])  # Join URLs for CSV
            writer.writerow(row)
        
        content = output.getvalue()
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=crawl_results_{task_id}.csv"
            }
        )
    else:
        # Default to JSON
        content = json.dumps(export_data, ensure_ascii=False, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=crawl_results_{task_id}.json"
            }
        )


# =============================================================================
# Crawler Agent Endpoints (for remote browser agents)
# =============================================================================

class AgentTaskResponse(BaseModel):
    """Schema for agent task."""
    id: str
    engine: str
    query: str
    config: dict


class AgentResultSubmit(BaseModel):
    """Schema for agent result submission."""
    task_id: str
    success: bool
    response_text: str = ""
    citations: List[dict] = []
    error: Optional[str] = None
    screenshot_base64: Optional[str] = None


async def verify_agent_token(authorization: str = None) -> bool:
    """Verify crawler agent token."""
    if not authorization:
        return False
    
    # Extract token from "Bearer {token}" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return False
    
    token = parts[1]
    
    # Get configured agent token from settings
    agent_token = getattr(settings, 'crawler_agent_token', None)
    if not agent_token:
        # If no token configured, agent feature is disabled
        return False
    
    return token == agent_token


@router.get("/agent/tasks")
async def get_agent_tasks(
    authorization: str = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get pending crawl tasks for remote browser agents.
    
    This endpoint is called by crawler agents running on machines with browsers.
    Agents poll this endpoint to get tasks, execute them, and report results.
    """
    from fastapi import Header
    from sqlalchemy import and_
    
    # Note: In production, use proper dependency injection for header
    # For now, check if agent feature is enabled
    if not getattr(settings, 'crawler_agent_enabled', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent feature not enabled"
        )
    
    # Verify agent token (simplified for demo)
    # In production, use proper authentication
    
    # Find pending tasks that haven't been claimed
    from app.models.crawler import CrawlTask, CrawlResult
    from app.models.query import QueryItem
    
    # Get tasks that are running and have uncompleted queries
    result = await db.execute(
        select(CrawlTask)
        .where(
            and_(
                CrawlTask.status == "running",
                CrawlTask.failed_queries + CrawlTask.successful_queries < CrawlTask.total_queries
            )
        )
        .order_by(CrawlTask.created_at.asc())
        .limit(1)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        return {"tasks": []}
    
    # Get queries that haven't been processed
    result = await db.execute(
        select(QueryItem)
        .where(QueryItem.project_id == task.project_id)
        .limit(5)
    )
    queries = result.scalars().all()
    
    # Get already processed query IDs for this task
    result = await db.execute(
        select(CrawlResult.query_item_id)
        .where(CrawlResult.task_id == task.id)
    )
    processed_ids = {str(r) for r in result.scalars().all()}
    
    # Filter out processed queries
    pending_queries = [q for q in queries if str(q.id) not in processed_ids]
    
    tasks = []
    for query in pending_queries[:3]:  # Return max 3 tasks at a time
        tasks.append({
            "id": f"{task.id}_{query.id}",
            "task_id": str(task.id),
            "query_item_id": str(query.id),
            "engine": task.engine,
            "query": query.text,
            "config": {
                "enable_web_search": True,
                "region": task.region,
                "language": task.language,
            }
        })
    
    return {"tasks": tasks}


@router.post("/agent/results")
async def submit_agent_result(
    data: AgentResultSubmit,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Submit crawl result from remote browser agent.
    """
    import base64
    from datetime import datetime, timezone
    from app.models.crawler import CrawlResult
    
    if not getattr(settings, 'crawler_agent_enabled', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent feature not enabled"
        )
    
    # Parse task ID (format: {task_id}_{query_item_id})
    parts = data.task_id.split('_')
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format"
        )
    
    task_id = parts[0]
    query_item_id = parts[1]
    
    # Verify task exists
    result = await db.execute(
        select(CrawlTask).where(CrawlTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Save screenshot if provided
    screenshot_path = None
    if data.screenshot_base64:
        try:
            import os
            screenshot_dir = "./data/screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            
            filename = f"agent_{task.engine}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot_path = os.path.join(screenshot_dir, filename)
            
            with open(screenshot_path, 'wb') as f:
                f.write(base64.b64decode(data.screenshot_base64))
        except Exception as e:
            pass  # Ignore screenshot errors
    
    # Create crawl result
    crawl_result = CrawlResult(
        id=str(uuid_module.uuid4()).replace('-', ''),
        task_id=task_id.replace('-', ''),
        query_item_id=query_item_id.replace('-', ''),
        engine=task.engine,
        raw_html="",  # Agent doesn't send raw HTML
        parsed_response={
            "query_text": "",
            "response_text": data.response_text,
            "error": data.error,
        },
        citations=data.citations,
        response_time_ms=0,
        screenshot_path=screenshot_path,
        is_complete=data.success,
        has_citations=len(data.citations) > 0,
    )
    
    db.add(crawl_result)
    
    # Update task counters
    if data.success:
        task.successful_queries += 1
    else:
        task.failed_queries += 1
    
    # Check if task is complete
    if task.successful_queries + task.failed_queries >= task.total_queries:
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {
        "status": "ok",
        "message": "Result submitted successfully"
    }
