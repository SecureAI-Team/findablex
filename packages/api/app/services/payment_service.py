"""
Payment Service - Handles payment processing and order management.

Supports:
- WeChat Pay (微信支付) - Native Pay (扫码支付)
- Alipay (支付宝) - PC payment
- Manual bank transfer (银行转账)

Payment flow:
1. User selects plan and clicks upgrade
2. Backend creates order and returns payment URL/QR code
3. User completes payment on WeChat/Alipay
4. Payment gateway sends callback notification
5. Backend verifies and activates subscription
"""
import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings, dynamic
from app.models.subscription import Subscription, PLANS

logger = logging.getLogger(__name__)


# Order statuses
ORDER_STATUS = {
    "pending": "待支付",
    "paid": "已支付",
    "activated": "已激活",
    "cancelled": "已取消",
    "refunded": "已退款",
    "expired": "已过期",
}


class PaymentService:
    """Payment processing service."""
    
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
        Create a payment order.
        
        Returns order details including payment URL or QR code data.
        """
        if plan_code not in PLANS:
            raise ValueError(f"Invalid plan code: {plan_code}")
        
        plan = PLANS[plan_code]
        price = plan["price_yearly"] if billing_cycle == "yearly" else plan["price_monthly"]
        
        if price <= 0:
            raise ValueError("Cannot create order for free plan")
        
        # Generate order ID
        order_id = f"FX{int(time.time())}{uuid.uuid4().hex[:8].upper()}"
        
        order = {
            "order_id": order_id,
            "workspace_id": str(workspace_id),
            "user_id": str(user_id),
            "plan_code": plan_code,
            "plan_name": plan["name"],
            "billing_cycle": billing_cycle,
            "amount": price,
            "currency": "CNY",
            "payment_method": payment_method,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        }
        
        # Generate payment-specific data
        if payment_method == "wechat":
            payment_data = await self._create_wechat_payment(order)
            order["payment_data"] = payment_data
        elif payment_method == "alipay":
            payment_data = await self._create_alipay_payment(order)
            order["payment_data"] = payment_data
        else:
            # Manual/bank transfer
            order["payment_data"] = {
                "type": "bank_transfer",
                "instructions": {
                    "bank_name": "招商银行",
                    "account_name": "某某科技有限公司",
                    "account_number": "6226-XXXX-XXXX-1234",
                    "note": f"请备注订单号: {order_id}",
                },
            }
        
        # In production, persist order to database
        # For now, we track via analytics
        try:
            from app.services.analytics_service import AnalyticsService
            analytics = AnalyticsService(self.db)
            await analytics.track_event(
                "payment_initiated",
                user_id=user_id,
                workspace_id=workspace_id,
                properties={
                    "order_id": order_id,
                    "plan": plan_code,
                    "amount": price,
                    "payment_method": payment_method,
                },
            )
        except Exception:
            pass
        
        return order
    
    async def _create_wechat_payment(self, order: Dict) -> Dict[str, Any]:
        """
        Create WeChat Pay native payment (扫码支付).
        
        In production, this would call WeChat Pay API to get a QR code URL.
        """
        # Get WeChat Pay configuration
        wechat_app_id = await dynamic.get("payment.wechat_app_id", "")
        wechat_mch_id = await dynamic.get("payment.wechat_mch_id", "")
        
        if not wechat_app_id or not wechat_mch_id:
            # WeChat Pay not configured, return placeholder
            return {
                "type": "wechat_native",
                "qr_code_url": None,
                "fallback": True,
                "message": "微信支付正在配置中，请联系客服完成支付",
                "contact_wechat": "FindableX_Sales",
                "contact_email": "sales@findablex.com",
            }
        
        # In production: call WeChat Pay unified order API
        # https://pay.weixin.qq.com/wiki/doc/apiv3/apis/chapter3_4_1.shtml
        return {
            "type": "wechat_native",
            "qr_code_url": f"weixin://wxpay/bizpayurl?pr={order['order_id']}",
            "expires_in": 7200,  # 2 hours
        }
    
    async def _create_alipay_payment(self, order: Dict) -> Dict[str, Any]:
        """
        Create Alipay PC payment.
        
        In production, this would generate an Alipay payment page URL.
        """
        alipay_app_id = await dynamic.get("payment.alipay_app_id", "")
        
        if not alipay_app_id:
            return {
                "type": "alipay",
                "payment_url": None,
                "fallback": True,
                "message": "支付宝支付正在配置中，请联系客服完成支付",
                "contact_email": "sales@findablex.com",
            }
        
        # In production: call Alipay trade page pay API
        return {
            "type": "alipay",
            "payment_url": f"https://openapi.alipay.com/gateway.do?order={order['order_id']}",
            "expires_in": 7200,
        }
    
    async def handle_payment_callback(
        self,
        payment_method: str,
        callback_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle payment gateway callback.
        
        Verifies the payment and activates the subscription.
        """
        if payment_method == "wechat":
            return await self._handle_wechat_callback(callback_data)
        elif payment_method == "alipay":
            return await self._handle_alipay_callback(callback_data)
        else:
            raise ValueError(f"Unknown payment method: {payment_method}")
    
    async def _handle_wechat_callback(self, data: Dict) -> Dict[str, Any]:
        """Handle WeChat Pay callback notification."""
        # In production:
        # 1. Verify signature
        # 2. Decrypt callback data
        # 3. Extract order info
        # 4. Activate subscription
        
        order_id = data.get("out_trade_no", "")
        transaction_id = data.get("transaction_id", "")
        
        if not order_id:
            return {"status": "error", "message": "Missing order_id"}
        
        logger.info(f"WeChat payment callback for order {order_id}, tx: {transaction_id}")
        
        # TODO: Look up order from database, verify amount, activate subscription
        return {"status": "success", "order_id": order_id}
    
    async def _handle_alipay_callback(self, data: Dict) -> Dict[str, Any]:
        """Handle Alipay callback notification."""
        order_id = data.get("out_trade_no", "")
        trade_no = data.get("trade_no", "")
        trade_status = data.get("trade_status", "")
        
        if trade_status != "TRADE_SUCCESS":
            return {"status": "pending", "message": f"Trade status: {trade_status}"}
        
        logger.info(f"Alipay payment callback for order {order_id}, trade: {trade_no}")
        
        # TODO: Verify signature, activate subscription
        return {"status": "success", "order_id": order_id}
    
    async def activate_subscription(
        self,
        workspace_id: UUID,
        plan_code: str,
        billing_cycle: str = "monthly",
        months: int = 1,
        payment_method: str = "wechat",
        order_id: Optional[str] = None,
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
