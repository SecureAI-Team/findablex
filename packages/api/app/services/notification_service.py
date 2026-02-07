"""
Notification Service - Unified notification management.

Handles sending notifications via multiple channels:
- Email (via EmailService)
- In-app notifications (stored in DB)
- Future: Webhook (企业微信/钉钉), SMS

Notification types:
- checkup_completed: GEO checkup finished
- drift_warning: Metric drift detected
- retest_reminder: Scheduled retest reminder
- weekly_digest: Weekly summary report
- quota_warning: Usage approaching limit
- renewal_reminder: Subscription expiring
- welcome: New user welcome
- team_invite: Team invitation
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.email_service import email_service

logger = logging.getLogger(__name__)


# Notification type definitions
NOTIFICATION_TYPES = {
    "checkup_completed": {
        "title": "体检完成",
        "description": "GEO 体检已完成",
        "channel": ["email", "in_app"],
        "preference_key": "checkup_completed",
    },
    "drift_warning": {
        "title": "漂移预警",
        "description": "检测到指标显著变化",
        "channel": ["email", "in_app"],
        "preference_key": "drift_warning",
    },
    "retest_reminder": {
        "title": "复测提醒",
        "description": "项目需要复测",
        "channel": ["email", "in_app"],
        "preference_key": "retest_reminder",
    },
    "weekly_digest": {
        "title": "每周摘要",
        "description": "每周 AI 可见性变化摘要",
        "channel": ["email"],
        "preference_key": "weekly_digest",
    },
    "quota_warning": {
        "title": "用量提醒",
        "description": "使用量接近限额",
        "channel": ["email", "in_app"],
        "preference_key": "quota_warning",
    },
    "renewal_reminder": {
        "title": "续费提醒",
        "description": "订阅即将到期",
        "channel": ["email", "in_app"],
        "preference_key": "renewal_reminder",
    },
}

# Default notification preferences for new users
DEFAULT_PREFERENCES = {
    "checkup_completed": True,
    "drift_warning": True,
    "retest_reminder": True,
    "weekly_digest": False,
    "quota_warning": True,
    "renewal_reminder": True,
    "marketing": False,
}


class NotificationService:
    """
    Unified notification service.
    
    Coordinates sending notifications through multiple channels
    while respecting user preferences.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_preferences(self, user_id: UUID) -> Dict[str, bool]:
        """
        Get notification preferences for a user.
        
        Returns default preferences if user hasn't set any.
        """
        from app.models.user import User
        
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return DEFAULT_PREFERENCES.copy()
        
        # Notification preferences are stored in a JSON column or separate table
        # For now, use defaults - will be saved per-user once the model is updated
        return DEFAULT_PREFERENCES.copy()
    
    async def update_user_preferences(
        self,
        user_id: UUID,
        preferences: Dict[str, bool],
    ) -> Dict[str, bool]:
        """Update notification preferences for a user."""
        # Validate preference keys
        valid_keys = set(DEFAULT_PREFERENCES.keys())
        updated = {}
        for key, value in preferences.items():
            if key in valid_keys:
                updated[key] = bool(value)
        
        # In a full implementation, store in DB
        # For now, merge with defaults
        result = DEFAULT_PREFERENCES.copy()
        result.update(updated)
        return result
    
    async def create_in_app_notification(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Create an in-app notification stored in the database.
        
        Returns the created Notification object or None on failure.
        """
        import json
        from app.models.notification import Notification
        
        try:
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message,
                link=link,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)
            logger.info(f"Created in-app notification: {notification_type} for user {user_id}")
            return notification
        except Exception as e:
            logger.error(f"Failed to create in-app notification: {e}")
            await self.db.rollback()
            return None
    
    async def _send_notification(
        self,
        user_id: UUID,
        user_email: str,
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        email_subject: Optional[str] = None,
        email_html: Optional[str] = None,
        email_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Internal helper: send notification through configured channels.
        
        Checks user preferences, creates in-app notification, and sends email
        if the notification type supports it.
        """
        type_config = NOTIFICATION_TYPES.get(notification_type, {})
        channels = type_config.get("channel", ["in_app"])
        
        success = True
        
        # In-app notification
        if "in_app" in channels:
            await self.create_in_app_notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
                metadata=metadata,
            )
        
        # Email notification
        if "email" in channels and email_html:
            email_ok = await email_service.send_email(
                user_email,
                email_subject or f"[FindableX] {title}",
                email_html,
                email_text,
            )
            if not email_ok:
                success = False
        
        return success
    
    async def send_checkup_completed(
        self,
        user_id: UUID,
        user_email: str,
        user_name: Optional[str],
        project_name: str,
        project_id: str,
        health_score: Optional[float] = None,
        engines_used: List[str] = None,
    ) -> bool:
        """Send checkup completed notification (in-app + email)."""
        from app.config import settings
        base_url = settings.allowed_origins.split(",")[0].strip()
        project_url = f"{base_url}/projects/{project_id}"
        
        engines_text = ", ".join(engines_used) if engines_used else "多个引擎"
        score_text = f"{health_score}分" if health_score is not None else "已生成"
        
        subject = f"[FindableX] 项目「{project_name}」体检完成"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #6366f1; }}
                .content {{ background: #f8fafc; border-radius: 12px; padding: 30px; }}
                .score {{ text-align: center; margin: 20px 0; }}
                .score-value {{ font-size: 48px; font-weight: bold; color: #22c55e; }}
                .button {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #94a3b8; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">FindableX</div>
                </div>
                <div class="content">
                    <h2 style="color: #1e293b; margin-bottom: 16px;">体检完成！</h2>
                    <p style="color: #475569;">您好{f' {user_name}' if user_name else ''}，</p>
                    <p style="color: #475569;">您的项目「<strong>{project_name}</strong>」已完成 GEO 体检。</p>
                    
                    <div class="score">
                        <div class="score-value">{score_text}</div>
                        <p style="color: #94a3b8;">使用引擎: {engines_text}</p>
                    </div>
                    
                    <a href="{project_url}" class="button">查看详细报告</a>
                </div>
                <div class="footer">
                    <p>© 2026 FindableX. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
体检完成！

项目「{project_name}」已完成 GEO 体检。
健康度: {score_text}
使用引擎: {engines_text}

查看报告: {project_url}

---
FindableX
        """
        
        return await self._send_notification(
            user_id=user_id,
            user_email=user_email,
            notification_type="checkup_completed",
            title=f"项目「{project_name}」体检完成",
            message=f"健康度: {score_text}，使用引擎: {engines_text}",
            link=f"/projects/{project_id}",
            email_subject=subject,
            email_html=html_content,
            email_text=text_content,
            metadata={"project_id": project_id, "health_score": health_score},
        )
    
    async def send_quota_warning(
        self,
        user_id: UUID,
        user_email: str,
        user_name: Optional[str],
        usage_percent: float,
        used: int,
        limit: int,
        resource_type: str = "runs",
    ) -> bool:
        """Send quota warning when usage is approaching limit."""
        from app.config import settings
        base_url = settings.allowed_origins.split(",")[0].strip()
        upgrade_url = f"{base_url}/subscription"
        
        resource_labels = {
            "runs": "运行次数",
            "projects": "项目数量",
            "queries": "查询词数量",
        }
        resource_label = resource_labels.get(resource_type, resource_type)
        
        subject = f"[FindableX] 用量提醒: {resource_label}已使用 {usage_percent:.0f}%"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #6366f1; }}
                .content {{ background: #f8fafc; border-radius: 12px; padding: 30px; }}
                .progress {{ background: #e2e8f0; border-radius: 8px; height: 12px; margin: 16px 0; overflow: hidden; }}
                .progress-bar {{ background: {'#ef4444' if usage_percent >= 90 else '#f59e0b'}; height: 100%; border-radius: 8px; }}
                .button {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #94a3b8; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">FindableX</div>
                </div>
                <div class="content">
                    <h2 style="color: #1e293b; margin-bottom: 16px;">用量提醒</h2>
                    <p style="color: #475569;">您好{f' {user_name}' if user_name else ''}，</p>
                    <p style="color: #475569;">您的{resource_label}已使用 <strong>{used}/{limit}</strong>，达到 {usage_percent:.0f}%。</p>
                    
                    <div class="progress">
                        <div class="progress-bar" style="width: {min(usage_percent, 100)}%"></div>
                    </div>
                    
                    <p style="color: #475569;">升级套餐可以获得更多用量和高级功能。</p>
                    
                    <a href="{upgrade_url}" class="button">升级套餐</a>
                </div>
                <div class="footer">
                    <p>© 2026 FindableX. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
用量提醒

您的{resource_label}已使用 {used}/{limit}，达到 {usage_percent:.0f}%。

升级套餐可以获得更多用量: {upgrade_url}

---
FindableX
        """
        
        return await self._send_notification(
            user_id=user_id,
            user_email=user_email,
            notification_type="quota_warning",
            title=f"用量提醒: {resource_label}已使用 {usage_percent:.0f}%",
            message=f"您的{resource_label}已使用 {used}/{limit}，升级套餐可获得更多用量。",
            link="/subscription",
            email_subject=subject,
            email_html=html_content,
            email_text=text_content,
            metadata={"usage_percent": usage_percent, "used": used, "limit": limit, "resource_type": resource_type},
        )
    
    async def send_renewal_reminder(
        self,
        user_id: UUID,
        user_email: str,
        user_name: Optional[str],
        plan_name: str,
        expires_at: str,
        days_until_expiry: int,
    ) -> bool:
        """Send subscription renewal reminder."""
        from app.config import settings
        base_url = settings.allowed_origins.split(",")[0].strip()
        subscription_url = f"{base_url}/subscription"
        
        if days_until_expiry <= 0:
            subject = f"[FindableX] 您的 {plan_name} 订阅已过期"
            urgency_text = "已过期"
        elif days_until_expiry <= 3:
            subject = f"[FindableX] 紧急: {plan_name} 订阅即将在 {days_until_expiry} 天后到期"
            urgency_text = f"将在 {days_until_expiry} 天后到期"
        else:
            subject = f"[FindableX] {plan_name} 订阅将在 {days_until_expiry} 天后到期"
            urgency_text = f"将在 {days_until_expiry} 天后到期"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #6366f1; }}
                .content {{ background: #f8fafc; border-radius: 12px; padding: 30px; }}
                .alert {{ background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin: 16px 0; text-align: center; }}
                .button {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #94a3b8; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">FindableX</div>
                </div>
                <div class="content">
                    <h2 style="color: #1e293b; margin-bottom: 16px;">续费提醒</h2>
                    <p style="color: #475569;">您好{f' {user_name}' if user_name else ''}，</p>
                    
                    <div class="alert">
                        <p style="color: #92400e; font-weight: bold; font-size: 18px; margin: 0;">
                            {plan_name} 订阅{urgency_text}
                        </p>
                        <p style="color: #92400e; margin: 8px 0 0 0;">到期日: {expires_at}</p>
                    </div>
                    
                    <p style="color: #475569;">续费后可继续使用所有高级功能，数据不会丢失。</p>
                    
                    <a href="{subscription_url}" class="button">立即续费</a>
                </div>
                <div class="footer">
                    <p>© 2026 FindableX. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
续费提醒

您的 {plan_name} 订阅{urgency_text}。
到期日: {expires_at}

续费后可继续使用所有高级功能: {subscription_url}

---
FindableX
        """
        
        return await self._send_notification(
            user_id=user_id,
            user_email=user_email,
            notification_type="renewal_reminder",
            title=f"{plan_name} 订阅{urgency_text}",
            message=f"您的 {plan_name} 订阅{urgency_text}，到期日: {expires_at}。",
            link="/subscription",
            email_subject=subject,
            email_html=html_content,
            email_text=text_content,
            metadata={"plan_name": plan_name, "expires_at": expires_at, "days_until_expiry": days_until_expiry},
        )
    
    async def send_weekly_digest(
        self,
        user_email: str,
        user_name: Optional[str],
        digest_data: Dict[str, Any],
    ) -> bool:
        """Send weekly digest email with AI visibility summary."""
        from app.config import settings
        base_url = settings.allowed_origins.split(",")[0].strip()
        dashboard_url = f"{base_url}/dashboard"
        
        projects_summary = digest_data.get("projects", [])
        total_projects = digest_data.get("total_projects", 0)
        total_runs = digest_data.get("total_runs_this_week", 0)
        avg_health = digest_data.get("avg_health_score", "--")
        
        # Build project rows
        project_rows = ""
        for p in projects_summary[:5]:
            score = p.get("health_score", "--")
            change = p.get("score_change", 0)
            change_text = f'+{change}' if change > 0 else str(change) if change != 0 else '--'
            change_color = '#22c55e' if change > 0 else '#ef4444' if change < 0 else '#94a3b8'
            project_rows += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #1e293b;">{p.get('name', '')}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: #1e293b; text-align: center;">{score}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e2e8f0; color: {change_color}; text-align: center;">{change_text}</td>
            </tr>
            """
        
        subject = f"[FindableX] 每周 AI 可见性报告 - {total_projects} 个项目概览"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #6366f1; }}
                .content {{ background: #f8fafc; border-radius: 12px; padding: 30px; }}
                .stats {{ display: flex; gap: 16px; margin: 20px 0; }}
                .stat {{ flex: 1; background: white; border-radius: 8px; padding: 16px; text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #1e293b; }}
                .stat-label {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
                .button {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #94a3b8; font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
                th {{ padding: 8px; text-align: left; color: #64748b; font-size: 12px; border-bottom: 2px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">FindableX</div>
                </div>
                <div class="content">
                    <h2 style="color: #1e293b; margin-bottom: 16px;">每周 AI 可见性报告</h2>
                    <p style="color: #475569;">您好{f' {user_name}' if user_name else ''}，以下是本周的 AI 可见性概览：</p>
                    
                    <table style="width: 100%; margin: 20px 0;">
                        <tr>
                            <td style="text-align: center; padding: 12px; background: white; border-radius: 8px;">
                                <div style="font-size: 24px; font-weight: bold; color: #6366f1;">{total_projects}</div>
                                <div style="font-size: 12px; color: #94a3b8;">活跃项目</div>
                            </td>
                            <td style="width: 12px;"></td>
                            <td style="text-align: center; padding: 12px; background: white; border-radius: 8px;">
                                <div style="font-size: 24px; font-weight: bold; color: #22c55e;">{total_runs}</div>
                                <div style="font-size: 12px; color: #94a3b8;">本周体检</div>
                            </td>
                            <td style="width: 12px;"></td>
                            <td style="text-align: center; padding: 12px; background: white; border-radius: 8px;">
                                <div style="font-size: 24px; font-weight: bold; color: #f59e0b;">{avg_health}</div>
                                <div style="font-size: 12px; color: #94a3b8;">平均健康度</div>
                            </td>
                        </tr>
                    </table>
                    
                    {f'''
                    <table>
                        <thead>
                            <tr>
                                <th>项目</th>
                                <th style="text-align: center;">健康度</th>
                                <th style="text-align: center;">变化</th>
                            </tr>
                        </thead>
                        <tbody>
                            {project_rows}
                        </tbody>
                    </table>
                    ''' if project_rows else '<p style="color: #94a3b8; text-align: center;">本周暂无体检数据</p>'}
                    
                    <a href="{dashboard_url}" class="button">查看详细数据</a>
                </div>
                <div class="footer">
                    <p>AI 引擎会漂移、竞品会动作 — 持续对齐生成式生态</p>
                    <p>© 2026 FindableX. All rights reserved.</p>
                    <p style="font-size: 12px;">如不想收到此邮件，请在设置中关闭每周摘要</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
每周 AI 可见性报告

您好{f' {user_name}' if user_name else ''}，以下是本周概览：

活跃项目: {total_projects}
本周体检: {total_runs}
平均健康度: {avg_health}

查看详细数据: {dashboard_url}

---
FindableX
        """
        
        return await email_service.send_email(user_email, subject, html_content, text_content)
