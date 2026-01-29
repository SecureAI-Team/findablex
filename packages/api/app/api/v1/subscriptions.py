"""Subscription management routes."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.subscription import Plan, Subscription, PLANS
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# ========== Schemas ==========

class PlanResponse(BaseModel):
    """Plan response schema."""
    code: str
    name: str
    description: str
    price_monthly: float
    price_yearly: float
    limits: dict
    features: list = []
    
    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    """Subscription response schema."""
    id: UUID
    workspace_id: UUID
    plan_code: str
    plan_name: str
    status: str
    billing_cycle: str
    started_at: str
    expires_at: Optional[str]
    usage: dict
    limits: dict
    remaining_runs: int


class UpgradeRequest(BaseModel):
    """Upgrade request schema."""
    plan_code: str = Field(..., description="目标套餐: pro, enterprise")
    billing_cycle: str = Field(default="monthly", description="计费周期: monthly, yearly")
    payment_method: str = Field(default="manual", description="支付方式: manual, stripe, wechat, alipay")


class ContactSalesRequest(BaseModel):
    """Contact sales request schema."""
    name: str
    email: str
    company: Optional[str] = None
    message: Optional[str] = None
    plan_interest: str = "enterprise"


# ========== Endpoints ==========

@router.get("/plans", response_model=List[PlanResponse])
async def list_plans() -> List[dict]:
    """List all available subscription plans."""
    plans = []
    for code, data in PLANS.items():
        plans.append({
            "code": code,
            "name": data["name"],
            "description": data["description"],
            "price_monthly": data["price_monthly"],
            "price_yearly": data["price_yearly"],
            "limits": data["limits"],
            "features": [
                f"{data['limits']['projects']} 个项目" if data['limits']['projects'] > 0 else "无限项目",
                f"{data['limits']['queries_per_project']} 个查询词/项目" if data['limits']['queries_per_project'] > 0 else "无限查询词",
                f"{data['limits']['runs_per_month']} 次/月" if data['limits']['runs_per_month'] > 0 else "无限运行次数",
                "对比报告" if data['limits']['compare_reports'] else None,
                "API 访问" if data['limits']['api_access'] else None,
                f"{data['limits']['team_members']} 团队成员" if data['limits']['team_members'] > 0 else "无限团队成员",
            ],
        })
    return plans


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    workspace_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Get current subscription for a workspace."""
    workspace_service = WorkspaceService(db)
    
    # Get workspace_id if not provided
    if not workspace_id:
        default_ws = await workspace_service.get_default_workspace(current_user.id)
        if not default_ws:
            raise HTTPException(status_code=404, detail="No workspace found")
        workspace_id = default_ws.id
    
    # Check membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Get or create subscription
    result = await db.execute(
        select(Subscription).where(Subscription.workspace_id == workspace_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        # Create default free subscription
        subscription = Subscription(
            workspace_id=workspace_id,
            plan_code="free",
            status="active",
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
    
    plan_data = PLANS.get(subscription.plan_code, PLANS["free"])
    
    return SubscriptionResponse(
        id=subscription.id,
        workspace_id=subscription.workspace_id,
        plan_code=subscription.plan_code,
        plan_name=plan_data["name"],
        status=subscription.status,
        billing_cycle=subscription.billing_cycle,
        started_at=subscription.started_at.isoformat(),
        expires_at=subscription.expires_at.isoformat() if subscription.expires_at else None,
        usage=subscription.usage,
        limits=subscription.get_limits(),
        remaining_runs=subscription.get_remaining_runs(),
    )


@router.get("/usage")
async def get_usage(
    workspace_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get detailed usage statistics."""
    workspace_service = WorkspaceService(db)
    
    if not workspace_id:
        default_ws = await workspace_service.get_default_workspace(current_user.id)
        if not default_ws:
            raise HTTPException(status_code=404, detail="No workspace found")
        workspace_id = default_ws.id
    
    result = await db.execute(
        select(Subscription).where(Subscription.workspace_id == workspace_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        subscription = Subscription(
            workspace_id=workspace_id,
            plan_code="free",
            status="active",
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
    
    limits = subscription.get_limits()
    usage = subscription.usage or {}
    
    return {
        "plan": subscription.plan_code,
        "limits": limits,
        "usage": {
            "runs": {
                "used": usage.get("runs_this_month", 0),
                "limit": limits.get("runs_per_month", 0),
                "remaining": subscription.get_remaining_runs(),
                "bonus": subscription.bonus_runs,
            },
            "projects": {
                "used": usage.get("projects_created", 0),
                "limit": limits.get("projects", 0),
            },
            "queries": {
                "used": usage.get("queries_created", 0),
                "limit_per_project": limits.get("queries_per_project", 0),
            },
        },
        "features": {
            "compare_reports": limits.get("compare_reports", False),
            "api_access": limits.get("api_access", False),
            "team_members": limits.get("team_members", 1),
        },
    }


@router.post("/upgrade")
async def request_upgrade(
    data: UpgradeRequest,
    workspace_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Request subscription upgrade.
    
    For manual payment, this creates an upgrade request.
    The admin will process and activate after payment confirmation.
    """
    workspace_service = WorkspaceService(db)
    
    if not workspace_id:
        default_ws = await workspace_service.get_default_workspace(current_user.id)
        if not default_ws:
            raise HTTPException(status_code=404, detail="No workspace found")
        workspace_id = default_ws.id
    
    if data.plan_code not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan code")
    
    plan_data = PLANS[data.plan_code]
    price = plan_data["price_yearly"] if data.billing_cycle == "yearly" else plan_data["price_monthly"]
    
    # For manual payment, return payment instructions
    if data.payment_method == "manual":
        return {
            "status": "pending_payment",
            "plan": data.plan_code,
            "plan_name": plan_data["name"],
            "billing_cycle": data.billing_cycle,
            "price": price,
            "currency": "CNY",
            "payment_instructions": {
                "bank_transfer": {
                    "bank": "招商银行",
                    "account": "XXXX-XXXX-XXXX-1234",
                    "name": "某某科技有限公司",
                },
                "wechat": "请联系销售获取微信支付二维码",
                "alipay": "请联系销售获取支付宝账号",
            },
            "contact": {
                "email": "sales@findablex.com",
                "wechat": "FindableX_Sales",
            },
            "message": f"请完成 ¥{price} 的付款后，联系销售开通 {plan_data['name']}",
        }
    
    # For other payment methods, would integrate with payment gateway
    return {
        "status": "payment_method_not_supported",
        "message": "暂时只支持线下付款，请联系销售",
    }


@router.post("/contact-sales")
async def contact_sales(
    data: ContactSalesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Submit a contact sales request."""
    # In production, this would send an email or create a CRM lead
    return {
        "status": "success",
        "message": "感谢您的咨询！我们的销售团队将在24小时内与您联系。",
    }


@router.post("/admin/activate")
async def admin_activate_subscription(
    workspace_id: UUID,
    plan_code: str,
    billing_cycle: str = "monthly",
    months: int = 1,
    bonus_runs: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Admin endpoint to manually activate a subscription.
    
    Used after confirming payment.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin only")
    
    if plan_code not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan code")
    
    from datetime import timedelta
    
    result = await db.execute(
        select(Subscription).where(Subscription.workspace_id == workspace_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        subscription = Subscription(workspace_id=workspace_id)
        db.add(subscription)
    
    # Update subscription
    subscription.plan_code = plan_code
    subscription.status = "active"
    subscription.billing_cycle = billing_cycle
    subscription.bonus_runs = bonus_runs
    subscription.started_at = datetime.now(timezone.utc)
    subscription.expires_at = datetime.now(timezone.utc) + timedelta(days=30 * months)
    subscription.last_payment_at = datetime.now(timezone.utc)
    subscription.payment_method = "manual"
    
    # Reset usage
    subscription.usage = {
        "runs_this_month": 0,
        "queries_created": 0,
        "reports_generated": 0,
        "last_reset_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.commit()
    await db.refresh(subscription)
    
    return {
        "status": "activated",
        "workspace_id": str(workspace_id),
        "plan": plan_code,
        "expires_at": subscription.expires_at.isoformat(),
        "bonus_runs": bonus_runs,
    }
