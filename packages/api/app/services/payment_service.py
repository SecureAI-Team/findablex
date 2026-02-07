"""
Payment Service - Manual QR code payment flow.

Since individual merchants cannot directly access WeChat Pay / Alipay APIs,
this service implements a manual payment flow:

1. User selects plan → backend creates Order record
2. Frontend shows personal WeChat/Alipay QR code
3. User scans, pays, and clicks "I've paid"
4. Admin verifies payment receipt and activates subscription

Payment flow:
  [User] → Create Order → See QR Code → Pay → Confirm Payment
  [Admin] → Review pending orders → Verify receipt → Activate subscription
"""
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.order import Order
from app.models.subscription import Subscription, PLANS

logger = logging.getLogger(__name__)


class PaymentService:
    """Payment processing service with manual QR code flow."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_order(
        self,
        workspace_id: UUID,
        user_id: UUID,
        plan_code: str,
        billing_cycle: str = "monthly",
        payment_method: str = "wechat",
    ) -> Dict[str, Any]:
        """
        Create a payment order and return QR code info.
        
        Persists the order to the database for tracking.
        """
        if plan_code not in PLANS:
            raise ValueError(f"Invalid plan code: {plan_code}")
        
        plan = PLANS[plan_code]
        price = plan["price_yearly"] if billing_cycle == "yearly" else plan["price_monthly"]
        
        if price <= 0:
            raise ValueError("Cannot create order for free plan")
        
        # Check for existing pending order (avoid duplicates)
        existing = await self.db.execute(
            select(Order).where(
                and_(
                    Order.workspace_id == workspace_id,
                    Order.plan_code == plan_code,
                    Order.status == "pending",
                    Order.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        existing_order = existing.scalar_one_or_none()
        
        if existing_order:
            # Return existing pending order
            return self._order_to_dict(existing_order, plan)
        
        # Generate order number
        order_no = f"FX{int(time.time())}{uuid.uuid4().hex[:8].upper()}"
        
        # Create and persist order
        order = Order(
            order_no=order_no,
            workspace_id=workspace_id,
            user_id=user_id,
            plan_code=plan_code,
            billing_cycle=billing_cycle,
            amount=price,
            payment_method=payment_method,
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        
        logger.info(
            f"Order created: {order_no}, workspace={workspace_id}, "
            f"plan={plan_code}, amount={price}"
        )
        
        # Track analytics
        try:
            from app.services.analytics_service import AnalyticsService
            analytics = AnalyticsService(self.db)
            await analytics.track_event(
                "payment_order_created",
                user_id=user_id,
                workspace_id=workspace_id,
                properties={
                    "order_no": order_no,
                    "plan": plan_code,
                    "amount": price,
                    "payment_method": payment_method,
                },
            )
        except Exception:
            pass
        
        return self._order_to_dict(order, plan)
    
    def _order_to_dict(self, order: Order, plan: dict = None) -> Dict[str, Any]:
        """Convert order to API response dict."""
        if plan is None:
            plan = PLANS.get(order.plan_code, PLANS["free"])
        
        return {
            "order_id": order.order_no,
            "workspace_id": str(order.workspace_id),
            "user_id": str(order.user_id) if order.user_id else None,
            "plan_code": order.plan_code,
            "plan_name": plan["name"],
            "billing_cycle": order.billing_cycle,
            "amount": order.amount,
            "currency": "CNY",
            "payment_method": order.payment_method,
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "expires_at": order.expires_at.isoformat() if order.expires_at else None,
            "payment_data": self._get_payment_data(order),
        }
    
    def _get_payment_data(self, order: Order) -> Dict[str, Any]:
        """Return payment instructions with QR code info."""
        base_data = {
            "order_no": order.order_no,
            "amount": order.amount,
            "note": f"FindableX升级-{order.order_no}",
        }
        
        if order.payment_method == "wechat":
            return {
                **base_data,
                "type": "wechat_qrcode",
                "qr_image": "/wechat-qrcode.jpg",
                "instructions": (
                    f"请使用微信扫描收款码，支付 ¥{order.amount}，"
                    f"并在付款备注中填写订单号：{order.order_no}"
                ),
            }
        elif order.payment_method == "alipay":
            return {
                **base_data,
                "type": "alipay_qrcode",
                "qr_image": "/alipay-qrcode.jpg",
                "instructions": (
                    f"请使用支付宝扫描收款码，支付 ¥{order.amount}，"
                    f"并在付款备注中填写订单号：{order.order_no}"
                ),
            }
        else:
            return {
                **base_data,
                "type": "bank_transfer",
                "instructions": (
                    f"请通过银行转账支付 ¥{order.amount}，"
                    f"并在转账备注中填写订单号：{order.order_no}"
                ),
                "contact_email": "support@findablex.com",
            }
    
    async def confirm_payment(
        self,
        order_no: str,
        user_id: UUID,
        user_note: str = "",
    ) -> Dict[str, Any]:
        """
        User confirms they've completed payment.
        
        Sets status to 'paid_unverified' and waits for admin activation.
        """
        result = await self.db.execute(
            select(Order).where(
                and_(
                    Order.order_no == order_no,
                    Order.user_id == user_id,
                )
            )
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise ValueError("Order not found")
        
        if order.status not in ("pending", "paid_unverified"):
            raise ValueError(f"Order status is {order.status}, cannot confirm payment")
        
        order.status = "paid_unverified"
        order.paid_at = datetime.now(timezone.utc)
        order.user_note = user_note or ""
        
        await self.db.commit()
        await self.db.refresh(order)
        
        logger.info(f"Payment confirmed by user for order {order_no}")
        
        # Notify admin (via notification service)
        try:
            from app.services.notification_service import NotificationService
            ns = NotificationService(self.db)
            await ns.create_in_app_notification(
                user_id=user_id,  # Will be shown to admin
                notification_type="payment_received",
                title=f"新付款确认: {order_no}",
                message=(
                    f"用户确认已支付 ¥{order.amount} ({order.plan_code} 套餐)。"
                    f"{'备注: ' + user_note if user_note else '请尽快核实并激活。'}"
                ),
                data={"order_no": order_no},
            )
        except Exception as e:
            logger.warning(f"Failed to send payment notification: {e}")
        
        return {
            "order_no": order.order_no,
            "status": order.status,
            "message": "付款确认已提交，我们将在 1-2 个工作日内核实并为您开通服务。",
        }
    
    async def get_order(self, order_no: str) -> Optional[Dict[str, Any]]:
        """Get order details by order number."""
        result = await self.db.execute(
            select(Order).where(Order.order_no == order_no)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        return self._order_to_dict(order)
    
    async def list_orders(
        self,
        workspace_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List orders, optionally filtered by workspace and status."""
        query = select(Order).order_by(desc(Order.created_at)).limit(limit)
        
        if workspace_id:
            query = query.where(Order.workspace_id == workspace_id)
        if status:
            query = query.where(Order.status == status)
        
        result = await self.db.execute(query)
        orders = result.scalars().all()
        
        return [self._order_to_dict(o) for o in orders]
    
    async def activate_order(
        self,
        order_no: str,
        admin_note: str = "",
    ) -> Dict[str, Any]:
        """
        Admin activates an order → creates/upgrades subscription.
        """
        result = await self.db.execute(
            select(Order).where(Order.order_no == order_no)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise ValueError("Order not found")
        
        if order.status == "activated":
            raise ValueError("Order already activated")
        
        # Activate subscription
        subscription = await self.activate_subscription(
            workspace_id=order.workspace_id,
            plan_code=order.plan_code,
            billing_cycle=order.billing_cycle,
            payment_method=order.payment_method,
            order_no=order.order_no,
        )
        
        # Update order status
        order.status = "activated"
        order.activated_at = datetime.now(timezone.utc)
        order.admin_note = admin_note
        
        await self.db.commit()
        
        logger.info(f"Order {order_no} activated, subscription updated")
        
        return {
            "order_no": order.order_no,
            "status": "activated",
            "subscription_plan": subscription.plan_code,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
        }
    
    async def activate_subscription(
        self,
        workspace_id: UUID,
        plan_code: str,
        billing_cycle: str = "monthly",
        months: int = 1,
        payment_method: str = "wechat",
        order_no: Optional[str] = None,
    ) -> Subscription:
        """Activate or upgrade a subscription after payment confirmation."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.workspace_id == workspace_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            subscription = Subscription(workspace_id=workspace_id)
            self.db.add(subscription)
        
        # Calculate period
        if billing_cycle == "yearly":
            period_days = 365
        else:
            period_days = 30 * months
        
        subscription.plan_code = plan_code
        subscription.status = "active"
        subscription.billing_cycle = billing_cycle
        subscription.started_at = datetime.now(timezone.utc)
        subscription.expires_at = datetime.now(timezone.utc) + timedelta(days=period_days)
        subscription.last_payment_at = datetime.now(timezone.utc)
        subscription.payment_method = payment_method
        
        # Reset monthly usage
        subscription.usage = {
            "runs_this_month": 0,
            "queries_created": 0,
            "reports_generated": 0,
            "last_reset_at": datetime.now(timezone.utc).isoformat(),
        }
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(
            f"Subscription activated: workspace={workspace_id}, "
            f"plan={plan_code}, expires={subscription.expires_at}"
        )
        
        return subscription
