"""Drift Events API routes."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.experiment import DriftEvent
from app.models.project import Project
from app.models.user import User
from app.services.workspace_service import WorkspaceService

router = APIRouter()


class DriftEventResponse(BaseModel):
    """Response schema for a drift event."""
    id: UUID
    project_id: UUID
    baseline_run_id: UUID
    compare_run_id: UUID
    drift_type: str
    severity: str
    metric_name: str
    baseline_value: float
    current_value: float
    change_percent: float
    detected_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class DriftEventSummary(BaseModel):
    """Summary of drift events."""
    total: int
    critical: int
    warning: int
    unacknowledged: int


@router.get("/{project_id}/drift-events", response_model=List[DriftEventResponse])
async def list_drift_events(
    project_id: UUID,
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DriftEventResponse]:
    """
    List drift events for a project.
    
    Filter by severity (critical, warning) or acknowledgment status.
    """
    from app.services.project_service import ProjectService
    
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Build query
    query = select(DriftEvent).where(DriftEvent.project_id == project_id)
    
    if severity:
        query = query.where(DriftEvent.severity == severity)
    
    if acknowledged is not None:
        if acknowledged:
            query = query.where(DriftEvent.acknowledged_at.isnot(None))
        else:
            query = query.where(DriftEvent.acknowledged_at.is_(None))
    
    query = query.order_by(DriftEvent.detected_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return [DriftEventResponse.model_validate(e) for e in events]


@router.get("/{project_id}/drift-events/summary", response_model=DriftEventSummary)
async def get_drift_events_summary(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DriftEventSummary:
    """Get summary of drift events for a project."""
    from app.services.project_service import ProjectService
    
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Get counts
    total_result = await db.execute(
        select(func.count(DriftEvent.id)).where(DriftEvent.project_id == project_id)
    )
    total = total_result.scalar() or 0
    
    critical_result = await db.execute(
        select(func.count(DriftEvent.id)).where(
            and_(DriftEvent.project_id == project_id, DriftEvent.severity == "critical")
        )
    )
    critical = critical_result.scalar() or 0
    
    warning_result = await db.execute(
        select(func.count(DriftEvent.id)).where(
            and_(DriftEvent.project_id == project_id, DriftEvent.severity == "warning")
        )
    )
    warning = warning_result.scalar() or 0
    
    unack_result = await db.execute(
        select(func.count(DriftEvent.id)).where(
            and_(DriftEvent.project_id == project_id, DriftEvent.acknowledged_at.is_(None))
        )
    )
    unacknowledged = unack_result.scalar() or 0
    
    return DriftEventSummary(
        total=total,
        critical=critical,
        warning=warning,
        unacknowledged=unacknowledged,
    )


@router.post("/{project_id}/drift-events/{event_id}/acknowledge")
async def acknowledge_drift_event(
    project_id: UUID,
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Acknowledge a drift event."""
    from app.services.project_service import ProjectService
    
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Get event
    result = await db.execute(
        select(DriftEvent).where(
            and_(DriftEvent.id == event_id, DriftEvent.project_id == project_id)
        )
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Drift event not found")
    
    if event.acknowledged_at:
        return {"message": "Event already acknowledged", "acknowledged_at": event.acknowledged_at}
    
    event.acknowledged_at = datetime.utcnow()
    event.acknowledged_by = current_user.id
    
    await db.commit()
    
    return {"message": "Event acknowledged", "acknowledged_at": event.acknowledged_at}
