"""Webhook management API routes for the open platform."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.webhook import Webhook, WebhookDelivery
from app.services.workspace_service import WorkspaceService

router = APIRouter()

# Allowed event types
WEBHOOK_EVENT_TYPES = [
    "run.completed",
    "crawl_task.completed",
    "drift.detected",
    "report.generated",
    "checkup.completed",
]


# ============ Schemas ============

class WebhookCreate(BaseModel):
    """Schema for creating a webhook."""
    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=10, max_length=2000)
    events: List[str] = Field(..., min_length=1)


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""
    name: Optional[str] = Field(None, max_length=200)
    url: Optional[str] = Field(None, max_length=2000)
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None


class WebhookResponse(BaseModel):
    """Response schema for a webhook."""
    id: UUID
    workspace_id: UUID
    name: str
    url: str
    secret: str
    events: List[str]
    is_active: bool
    last_triggered_at: Optional[str] = None
    last_status_code: Optional[int] = None
    last_error: Optional[str] = None
    failure_count: int = 0
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    """Response schema for a webhook delivery."""
    id: UUID
    webhook_id: UUID
    event_type: str
    payload: Optional[dict] = None
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    success: bool
    created_at: str

    class Config:
        from_attributes = True


class WebhookTestResponse(BaseModel):
    """Response after testing a webhook."""
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


# ============ Helper ============

def _validate_events(events: List[str]) -> None:
    """Validate webhook event types."""
    invalid = [e for e in events if e not in WEBHOOK_EVENT_TYPES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event types: {', '.join(invalid)}. "
                   f"Valid types: {', '.join(WEBHOOK_EVENT_TYPES)}",
        )


def _webhook_to_response(webhook: Webhook) -> WebhookResponse:
    return WebhookResponse(
        id=webhook.id,
        workspace_id=webhook.workspace_id,
        name=webhook.name,
        url=webhook.url,
        secret=webhook.secret,
        events=webhook.events or [],
        is_active=webhook.is_active,
        last_triggered_at=webhook.last_triggered_at.isoformat() if webhook.last_triggered_at else None,
        last_status_code=webhook.last_status_code,
        last_error=webhook.last_error,
        failure_count=webhook.failure_count,
        created_at=webhook.created_at.isoformat(),
        updated_at=webhook.updated_at.isoformat() if webhook.updated_at else None,
    )


# ============ Endpoints ============

@router.get("/workspaces/{workspace_id}/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[WebhookResponse]:
    """List all webhooks for a workspace."""
    workspace_service = WorkspaceService(db)
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    result = await db.execute(
        select(Webhook)
        .where(Webhook.workspace_id == workspace_id)
        .order_by(Webhook.created_at.desc())
    )
    webhooks = result.scalars().all()
    return [_webhook_to_response(w) for w in webhooks]


@router.post("/workspaces/{workspace_id}/webhooks", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    workspace_id: UUID,
    data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """Create a new webhook subscription."""
    workspace_service = WorkspaceService(db)
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Only admins can create webhooks")

    _validate_events(data.events)

    # Limit to 10 webhooks per workspace
    count_result = await db.execute(
        select(func.count(Webhook.id)).where(Webhook.workspace_id == workspace_id)
    )
    count = count_result.scalar() or 0
    if count >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 webhooks per workspace")

    webhook = Webhook(
        workspace_id=workspace_id,
        created_by=current_user.id,
        name=data.name.strip(),
        url=data.url.strip(),
        events=data.events,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)

    return _webhook_to_response(webhook)


@router.put("/workspaces/{workspace_id}/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    workspace_id: UUID,
    webhook_id: UUID,
    data: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """Update a webhook."""
    workspace_service = WorkspaceService(db)
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Only admins can update webhooks")

    result = await db.execute(
        select(Webhook).where(
            and_(Webhook.id == webhook_id, Webhook.workspace_id == workspace_id)
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if data.name is not None:
        webhook.name = data.name.strip()
    if data.url is not None:
        webhook.url = data.url.strip()
    if data.events is not None:
        _validate_events(data.events)
        webhook.events = data.events
    if data.is_active is not None:
        webhook.is_active = data.is_active
        if data.is_active:
            webhook.failure_count = 0  # Reset failures on re-enable

    await db.commit()
    await db.refresh(webhook)

    return _webhook_to_response(webhook)


@router.delete("/workspaces/{workspace_id}/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(
    workspace_id: UUID,
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a webhook."""
    workspace_service = WorkspaceService(db)
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Only admins can delete webhooks")

    result = await db.execute(
        select(Webhook).where(
            and_(Webhook.id == webhook_id, Webhook.workspace_id == workspace_id)
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await db.delete(webhook)
    await db.commit()


@router.get(
    "/workspaces/{workspace_id}/webhooks/{webhook_id}/deliveries",
    response_model=List[WebhookDeliveryResponse],
)
async def list_webhook_deliveries(
    workspace_id: UUID,
    webhook_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[WebhookDeliveryResponse]:
    """Get recent deliveries for a webhook."""
    workspace_service = WorkspaceService(db)
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    # Verify webhook belongs to workspace
    webhook_result = await db.execute(
        select(Webhook.id).where(
            and_(Webhook.id == webhook_id, Webhook.workspace_id == workspace_id)
        )
    )
    if not webhook_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Webhook not found")

    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    deliveries = result.scalars().all()

    return [
        WebhookDeliveryResponse(
            id=d.id,
            webhook_id=d.webhook_id,
            event_type=d.event_type,
            payload=d.payload,
            status_code=d.status_code,
            response_body=d.response_body[:500] if d.response_body else None,
            error=d.error,
            duration_ms=d.duration_ms,
            success=d.success,
            created_at=d.created_at.isoformat(),
        )
        for d in deliveries
    ]


@router.post(
    "/workspaces/{workspace_id}/webhooks/{webhook_id}/test",
    response_model=WebhookTestResponse,
)
async def test_webhook(
    workspace_id: UUID,
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebhookTestResponse:
    """Send a test event to a webhook endpoint."""
    import httpx
    import time
    import hmac
    import hashlib
    import json

    workspace_service = WorkspaceService(db)
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Only admins can test webhooks")

    result = await db.execute(
        select(Webhook).where(
            and_(Webhook.id == webhook_id, Webhook.workspace_id == workspace_id)
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    # Build test payload
    test_payload = {
        "event": "test",
        "webhook_id": str(webhook.id),
        "workspace_id": str(workspace_id),
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "message": "This is a test event from FindableX",
        },
    }

    payload_bytes = json.dumps(test_payload).encode("utf-8")
    signature = hmac.new(
        webhook.secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()

    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-FindableX-Signature": signature,
                    "X-FindableX-Event": "test",
                },
            )
        duration_ms = int((time.time() - start_time) * 1000)

        # Record delivery
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type="test",
            payload=test_payload,
            status_code=response.status_code,
            response_body=response.text[:1000] if response.text else None,
            success=200 <= response.status_code < 300,
            duration_ms=duration_ms,
        )
        db.add(delivery)
        await db.commit()

        return WebhookTestResponse(
            success=200 <= response.status_code < 300,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        # Record failed delivery
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type="test",
            payload=test_payload,
            error=str(e)[:500],
            success=False,
            duration_ms=duration_ms,
        )
        db.add(delivery)
        await db.commit()

        return WebhookTestResponse(
            success=False,
            error=str(e)[:200],
            duration_ms=duration_ms,
        )


@router.get("/webhook-events")
async def list_webhook_event_types() -> dict:
    """List available webhook event types and their descriptions."""
    return {
        "events": [
            {
                "type": "run.completed",
                "description": "Fired when a GEO health check run finishes",
                "payload_fields": ["run_id", "project_id", "status", "health_score"],
            },
            {
                "type": "crawl_task.completed",
                "description": "Fired when a research crawl task completes",
                "payload_fields": ["task_id", "project_id", "engine", "success_count", "total_count"],
            },
            {
                "type": "drift.detected",
                "description": "Fired when metric drift is detected on a project",
                "payload_fields": ["project_id", "drift_type", "severity", "metric_name", "change_percent"],
            },
            {
                "type": "report.generated",
                "description": "Fired when a report is generated",
                "payload_fields": ["report_id", "project_id", "report_type"],
            },
            {
                "type": "checkup.completed",
                "description": "Fired when an auto-checkup finishes all engines",
                "payload_fields": ["project_id", "engines", "total_tasks", "success_count"],
            },
        ]
    }
