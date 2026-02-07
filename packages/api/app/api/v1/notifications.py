"""
Notification API endpoints for in-app message center.

Provides endpoints for:
- Listing user notifications (with pagination)
- Getting unread count
- Marking notifications as read
- Marking all as read
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.notification import Notification

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Schemas ---

class NotificationResponse(BaseModel):
    """Single notification response."""
    id: str
    type: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: str
    
    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Paginated notification list."""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """Unread notification count."""
    count: int


class MarkReadRequest(BaseModel):
    """Request to mark specific notifications as read."""
    notification_ids: List[str]


# --- Endpoints ---

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user with pagination."""
    offset = (page - 1) * page_size
    
    # Base filter
    base_filter = Notification.user_id == current_user.id
    if unread_only:
        base_filter = and_(base_filter, Notification.is_read == False)
    
    # Get total count
    count_query = select(func.count()).select_from(Notification).where(base_filter)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get unread count (always)
    unread_query = select(func.count()).select_from(Notification).where(
        and_(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar() or 0
    
    # Get notifications
    query = (
        select(Notification)
        .where(base_filter)
        .order_by(desc(Notification.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=str(n.id),
                type=n.type,
                title=n.title,
                message=n.message,
                link=n.link,
                is_read=n.is_read,
                created_at=n.created_at.isoformat() if n.created_at else "",
            )
            for n in notifications
        ],
        total=total,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get unread notification count for badge display."""
    query = select(func.count()).select_from(Notification).where(
        and_(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    result = await db.execute(query)
    count = result.scalar() or 0
    
    return UnreadCountResponse(count=count)


@router.post("/mark-read")
async def mark_notifications_read(
    request: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark specific notifications as read."""
    now = datetime.now(timezone.utc)
    
    try:
        notification_uuids = [UUID(nid) for nid in request.notification_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID format")
    
    stmt = (
        update(Notification)
        .where(
            and_(
                Notification.id.in_(notification_uuids),
                Notification.user_id == current_user.id,
            )
        )
        .values(is_read=True, read_at=now)
    )
    await db.execute(stmt)
    await db.commit()
    
    return {"status": "ok", "marked": len(notification_uuids)}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    now = datetime.now(timezone.utc)
    
    stmt = (
        update(Notification)
        .where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            )
        )
        .values(is_read=True, read_at=now)
    )
    result = await db.execute(stmt)
    await db.commit()
    
    return {"status": "ok", "marked": result.rowcount}
