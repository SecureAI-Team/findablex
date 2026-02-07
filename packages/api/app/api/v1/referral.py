"""Referral / invite reward API.

Each user gets a unique referral code.  When a new user registers with that
code, both the referrer and the new user receive bonus runs.

Rewards:
  - Referrer: +5 bonus runs per successful referral
  - New user: +3 bonus runs (on top of free tier)
"""
import logging
import secrets
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.services.workspace_service import WorkspaceService

router = APIRouter()
logger = logging.getLogger(__name__)

# Reward configuration
REFERRER_BONUS_RUNS = 5
REFEREE_BONUS_RUNS = 3


class ReferralInfo(BaseModel):
    """Current user's referral information."""
    referral_code: str
    referral_url: str
    total_referrals: int
    total_bonus_earned: int


class ApplyReferralRequest(BaseModel):
    """Apply a referral code (called during registration or post-signup)."""
    referral_code: str


def _generate_referral_code() -> str:
    """Generate a short, unique referral code."""
    return "FX" + secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()


@router.get("/referral/me", response_model=ReferralInfo)
async def get_my_referral_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReferralInfo:
    """Get current user's referral code and stats."""
    # Ensure user has a referral code stored in their settings
    user_settings = current_user.settings or {}
    referral_code = user_settings.get("referral_code")
    
    if not referral_code:
        referral_code = _generate_referral_code()
        if current_user.settings is None:
            current_user.settings = {}
        current_user.settings = {**current_user.settings, "referral_code": referral_code}
        await db.commit()
    
    # Count referrals (users who have this user's referral code in their settings)
    total_referrals = user_settings.get("referral_count", 0)
    total_bonus = total_referrals * REFERRER_BONUS_RUNS
    
    base_url = "https://findablex.com"
    
    return ReferralInfo(
        referral_code=referral_code,
        referral_url=f"{base_url}/register?ref={referral_code}",
        total_referrals=total_referrals,
        total_bonus_earned=total_bonus,
    )


@router.post("/referral/apply")
async def apply_referral_code(
    data: ApplyReferralRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Apply a referral code.
    
    Called after a new user registers with a referral link.
    Awards bonus runs to both referrer and referee.
    """
    referral_code = data.referral_code.strip().upper()
    
    # Check if user already used a referral code
    user_settings = current_user.settings or {}
    if user_settings.get("referred_by"):
        return {
            "status": "already_applied",
            "message": "您已经使用过邀请码",
        }
    
    # Don't allow self-referral
    if user_settings.get("referral_code") == referral_code:
        raise HTTPException(status_code=400, detail="不能使用自己的邀请码")
    
    # Find the referrer by their referral code
    # We need to search through user settings - this is not ideal for large scale
    # but works for early stage
    result = await db.execute(select(User))
    all_users = list(result.scalars().all())
    
    referrer = None
    for u in all_users:
        u_settings = u.settings or {}
        if u_settings.get("referral_code") == referral_code:
            referrer = u
            break
    
    if not referrer:
        raise HTTPException(status_code=404, detail="邀请码无效")
    
    # Award bonus to referee (current user)
    workspace_service = WorkspaceService(db)
    ref_ws = await workspace_service.get_default_workspace(current_user.id)
    if ref_ws:
        from app.middleware.quota import get_workspace_subscription
        sub = await get_workspace_subscription(ref_ws.id, db)
        sub.bonus_runs = (sub.bonus_runs or 0) + REFEREE_BONUS_RUNS
    
    # Award bonus to referrer
    ref_ws_referrer = await workspace_service.get_default_workspace(referrer.id)
    if ref_ws_referrer:
        from app.middleware.quota import get_workspace_subscription
        sub_ref = await get_workspace_subscription(ref_ws_referrer.id, db)
        sub_ref.bonus_runs = (sub_ref.bonus_runs or 0) + REFERRER_BONUS_RUNS
    
    # Update user settings
    current_user.settings = {
        **(current_user.settings or {}),
        "referred_by": str(referrer.id),
        "referred_at": __import__("datetime").datetime.now().isoformat(),
    }
    
    # Update referrer stats
    referrer.settings = {
        **(referrer.settings or {}),
        "referral_count": (referrer.settings or {}).get("referral_count", 0) + 1,
    }
    
    await db.commit()
    
    logger.info(
        f"Referral applied: {current_user.id} referred by {referrer.id} "
        f"(code: {referral_code})"
    )
    
    return {
        "status": "success",
        "message": f"邀请码已生效！您获得了 {REFEREE_BONUS_RUNS} 次额外体检次数",
        "bonus_runs": REFEREE_BONUS_RUNS,
    }
