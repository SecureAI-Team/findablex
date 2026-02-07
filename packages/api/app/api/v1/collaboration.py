"""Collaboration API routes: Comments and Activity Feed."""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.collaboration import Comment, ActivityEvent
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Membership
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# ============ Schemas ============

class CommentCreate(BaseModel):
    """Schema for creating a comment."""
    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: Optional[UUID] = None
    target_type: Optional[str] = None  # project, run, crawl_result, drift_event
    target_id: Optional[UUID] = None
    mentions: Optional[List[UUID]] = None


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""
    content: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    """Response schema for a comment."""
    id: UUID
    project_id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    parent_id: Optional[UUID] = None
    content: str
    target_type: Optional[str] = None
    target_id: Optional[UUID] = None
    mentions: Optional[List[UUID]] = None
    is_edited: bool = False
    reply_count: int = 0
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class ActivityEventResponse(BaseModel):
    """Response schema for an activity event."""
    id: UUID
    project_id: UUID
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
    event_type: str
    summary: str
    metadata_json: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True


# ============ Helper ============

async def _check_project_membership(
    project_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> Project:
    """Verify project exists and user is a member."""
    from app.services.project_service import ProjectService

    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)

    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    return project


async def _record_activity(
    db: AsyncSession,
    project: Project,
    user_id: Optional[UUID],
    event_type: str,
    summary: str,
    metadata: Optional[dict] = None,
) -> ActivityEvent:
    """Record an activity event."""
    event = ActivityEvent(
        project_id=project.id,
        workspace_id=project.workspace_id,
        user_id=user_id,
        event_type=event_type,
        summary=summary,
        metadata_json=metadata,
    )
    db.add(event)
    await db.flush()
    return event


# ============ Comment Endpoints ============

