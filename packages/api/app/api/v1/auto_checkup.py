"""Auto-checkup API - One-click GEO health check automation.

Combines crawl task creation and run generation into a single automated flow:
1. Select available engines (prefer API engines)
2. Create crawl tasks for project queries
3. Track progress
4. Auto-generate report when complete
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.crawler import CrawlTask
from app.models.project import Project, QueryItem
from app.models.user import User
from app.services.project_service import ProjectService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# ========== Schemas ==========

class AutoCheckupRequest(BaseModel):
    """Request for auto-checkup."""
    engines: Optional[List[str]] = None  # If None, auto-select
    max_engines: int = 3  # Max number of engines to use


class AutoCheckupResponse(BaseModel):
    """Response after initiating auto-checkup."""
    project_id: str
    project_name: str
    tasks_created: int
    engines_used: List[str]
    total_queries: int
    estimated_time_minutes: int
    task_ids: List[str]
    message: str


class CheckupStatusResponse(BaseModel):
    """Status of an auto-checkup."""
    project_id: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    failed_tasks: int
    overall_progress: float  # 0-100
    engines: List[Dict[str, Any]]
    is_complete: bool
    can_generate_report: bool


# Available engines ordered by preference (API engines first)
AVAILABLE_ENGINES = [
    {"id": "deepseek", "name": "DeepSeek", "type": "api", "priority": 1},
    {"id": "qwen", "name": "通义千问", "type": "api", "priority": 2},
    {"id": "kimi", "name": "Kimi", "type": "api", "priority": 3},
    {"id": "chatgpt", "name": "ChatGPT", "type": "api", "priority": 4},
    {"id": "perplexity", "name": "Perplexity", "type": "api", "priority": 5},
    {"id": "doubao", "name": "豆包", "type": "browser", "priority": 6},
    {"id": "chatglm", "name": "ChatGLM", "type": "browser", "priority": 7},
    {"id": "google_sge", "name": "Google SGE", "type": "browser", "priority": 8},
]


def select_engines(
    requested_engines: Optional[List[str]] = None,
    max_engines: int = 3,
) -> List[Dict[str, Any]]:
    """Select engines for auto-checkup."""
    if requested_engines:
        # Use requested engines
        return [
            e for e in AVAILABLE_ENGINES
            if e["id"] in requested_engines
        ][:max_engines]
    
    # Auto-select: prefer API engines, limit to max_engines
    sorted_engines = sorted(AVAILABLE_ENGINES, key=lambda e: e["priority"])
    return sorted_engines[:max_engines]


@router.post("/{project_id}/auto-checkup", response_model=AutoCheckupResponse)
async def create_auto_checkup(
    project_id: UUID,
    data: AutoCheckupRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutoCheckupResponse:
    """
    One-click auto checkup for a project.
    
    Automatically:
    1. Selects the best available engines
    2. Creates crawl tasks for all project queries
    3. Dispatches tasks for processing
    
    The frontend can poll the status endpoint for progress.
    """
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    # Verify project exists and user has access
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Get project queries
    result = await db.execute(
        select(QueryItem)
        .where(QueryItem.project_id == project_id)
        .order_by(QueryItem.position)
    )
    queries = list(result.scalars().all())
    
    if not queries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="项目没有查询词，请先添加查询词或使用模板",
        )
    
    # Check subscription quota
    try:
        from app.middleware.quota import get_workspace_subscription
        subscription = await get_workspace_subscription(project.workspace_id, db)
        remaining_runs = subscription.get_remaining_runs()
        if remaining_runs == 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="本月运行次数已用完，请升级套餐",
            )
    except ImportError:
        pass  # Quota middleware not available
    except HTTPException:
        raise
    except Exception:
        pass  # Non-critical
    
    # Select engines
    engines = select_engines(data.engines, data.max_engines)
    if not engines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可用的引擎",
        )
    
    # Create crawl tasks for each engine
    task_ids = []
    from datetime import datetime, timezone
    
    for engine_info in engines:
        task = CrawlTask(
            project_id=project_id,
            engine=engine_info["id"],
            status="pending",
            total_queries=len(queries),
            successful_queries=0,
            failed_queries=0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(task)
        await db.flush()
        task_ids.append(str(task.id))
    
    await db.commit()
    
    # Dispatch crawl tasks to worker
    for task_id in task_ids:
        try:
            from app.tasks import process_crawl_task
            process_crawl_task.delay(task_id)
        except Exception as e:
            # Task dispatch failure is non-fatal - task is created and can be retried
            import logging
            logging.getLogger(__name__).warning(f"Failed to dispatch crawl task {task_id}: {e}")
    
    # Track analytics event
    try:
        from app.services.analytics_service import AnalyticsService
        analytics = AnalyticsService(db)
        await analytics.track_event(
            "auto_checkup_started",
            user_id=current_user.id,
            workspace_id=project.workspace_id,
            properties={
                "project_id": str(project_id),
                "engines": [e["id"] for e in engines],
                "query_count": len(queries),
            },
        )
    except Exception:
        pass
    
    # Estimate time (roughly 5 seconds per query per engine)
    estimated_time = max(1, (len(queries) * len(engines) * 5) // 60)
    
    engine_ids = [e["id"] for e in engines]
    
    return AutoCheckupResponse(
        project_id=str(project_id),
        project_name=project.name,
        tasks_created=len(engines),
        engines_used=engine_ids,
        total_queries=len(queries),
        estimated_time_minutes=estimated_time,
        task_ids=task_ids,
        message=f"已创建 {len(engines)} 个引擎的研究任务，共 {len(queries)} 个查询词",
    )


@router.get("/{project_id}/checkup-status", response_model=CheckupStatusResponse)
async def get_checkup_status(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckupStatusResponse:
    """
    Get the status of the latest auto-checkup for a project.
    
    Poll this endpoint to track progress.
    """
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Get all crawl tasks for this project, ordered by most recent
    result = await db.execute(
        select(CrawlTask)
        .where(CrawlTask.project_id == project_id)
        .order_by(CrawlTask.created_at.desc())
    )
    tasks = list(result.scalars().all())
    
    if not tasks:
        return CheckupStatusResponse(
            project_id=str(project_id),
            total_tasks=0,
            completed_tasks=0,
            in_progress_tasks=0,
            failed_tasks=0,
            overall_progress=0,
            engines=[],
            is_complete=False,
            can_generate_report=False,
        )
    
    completed = sum(1 for t in tasks if t.status == "completed")
    in_progress = sum(1 for t in tasks if t.status in ("pending", "processing", "running"))
    failed = sum(1 for t in tasks if t.status == "failed")
    
    # Calculate overall progress
    total_queries = sum(t.total_queries for t in tasks)
    processed_queries = sum(t.successful_queries + t.failed_queries for t in tasks)
    progress = (processed_queries / total_queries * 100) if total_queries > 0 else 0
    
    engines_status = [
        {
            "engine": t.engine,
            "status": t.status,
            "total_queries": t.total_queries,
            "successful": t.successful_queries,
            "failed": t.failed_queries,
            "progress": round(
                (t.successful_queries + t.failed_queries) / t.total_queries * 100
                if t.total_queries > 0 else 0
            ),
        }
        for t in tasks
    ]
    
    is_complete = in_progress == 0 and len(tasks) > 0
    can_generate_report = completed > 0
    
    return CheckupStatusResponse(
        project_id=str(project_id),
        total_tasks=len(tasks),
        completed_tasks=completed,
        in_progress_tasks=in_progress,
        failed_tasks=failed,
        overall_progress=round(progress, 1),
        engines=engines_status,
        is_complete=is_complete,
        can_generate_report=can_generate_report,
    )
