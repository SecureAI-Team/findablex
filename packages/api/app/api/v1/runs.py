"""Run routes."""
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.run import (
    CitationResponse,
    MetricResponse,
    RunCreate,
    RunImport,
    RunResponse,
)
from app.services.project_service import ProjectService
from app.services.run_service import RunService
from app.services.workspace_service import WorkspaceService
from app.tasks import parse_import, process_run

router = APIRouter()
logger = logging.getLogger(__name__)


def trigger_celery_task(task_name: str, *args, **kwargs):
    """Trigger a Celery task. Gracefully handles missing Celery."""
    try:
        from app.tasks import celery_app
        task = celery_app.send_task(task_name, args=args, kwargs=kwargs)
        logger.info(f"Triggered Celery task {task_name}: {task.id}")
        return task.id
    except Exception as e:
        logger.warning(f"Failed to trigger Celery task {task_name}: {e}")
        return None


@router.get("", response_model=List[RunResponse])
async def list_runs(
    project_id: UUID,
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[RunResponse]:
    """List all runs for a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    run_service = RunService(db)
    
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
    
    runs = await run_service.get_project_runs(project_id, status)
    return runs


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    data: RunCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Create a new run."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    run_service = RunService(db)
    
    project = await project_service.get_by_id(data.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "analyst"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create runs",
            )
    
    run = await run_service.create(data, current_user.id)
    
    # Queue background task for processing
    trigger_celery_task("app.tasks.ingest.process_run", str(run.id))
    
    return run


@router.post("/import", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def import_run(
    data: RunImport,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Create a run by importing data."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    run_service = RunService(db)
    
    project = await project_service.get_by_id(data.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "analyst"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to import runs",
            )
    
    # Create run
    run_data = RunCreate(
        project_id=data.project_id,
        run_type="checkup",
        input_method="import",
        parameters={"input_format": data.input_format},
    )
    run = await run_service.create(run_data, current_user.id)
    
    # Queue background task for parsing and processing
    trigger_celery_task(
        "app.tasks.ingest.parse_import",
        str(run.id),
        data.input_data,
        data.input_format,
    )
    
    return run


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Get run by ID."""
    run_service = RunService(db)
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    run = await run_service.get_by_id(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    project = await project_service.get_by_id(run.project_id)
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    return run


@router.get("/{run_id}/citations", response_model=List[CitationResponse])
async def get_citations(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CitationResponse]:
    """Get all citations for a run."""
    run_service = RunService(db)
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    run = await run_service.get_by_id(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    project = await project_service.get_by_id(run.project_id)
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    citations = await run_service.get_citations(run_id)
    return citations


@router.get("/{run_id}/metrics", response_model=List[MetricResponse])
async def get_metrics(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MetricResponse]:
    """Get all metrics for a run."""
    run_service = RunService(db)
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    run = await run_service.get_by_id(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    project = await project_service.get_by_id(run.project_id)
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    metrics = await run_service.get_metrics(run_id)
    return metrics


@router.post("/{run_id}/retest", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def retest_run(
    run_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Create a retest run based on an existing run."""
    run_service = RunService(db)
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    original_run = await run_service.get_by_id(run_id)
    if not original_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    project = await project_service.get_by_id(original_run.project_id)
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "analyst"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create runs",
            )
    
    # Create retest run
    run_data = RunCreate(
        project_id=original_run.project_id,
        run_type="retest",
        input_method=original_run.input_method,
        parameters={
            **original_run.parameters,
            "baseline_run_id": str(run_id),
        },
        region=original_run.region,
        language=original_run.language,
    )
    run = await run_service.create(run_data, current_user.id)
    
    # Queue background task for processing retest
    trigger_celery_task("app.tasks.ingest.process_run", str(run.id))
    
    return run