@router.get("/{project_id}/comments", response_model=List[CommentResponse])
async def list_comments(
    project_id: UUID,
    target_type: Optional[str] = None,
    target_id: Optional[UUID] = None,
    parent_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CommentResponse]:
    """
    List comments for a project.

    Filters:
    - target_type/target_id: filter by attached entity (run, crawl_result, etc.)
    - parent_id: get replies to a specific comment (null = top-level only)
    """
    await _check_project_membership(project_id, current_user, db)

    query = (
        select(Comment, User.full_name, User.email)
        .join(User, Comment.user_id == User.id)
        .where(
            and_(
                Comment.project_id == project_id,
                Comment.is_deleted == False,
            )
        )
    )

    if target_type and target_id:
        query = query.where(
            and_(Comment.target_type == target_type, Comment.target_id == target_id)
        )

    if parent_id:
        query = query.where(Comment.parent_id == parent_id)
    else:
        # Top-level comments only by default
        query = query.where(Comment.parent_id.is_(None))

    query = query.order_by(Comment.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.all()

    # Get reply counts for each comment
    comment_ids = [row[0].id for row in rows]
    reply_counts: dict[UUID, int] = {}
    if comment_ids:
        count_result = await db.execute(
            select(Comment.parent_id, func.count(Comment.id))
            .where(
                and_(
                    Comment.parent_id.in_(comment_ids),
                    Comment.is_deleted == False,
                )
            )
            .group_by(Comment.parent_id)
        )
        for parent, count in count_result:
            reply_counts[parent] = count

    return [
        CommentResponse(
            id=comment.id,
            project_id=comment.project_id,
            user_id=comment.user_id,
            user_name=user_name,
            user_email=user_email,
            parent_id=comment.parent_id,
            content=comment.content,
            target_type=comment.target_type,
            target_id=comment.target_id,
            mentions=comment.mentions,
            is_edited=comment.is_edited,
            reply_count=reply_counts.get(comment.id, 0),
            created_at=comment.created_at.isoformat(),
            updated_at=comment.updated_at.isoformat() if comment.updated_at else None,
        )
        for comment, user_name, user_email in rows
    ]


@router.post("/{project_id}/comments", response_model=CommentResponse, status_code=201)
async def create_comment(
    project_id: UUID,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """Create a comment on a project."""
    project = await _check_project_membership(project_id, current_user, db)

    # Validate parent comment exists if replying
    if data.parent_id:
        parent_result = await db.execute(
            select(Comment).where(
                and_(
                    Comment.id == data.parent_id,
                    Comment.project_id == project_id,
                    Comment.is_deleted == False,
                )
            )
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Parent comment not found")

    comment = Comment(
        project_id=project_id,
        user_id=current_user.id,
        parent_id=data.parent_id,
        content=data.content.strip(),
        target_type=data.target_type,
        target_id=data.target_id,
        mentions=data.mentions,
    )
    db.add(comment)

    # Record activity
    await _record_activity(
        db,
        project,
        current_user.id,
        "comment_added",
        f"{current_user.full_name or current_user.email} 添加了评论",
        metadata={"comment_id": str(comment.id), "target_type": data.target_type},
    )

    # Create notifications for mentioned users
    if data.mentions:
        from app.models.notification import Notification

        for mentioned_user_id in data.mentions:
            if mentioned_user_id != current_user.id:
                notification = Notification(
                    user_id=mentioned_user_id,
                    type="team_invite",
                    title="你被提到了",
                    message=f"{current_user.full_name or current_user.email} 在 {project.name} 中提到了你",
                    link=f"/projects/{project_id}?tab=overview",
                )
                db.add(notification)

    await db.commit()
    await db.refresh(comment)

    return CommentResponse(
        id=comment.id,
        project_id=comment.project_id,
        user_id=comment.user_id,
        user_name=current_user.full_name,
        user_email=current_user.email,
        parent_id=comment.parent_id,
        content=comment.content,
        target_type=comment.target_type,
        target_id=comment.target_id,
        mentions=comment.mentions,
        is_edited=False,
        reply_count=0,
        created_at=comment.created_at.isoformat(),
        updated_at=None,
    )


@router.put("/{project_id}/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    project_id: UUID,
    comment_id: UUID,
    data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """Update a comment (only by the author)."""
    await _check_project_membership(project_id, current_user, db)

    result = await db.execute(
        select(Comment).where(
            and_(
                Comment.id == comment_id,
                Comment.project_id == project_id,
                Comment.is_deleted == False,
            )
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Can only edit your own comments")

    comment.content = data.content.strip()
    comment.is_edited = True
    comment.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(comment)

    return CommentResponse(
        id=comment.id,
        project_id=comment.project_id,
        user_id=comment.user_id,
        user_name=current_user.full_name,
        user_email=current_user.email,
        parent_id=comment.parent_id,
        content=comment.content,
        target_type=comment.target_type,
        target_id=comment.target_id,
        mentions=comment.mentions,
        is_edited=comment.is_edited,
        reply_count=0,
        created_at=comment.created_at.isoformat(),
        updated_at=comment.updated_at.isoformat() if comment.updated_at else None,
    )


@router.delete("/{project_id}/comments/{comment_id}", status_code=204)
async def delete_comment(
    project_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a comment (only by the author or admin)."""
    await _check_project_membership(project_id, current_user, db)

    result = await db.execute(
        select(Comment).where(
            and_(
                Comment.id == comment_id,
                Comment.project_id == project_id,
                Comment.is_deleted == False,
            )
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Can only delete your own comments")

    comment.is_deleted = True
    await db.commit()


# ============ Activity Feed Endpoints ============

@router.get("/{project_id}/activity", response_model=List[ActivityEventResponse])
async def list_activity(
    project_id: UUID,
    event_type: Optional[str] = None,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ActivityEventResponse]:
    """
    Get activity feed for a project.

    Returns chronologically ordered events: runs, checkups, comments, drift, etc.
    """
    await _check_project_membership(project_id, current_user, db)

    query = (
        select(ActivityEvent, User.full_name)
        .outerjoin(User, ActivityEvent.user_id == User.id)
        .where(ActivityEvent.project_id == project_id)
    )

    if event_type:
        query = query.where(ActivityEvent.event_type == event_type)

    query = query.order_by(ActivityEvent.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    rows = result.all()

    return [
        ActivityEventResponse(
            id=event.id,
            project_id=event.project_id,
            user_id=event.user_id,
            user_name=user_name,
            event_type=event.event_type,
            summary=event.summary,
            metadata_json=event.metadata_json,
            created_at=event.created_at.isoformat(),
        )
        for event, user_name in rows
    ]


@router.get("/workspaces/{workspace_id}/activity", response_model=List[ActivityEventResponse])
async def list_workspace_activity(
    workspace_id: UUID,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ActivityEventResponse]:
    """Get activity feed for an entire workspace (across all projects)."""
    workspace_service = WorkspaceService(db)
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    query = (
        select(ActivityEvent, User.full_name)
        .outerjoin(User, ActivityEvent.user_id == User.id)
        .where(ActivityEvent.workspace_id == workspace_id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        ActivityEventResponse(
            id=event.id,
            project_id=event.project_id,
            user_id=event.user_id,
            user_name=user_name,
            event_type=event.event_type,
            summary=event.summary,
            metadata_json=event.metadata_json,
            created_at=event.created_at.isoformat(),
        )
        for event, user_name in rows
    ]
