"""Payment API endpoints for subscription billing.

Implements a manual QR code payment flow:
1. POST /orders - Create an upgrade order
2. POST /orders/{order_no}/confirm - User confirms payment
3. GET /orders/{order_no} - Check order status
4. POST /orders/{order_no}/activate - Admin activates subscription
5. GET /orders - List orders (admin)
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_current_superuser, get_db
from app.models.user import User
from app.services.payment_service import PaymentService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# ========== Schemas ==========

class CreateOrderRequest(BaseModel):
    """Request to create a payment order."""
    plan_code: str
    billing_cycle: str = "monthly"  # monthly or yearly
    payment_method: str = "wechat"  # wechat, alipay, bank_transfer


class ConfirmPaymentRequest(BaseModel):
    """User confirms they've completed payment."""
    user_note: str = ""


class ActivateOrderRequest(BaseModel):
    """Admin activates an order."""
    admin_note: str = ""


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
    
    Returns order details with QR code payment info.
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


@router.post("/orders/{order_no}/confirm")
async def confirm_payment(
    order_no: str,
    data: ConfirmPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    User confirms they've completed payment.
    
    Moves order to 'paid_unverified' status for admin review.
    """
    payment_service = PaymentService(db)
    
    try:
        result = await payment_service.confirm_payment(
            order_no=order_no,
            user_id=current_user.id,
            user_note=data.user_note,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/{order_no}")
async def get_order_status(
    order_no: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get payment order status."""
    payment_service = PaymentService(db)
    order = await payment_service.get_order(order_no)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Non-admin can only see their own orders
    if not current_user.is_superuser and order.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return order


@router.get("/orders")
async def list_orders(
    order_status: Optional[str] = None,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List all orders (admin only)."""
    payment_service = PaymentService(db)
    orders = await payment_service.list_orders(status=order_status)
    
    return {"orders": orders, "total": len(orders)}


@router.post("/orders/{order_no}/activate")
async def activate_order(
    order_no: str,
    data: ActivateOrderRequest,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Admin activates an order and upgrades the subscription.
    """
    payment_service = PaymentService(db)
    
    try:
        result = await payment_service.activate_order(
            order_no=order_no,
            admin_note=data.admin_note,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
                "description": "微信扫码支付",
            },
            {
                "id": "alipay",
                "name": "支付宝",
                "icon": "alipay",
                "enabled": True,
                "description": "支付宝扫码支付",
            },
            {
                "id": "bank_transfer",
                "name": "对公转账",
                "icon": "bank",
                "enabled": True,
                "description": "银行转账，1-2 个工作日到账",
            },
        ],
    }
