"""
Bot integration service for Feishu (飞书) and WeCom (企业微信).

Sends notification messages to configured bot webhook URLs.
Used for:
  - Checkup completion alerts
  - Drift detection alerts
  - Weekly digest summaries

Configuration:
  Set webhook URLs in dynamic settings or per-workspace settings:
    - integrations.feishu_webhook_url
    - integrations.wecom_webhook_url
"""
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import dynamic

logger = logging.getLogger(__name__)


class BotService:
    """Sends messages to Feishu and WeCom bots."""
    
    @staticmethod
    async def send_feishu(
        webhook_url: str,
        title: str,
        content: str,
        extra_fields: Optional[List[Dict[str, str]]] = None,
    ) -> bool:
        """
        Send a card message to Feishu bot.
        
        Args:
            webhook_url: Feishu bot webhook URL
            title: Card title
            content: Main content text
            extra_fields: Optional list of {"tag": "text", "text": "..."} elements
        
        Returns:
            True if sent successfully
        """
        if not webhook_url:
            return False
        
        # Build Feishu Interactive Card
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": content,
                },
            }
        ]
        
        if extra_fields:
            fields = [
                {"is_short": True, "text": {"tag": "lark_md", "content": f["text"]}}
                for f in extra_fields
            ]
            elements.append({"tag": "div", "fields": fields})
        
        # Add action button
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看详情"},
                    "type": "primary",
                    "url": "https://findablex.com/dashboard",
                }
            ],
        })
        
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue",
                },
                "elements": elements,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(webhook_url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0 or data.get("StatusCode") == 0:
                        logger.info(f"Feishu message sent: {title}")
                        return True
                logger.warning(f"Feishu send failed: {response.status_code} {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Feishu send error: {e}")
            return False
    
    @staticmethod
    async def send_wecom(
        webhook_url: str,
        title: str,
        content: str,
    ) -> bool:
        """
        Send a markdown message to WeCom (企业微信) bot.
        
        Args:
            webhook_url: WeCom bot webhook URL
            title: Message title (included in markdown)
            content: Markdown content
        
        Returns:
            True if sent successfully
        """
        if not webhook_url:
            return False
        
        markdown_content = f"## {title}\n\n{content}\n\n[查看详情](https://findablex.com/dashboard)"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_content,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(webhook_url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errcode") == 0:
                        logger.info(f"WeCom message sent: {title}")
                        return True
                logger.warning(f"WeCom send failed: {response.status_code} {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"WeCom send error: {e}")
            return False
    
    @classmethod
    async def notify(
        cls,
        event_type: str,
        title: str,
        content: str,
        workspace_id: Optional[str] = None,
        workspace_settings: Optional[Dict] = None,
    ) -> Dict[str, bool]:
        """
        Send notification to all configured bots.
        
        Checks:
        1. Database BotIntegration records for the workspace (if workspace_id given)
        2. Global dynamic settings as fallback
        3. Explicit workspace_settings dict as override
        
        Returns:
            Dict of {platform: success} results
        """
        results = {}

        # Collect webhook URLs
        feishu_url = ""
        wecom_url = ""
        feishu_events: List[str] = []
        wecom_events: List[str] = []

        # 1. Try DB-based integrations
        if workspace_id:
            try:
                from sqlalchemy import select, and_
                from app.db.session import async_session_maker
                from app.models.bot_integration import BotIntegration

                async with async_session_maker() as db:
                    result = await db.execute(
                        select(BotIntegration).where(
                            and_(
                                BotIntegration.workspace_id == workspace_id,
                                BotIntegration.is_active == True,
                            )
                        )
                    )
                    bots = result.scalars().all()
                    for bot in bots:
                        if bot.platform == "feishu":
                            feishu_url = bot.webhook_url
                            feishu_events = bot.events or []
                        elif bot.platform == "wecom":
                            wecom_url = bot.webhook_url
                            wecom_events = bot.events or []
            except Exception as e:
                logger.warning(f"Failed to load bot integrations from DB: {e}")

        # 2. Fallback to global dynamic settings
        if not feishu_url:
            feishu_url = await dynamic.get("integrations.feishu_webhook_url", "")
        if not wecom_url:
            wecom_url = await dynamic.get("integrations.wecom_webhook_url", "")

        # 3. Override with explicit workspace_settings
        if workspace_settings:
            feishu_url = workspace_settings.get("feishu_webhook_url", feishu_url)
            wecom_url = workspace_settings.get("wecom_webhook_url", wecom_url)

        # Send to Feishu if URL is set and event is subscribed (or no DB config)
        if feishu_url and (not feishu_events or event_type in feishu_events):
            results["feishu"] = await cls.send_feishu(feishu_url, title, content)

        # Send to WeCom if URL is set and event is subscribed (or no DB config)
        if wecom_url and (not wecom_events or event_type in wecom_events):
            results["wecom"] = await cls.send_wecom(wecom_url, title, content)

        return results


async def notify_checkup_complete(
    project_name: str,
    health_score: float,
    workspace_settings: Optional[Dict] = None,
):
    """Helper: send checkup completion notification to bots."""
    emoji = "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
    await BotService.notify(
        event_type="checkup.completed",
        title=f"{emoji} 体检完成 - {project_name}",
        content=(
            f"**项目**: {project_name}\n"
            f"**健康度**: {health_score:.0f}/100\n"
            f"**状态**: {'优秀' if health_score >= 80 else '良好' if health_score >= 60 else '需改进'}"
        ),
        workspace_settings=workspace_settings,
    )


async def notify_drift_detected(
    project_name: str,
    metric_name: str,
    change_pct: float,
    workspace_settings: Optional[Dict] = None,
):
    """Helper: send drift detection alert to bots."""
    direction = "上升" if change_pct > 0 else "下降"
    await BotService.notify(
        event_type="drift.detected",
        title=f"⚠️ 指标漂移 - {project_name}",
        content=(
            f"**项目**: {project_name}\n"
            f"**指标**: {metric_name}\n"
            f"**变化**: {direction} {abs(change_pct):.1f}%"
        ),
        workspace_settings=workspace_settings,
    )
