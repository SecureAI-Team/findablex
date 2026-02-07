"""Bot integration API routes for Feishu / WeCom notifications."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.bot_integration import BotIntegration
from app.services.workspace_service import WorkspaceService

router = APIRouter()

# Supported platforms and events
BOT_PLATFORMS = ["feishu", "wecom"]
BOT_EVENT_TYPES = ["checkup_complete", "drift_detected", "weekly_digest"]


# ============ Schemas ============

class BotIntegrationSave(BaseModel):
    """Save / update a bot integration."""
    platform: str = Field(..., description="feishu | wecom")
    webhook_url: str = Field(..., min_length=10, max_length=2000)
    events: List[str] = Field(
        default=["checkup_complete", "drift_detected", "weekly_digest"],
        description="Events to subscribe to",
    )
    is_active: bool = True


class BotIntegrationResponse(BaseModel):
    """Response schema for a bot integration."""
    id: UUID
    workspace_id: UUID
    platform: str
    webhook_url: str
    events: List[str]
    is_active: bool
    last_triggered_at: Optional[str] = None
    last_error: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class BotTestResponse(BaseModel):
    success: bool
    error: Optional[str] = None


# ============ Helpers ============

def _validate_platform(platform: str) -> None:
    if platform not in BOT_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform: {platform}. Must be one of: {', '.join(BOT_PLATFORMS)}",
        )


def _validate_events(events: List[str]) -> None:
    invalid = [e for e in events if e not in BOT_EVENT_TYPES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event types: {', '.join(invalid)}. Valid: {', '.join(BOT_EVENT_TYPES)}",
        )


def _to_response(bot: BotIntegration) -> BotIntegrationResponse:
    return BotIntegrationResponse(
        id=bot.id,
        workspace_id=bot.workspace_id,
        platform=bot.platform,
        webhook_url=bot.webhook_url,
        events=bot.events or [],
        is_active=bot.is_active,
        last_triggered_at=bot.last_triggered_at.isoformat() if bot.last_triggered_at else None,
        last_error=bot.last_error,
        created_at=bot.created_at.isoformat(),
        updated_at=bot.updated_at.isoformat() if bot.updated_at else None,
    )


# ============ Endpoints ============

@router.get(
    "/workspaces/{workspace_id}/bots",
    response_model=List[BotIntegrationResponse],
)
async def list_bot_integrations(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[BotIntegrationResponse]:
    """List all bot integrations for a workspace."""
    ws_service = WorkspaceService(db)
    membership = await ws_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    result = await db.execute(
        select(BotIntegration)
        .where(BotIntegration.workspace_id == workspace_id)
        .order_by(BotIntegration.platform)
    )
    bots = result.scalars().all()
    return [_to_response(b) for b in bots]


@router.put(
    "/workspaces/{workspace_id}/bots",
    response_model=BotIntegrationResponse,
)
async def save_bot_integration(
    workspace_id: UUID,
    data: BotIntegrationSave,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BotIntegrationResponse:
    """Create or update a bot integration (upsert by workspace + platform)."""
    ws_service = WorkspaceService(db)
    membership = await ws_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Only admins can configure bot integrations")

    _validate_platform(data.platform)
    _validate_events(data.events)

    # Upsert: find existing or create new
    result = await db.execute(
        select(BotIntegration).where(
            and_(
                BotIntegration.workspace_id == workspace_id,
                BotIntegration.platform == data.platform,
            )
        )
    )
    bot = result.scalar_one_or_none()

    if bot:
        bot.webhook_url = data.webhook_url.strip()
        bot.events = data.events
        bot.is_active = data.is_active
    else:
        bot = BotIntegration(
            workspace_id=workspace_id,
            created_by=current_user.id,
            platform=data.platform,
            webhook_url=data.webhook_url.strip(),
            events=data.events,
            is_active=data.is_active,
        )
        db.add(bot)

    await db.commit()
    await db.refresh(bot)
    return _to_response(bot)


@router.delete(
    "/workspaces/{workspace_id}/bots/{platform}",
    status_code=204,
)
async def delete_bot_integration(
    workspace_id: UUID,
    platform: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a bot integration by platform."""
    ws_service = WorkspaceService(db)
    membership = await ws_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Only admins can delete bot integrations")

    result = await db.execute(
        select(BotIntegration).where(
            and_(
                BotIntegration.workspace_id == workspace_id,
                BotIntegration.platform == platform,
            )
        )
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot integration not found")

    await db.delete(bot)
    await db.commit()


@router.post(
    "/workspaces/{workspace_id}/bots/{platform}/test",
    response_model=BotTestResponse,
)
async def test_bot_integration(
    workspace_id: UUID,
    platform: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BotTestResponse:
    """Send a test message to a bot integration."""
    ws_service = WorkspaceService(db)
    membership = await ws_service.get_membership(workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Only admins can test bot integrations")

    result = await db.execute(
        select(BotIntegration).where(
            and_(
                BotIntegration.workspace_id == workspace_id,
                BotIntegration.platform == platform,
            )
        )
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot integration not found")

    from app.services.bot_service import BotService
    bot_service = BotService()

    try:
        if platform == "feishu":
            await bot_service.send_feishu(
                bot.webhook_url,
                "FindableX 测试消息",
                "这是一条来自 FindableX 的测试通知，配置成功！🎉",
            )
        elif platform == "wecom":
            await bot_service.send_wecom(
                bot.webhook_url,
                "FindableX 测试消息\n这是一条来自 FindableX 的测试通知，配置成功！🎉",
            )
        return BotTestResponse(success=True)
    except Exception as e:
        return BotTestResponse(success=False, error=str(e)[:200])
