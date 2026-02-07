"""Payment API endpoints for subscription billing."""
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.services.payment_service import PaymentService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# ========== Schemas ==========

class CreateOrderRequest(BaseModel):
    """Request to create a payment order."""
    plan_code: str
    billing_cycle: str = "monthly"  # monthly or yearly
    payment_method: str = "wechat"  # wechat, alipay, manual


class OrderResponse(BaseModel):
    """Payment order response."""
    order_id: str
    plan_code: str
    plan_name: str
    amount: float
    currency: str
    payment_method: str
    status: str
    payment_data: Dict[str, Any]


# ========== Endpoints ==========

@router.post("/orders", response_model=OrderResponse)
async def create_payment_order(
    data: CreateOrderRequest,
    workspace_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Create a payment order for subscription upgrade.
    
    Returns payment data (QR code URL for WeChat, payment URL for Alipay).
    """
    workspace_service = WorkspaceService(db)
    
    if not workspace_id:
        default_ws = await workspace_service.get_default_workspace(current_user.id)
        if not default_ws:
            raise HTTPException(status_code=404, detail="No workspace found")
        workspace_id = default_ws.id
    
    # Verify membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    payment_service = PaymentService(db)
    
    try:
        order = await payment_service.create_order(
            workspace_id=workspace_id,
            user_id=current_user.id,
            plan_code=data.plan_code,
            billing_cycle=data.billing_cycle,
            payment_method=data.payment_method,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return OrderResponse(
        order_id=order["order_id"],
        plan_code=order["plan_code"],
        plan_name=order["plan_name"],
        amount=order["amount"],
        currency=order["currency"],
        payment_method=order["payment_method"],
        status=order["status"],
        payment_data=order.get("payment_data", {}),
    )


@router.post("/callback/wechat")
async def wechat_payment_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    WeChat Pay callback endpoint.
    
    Called by WeChat Pay gateway after payment is completed.
    """
    try:
        body = await request.body()
        # In production: parse and verify WeChat callback XML/JSON
        callback_data = {"raw": body.decode("utf-8", errors="replace")}
        
        payment_service = PaymentService(db)
        result = await payment_service.handle_payment_callback("wechat", callback_data)
        
        return {"code": "SUCCESS", "message": "OK"}
    except Exception as e:
        return {"code": "FAIL", "message": str(e)}


@router.post("/callback/alipay")
async def alipay_payment_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    Alipay callback endpoint.
    
    Called by Alipay after payment is completed.
    """
    try:
        form_data = await request.form()
        callback_data = dict(form_data)
        
        payment_service = PaymentService(db)
        result = await payment_service.handle_payment_callback("alipay", callback_data)
        
        return "success"
    except Exception:
        return "fail"


@router.get("/orders/{order_id}")
async def get_order_status(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get payment order status."""
    # In production: look up order from database
    return {
        "order_id": order_id,
        "status": "pending",
        "message": "等待支付",
    }


@router.get("/methods")
async def list_payment_methods(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List available payment methods."""
    return {
        "methods": [
            {
                "id": "wechat",
                "name": "微信支付",
                "icon": "wechat",
                "enabled": True,
                "description": "扫码支付，即时到账",
            },
            {
                "id": "alipay",
                "name": "支付宝",
                "icon": "alipay",
                "enabled": True,
                "description": "支付宝扫码或登录支付",
            },
            {
                "id": "manual",
                "name": "对公转账",
                "icon": "bank",
                "enabled": True,
                "description": "银行转账，1-2个工作日到账",
            },
        ],
    }
