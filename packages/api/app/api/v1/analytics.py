"""Analytics routes for event tracking."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db, get_current_user_optional
from app.models.user import User
from app.services.analytics_service import AnalyticsService

router = APIRouter()


# ========== Schemas ==========

class TrackEventRequest(BaseModel):
    """Request to track an event."""
    event_type: str
    properties: Optional[Dict[str, Any]] = None


class FunnelMetricsResponse(BaseModel):
    """Response for funnel metrics."""
    activation_funnel: dict
    conversion_funnel: dict
    key_metrics: dict


# ========== Endpoints ==========

@router.post("/track")
async def track_event(
    data: TrackEventRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Track a user event.
    
    Can be called with or without authentication.
    """
    analytics = AnalyticsService(db)
    
    # 获取workspace_id from properties if available
    workspace_id = None
    if data.properties and data.properties.get("workspace_id"):
        try:
            workspace_id = UUID(data.properties["workspace_id"])
        except (ValueError, TypeError):
            pass
    
    await analytics.track_event(
        event_type=data.event_type,
        user_id=current_user.id if current_user else None,
        workspace_id=workspace_id,
        properties=data.properties,
    )
    
    return {"status": "tracked"}


@router.get("/funnel")
async def get_funnel_metrics(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FunnelMetricsResponse:
    """
    Get funnel metrics for the last N days.
    
    Admin only endpoint.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin only")
    
    analytics = AnalyticsService(db)
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    metrics = await analytics.get_funnel_metrics(start_date)
    
    return FunnelMetricsResponse(**metrics)


@router.get("/user/activation")
async def get_user_activation_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get activation status for current user.
    
    Returns which activation steps the user has completed.
    """
    analytics = AnalyticsService(db)
    status = await analytics.check_user_activation(current_user.id)
    
    return {
        "user_id": str(current_user.id),
        "activation_status": status,
        "is_activated": status.get("is_activated", False),
        "next_step": _get_next_activation_step(status),
    }


def _get_next_activation_step(status: Dict[str, bool]) -> Optional[str]:
    """Determine the next activation step for the user."""
    if not status.get("selected_template"):
        return "select_template"
    if not status.get("generated_queries"):
        return "generate_queries"
    if not status.get("completed_first_crawl"):
        return "run_first_crawl"
    if not status.get("viewed_first_report"):
        return "view_report"
    return None


@router.get("/events")
async def get_event_counts(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get event counts for the last N days.
    
    Admin only endpoint.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin only")
    
    analytics = AnalyticsService(db)
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    counts = await analytics.get_event_counts(start_date)
    
    # Group by category
    by_category = {
        "activation": {},
        "value": {},
        "conversion": {},
        "retention": {},
    }
    
    from app.services.analytics_service import EVENT_TYPES
    for event_type, count in counts.items():
        category = EVENT_TYPES.get(event_type, {}).get("category", "unknown")
        if category in by_category:
            by_category[category][event_type] = count
    
    return {
        "period_days": days,
        "total_events": sum(counts.values()),
        "by_event": counts,
        "by_category": by_category,
    }
