"""Email service for sending transactional emails."""
import logging
from typing import Optional

from app.config import settings, dynamic

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails.
    
    In development mode, emails are logged rather than sent.
    In production, configure SMTP or use a service like SendGrid.
    """
    
    def __init__(self):
        self.is_production = settings.is_production
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email.
        
        Returns True if email was sent successfully, False otherwise.
        """
        if not self.is_production:
            # In development, just log the email
            logger.info(f"[EMAIL] To: {to_email}")
            logger.info(f"[EMAIL] Subject: {subject}")
            logger.info(f"[EMAIL] Content:\n{text_content or html_content[:500]}")
            return True
        
        # In production, send via SMTP or email service
        try:
            # Get email configuration from dynamic settings
            smtp_host = await dynamic.get("email.smtp_host")
            smtp_port = await dynamic.get("email.smtp_port", 587)
            smtp_user = await dynamic.get("email.smtp_user")
            smtp_password = await dynamic.get("email.smtp_password")
            from_address = await dynamic.get("email.from_address", "noreply@findablex.com")
            
            if not smtp_host or not smtp_user:
                logger.warning("SMTP not configured, email not sent")
                return False
            
            # TODO: Implement actual SMTP sending
            # For now, just log
            logger.info(f"[EMAIL] Would send to: {to_email}, subject: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """Send password reset email."""
        # Build reset URL
        base_url = settings.allowed_origins.split(",")[0].strip()
        reset_url = f"{base_url}/reset-password?token={reset_token}"
        
        subject = "[FindableX] 重置您的密码"
        
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
                    <h2 style="color: #1e293b; margin-bottom: 16px;">重置您的密码</h2>
                    <p style="color: #475569;">您好{f' {user_name}' if user_name else ''}，</p>
                    <p style="color: #475569;">我们收到了重置您密码的请求。点击下面的按钮设置新密码：</p>
                    <a href="{reset_url}" class="button">重置密码</a>
                    <p style="color: #475569;">如果您没有请求重置密码，请忽略此邮件。</p>
                    <p style="color: #94a3b8; font-size: 14px;">此链接将在 24 小时后失效。</p>
                </div>
                <div class="footer">
                    <p>© 2026 FindableX. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
重置您的密码

您好{f' {user_name}' if user_name else ''}，

我们收到了重置您密码的请求。请访问以下链接设置新密码：

{reset_url}

如果您没有请求重置密码，请忽略此邮件。

此链接将在 24 小时后失效。

---
FindableX
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_welcome_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """Send welcome email to new users."""
        base_url = settings.allowed_origins.split(",")[0].strip()
        login_url = f"{base_url}/login"
        
        subject = "欢迎加入 FindableX！"
        
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
                .button {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 20px 0; }}
                .feature {{ display: flex; align-items: center; margin: 12px 0; }}
                .check {{ color: #22c55e; margin-right: 8px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #94a3b8; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">FindableX</div>
                </div>
                <div class="content">
                    <h2 style="color: #1e293b; margin-bottom: 16px;">欢迎加入 FindableX！</h2>
                    <p style="color: #475569;">您好{f' {user_name}' if user_name else ''}，</p>
                    <p style="color: #475569;">感谢您注册 FindableX，您的 GEO 优化之旅即将开始！</p>
                    
                    <p style="color: #475569; margin-top: 20px;">您现在可以：</p>
                    <div class="feature"><span class="check">✓</span> 创建项目并导入数据</div>
                    <div class="feature"><span class="check">✓</span> 分析品牌在 AI 搜索中的可见性</div>
                    <div class="feature"><span class="check">✓</span> 获取优化建议提升排名</div>
                    
                    <a href="{login_url}" class="button">开始使用</a>
                </div>
                <div class="footer">
                    <p>© 2026 FindableX. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
欢迎加入 FindableX！

您好{f' {user_name}' if user_name else ''}，

感谢您注册 FindableX，您的 GEO 优化之旅即将开始！

您现在可以：
✓ 创建项目并导入数据
✓ 分析品牌在 AI 搜索中的可见性
✓ 获取优化建议提升排名

登录地址：{login_url}

---
FindableX
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_invite_email(
        self,
        to_email: str,
        workspace_name: str,
        inviter_name: str,
        role: str,
    ) -> bool:
        """Send workspace invitation email."""
        base_url = settings.allowed_origins.split(",")[0].strip()
        login_url = f"{base_url}/login"
        
        role_labels = {
            "admin": "管理员",
            "analyst": "分析师",
            "researcher": "研究员",
            "viewer": "查看者",
        }
        role_label = role_labels.get(role, role)
        
        subject = f"[FindableX] {inviter_name} 邀请您加入 {workspace_name}"
        
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
                .button {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 20px 0; }}
                .highlight {{ background: #eef2ff; padding: 16px; border-radius: 8px; margin: 16px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #94a3b8; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">FindableX</div>
                </div>
                <div class="content">
                    <h2 style="color: #1e293b; margin-bottom: 16px;">您收到一份邀请</h2>
                    <p style="color: #475569;"><strong>{inviter_name}</strong> 邀请您以 <strong>{role_label}</strong> 身份加入工作空间：</p>
                    
                    <div class="highlight">
                        <strong style="color: #1e293b;">{workspace_name}</strong>
                    </div>
                    
                    <p style="color: #475569;">登录您的账户即可开始协作。</p>
                    
                    <a href="{login_url}" class="button">接受邀请</a>
                </div>
                <div class="footer">
                    <p>© 2026 FindableX. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
您收到一份邀请

{inviter_name} 邀请您以 {role_label} 身份加入工作空间：{workspace_name}

登录您的账户即可开始协作：{login_url}

---
FindableX
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)


    async def send_drift_warning_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
        project_name: str = "",
        drift_events: list = None,
    ) -> bool:
        """Send drift warning email when significant metric changes are detected."""
        base_url = settings.allowed_origins.split(",")[0].strip()
        project_url = f"{base_url}/projects"
        
        drift_events = drift_events or []
        
        # Build drift summary
        severity_emoji = {"critical": "🔴", "warning": "🟡"}
        drift_items = ""
        for event in drift_events[:5]:
            emoji = severity_emoji.get(event.get("severity", "warning"), "🟡")
            metric = event.get("metric_name", "未知")
            change = event.get("change_percent", 0)
            drift_items += f'<div style="margin: 8px 0;">{emoji} {metric}: {change:+.1f}%</div>'
        
        subject = f"[FindableX] ⚠️ 项目「{project_name}」检测到指标漂移"
        
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
                .alert {{ background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 16px; margin: 16px 0; }}
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
                    <h2 style="color: #1e293b; margin-bottom: 16px;">⚠️ 指标漂移警告</h2>
                    <p style="color: #475569;">您好{f' {user_name}' if user_name else ''}，</p>
                    <p style="color: #475569;">您的项目「<strong>{project_name}</strong>」检测到以下指标发生显著变化：</p>
                    
                    <div class="alert">
                        {drift_items}
                    </div>
                    
                    <p style="color: #475569;">建议您查看详细报告并采取相应措施。</p>
                    
                    <a href="{project_url}" class="button">查看项目详情</a>
                </div>
                <div class="footer">
                    <p>© 2026 FindableX. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
指标漂移警告

您好{f' {user_name}' if user_name else ''}，

您的项目「{project_name}」检测到指标漂移。

建议您登录查看详细报告：{project_url}

---
FindableX
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_retest_reminder_email(
        self,
        to_email: str,
        user_name: Optional[str] = None,
        project_name: str = "",
        days_until_retest: int = 0,
        last_test_date: str = "",
    ) -> bool:
        """Send retest reminder email."""
        base_url = settings.allowed_origins.split(",")[0].strip()
        project_url = f"{base_url}/projects"
        
        if days_until_retest <= 0:
            subject = f"[FindableX] 📅 项目「{project_name}」已到复测时间"
            reminder_text = "已到复测时间"
        elif days_until_retest == 1:
            subject = f"[FindableX] 📅 项目「{project_name}」明天需要复测"
            reminder_text = "明天到期"
        else:
            subject = f"[FindableX] 📅 项目「{project_name}」{days_until_retest} 天后需要复测"
            reminder_text = f"{days_until_retest} 天后到期"
        
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
                .highlight {{ background: #eef2ff; padding: 16px; border-radius: 8px; margin: 16px 0; text-align: center; }}
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
                    <h2 style="color: #1e293b; margin-bottom: 16px;">📅 复测提醒</h2>
                    <p style="color: #475569;">您好{f' {user_name}' if user_name else ''}，</p>
                    <p style="color: #475569;">您的项目「<strong>{project_name}</strong>」{reminder_text}。</p>
                    
                    <div class="highlight">
                        <p style="color: #6366f1; font-weight: bold; font-size: 18px; margin: 0;">
                            上次体检: {last_test_date}
                        </p>
                    </div>
                    
                    <p style="color: #475569;">定期复测可以帮助您追踪 AI 搜索中品牌可见性的变化，及时发现竞品动态和引擎漂移。</p>
                    
                    <a href="{project_url}" class="button">立即复测</a>
                </div>
                <div class="footer">
                    <p>AI 引擎会漂移、竞品会动作、标准会更新 — 持续对齐生成式生态</p>
                    <p>© 2026 FindableX. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
复测提醒

您好{f' {user_name}' if user_name else ''}，

您的项目「{project_name}」{reminder_text}。
上次体检: {last_test_date}

定期复测可以帮助您追踪 AI 搜索中品牌可见性的变化。

登录复测：{project_url}

---
FindableX
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)


# Global email service instance
email_service = EmailService()
