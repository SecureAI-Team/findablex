"""
Weekly digest service – generates and sends weekly AI visibility summaries.

Triggered by a scheduled task (cron / Celery beat) every Monday morning.
For each active workspace:
  1. Query last 7 days of runs and drift events
  2. Compute change summaries (score delta, new mentions, drops)
  3. Render HTML email template
  4. Send via EmailService
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.run import Run
from app.models.user import User
from app.models.workspace import Workspace, Membership
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)


class WeeklyDigestService:
    """Generates and sends weekly AI visibility digest emails."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def send_all_digests(self) -> Dict[str, int]:
        """Send weekly digests for all active workspaces. Returns stats."""
        stats = {"total_workspaces": 0, "emails_sent": 0, "errors": 0}
        
        # Get all active workspaces with at least one project
        result = await self.db.execute(
            select(Workspace).where(Workspace.is_active == True)
        )
        workspaces = list(result.scalars().all())
        
        for ws in workspaces:
            try:
                sent = await self._send_workspace_digest(ws)
                if sent:
                    stats["emails_sent"] += sent
                stats["total_workspaces"] += 1
            except Exception as e:
                logger.error(f"Failed to send digest for workspace {ws.id}: {e}")
                stats["errors"] += 1
        
        logger.info(f"Weekly digest complete: {stats}")
        return stats
    
    async def _send_workspace_digest(self, workspace: Workspace) -> int:
        """Send digest to all members of a workspace. Returns emails sent count."""
        # Gather data for the last 7 days
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Get projects
        proj_result = await self.db.execute(
            select(Project).where(
                and_(
                    Project.workspace_id == workspace.id,
                    Project.status == "active",
                )
            )
        )
        projects = list(proj_result.scalars().all())
        
        if not projects:
            return 0  # No projects, skip
        
        # Get recent runs
        project_ids = [p.id for p in projects]
        runs_result = await self.db.execute(
            select(Run)
            .where(
                and_(
                    Run.project_id.in_(project_ids),
                    Run.created_at >= week_ago,
                )
            )
            .order_by(desc(Run.created_at))
            .limit(50)
        )
        recent_runs = list(runs_result.scalars().all())
        
        if not recent_runs:
            return 0  # No activity, skip
        
        # Build digest data
        digest = self._build_digest(workspace, projects, recent_runs)
        
        if not digest["has_content"]:
            return 0
        
        # Get members
        members_result = await self.db.execute(
            select(User).join(Membership).where(
                Membership.workspace_id == workspace.id
            )
        )
        members = list(members_result.scalars().all())
        
        # Send to each member
        from app.services.email_service import email_service
        
        sent_count = 0
        for member in members:
            try:
                html = self._render_digest_email(digest, member)
                success = await email_service.send_email(
                    to_email=member.email,
                    subject=f"[FindableX] 周报 – {workspace.name} AI 可见性变化摘要",
                    html_content=html,
                    text_content=self._render_digest_text(digest, member),
                )
                if success:
                    sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send digest to {member.email}: {e}")
        
        return sent_count
    
    def _build_digest(
        self,
        workspace: Workspace,
        projects: List[Project],
        recent_runs: List[Run],
    ) -> Dict[str, Any]:
        """Build the digest data structure."""
        total_runs = len(recent_runs)
        
        # Per-project summary
        project_summaries = []
        for proj in projects:
            proj_runs = [r for r in recent_runs if r.project_id == proj.id]
            if not proj_runs:
                continue
            
            # Get latest score
            latest = max(proj_runs, key=lambda r: r.created_at)
            latest_score = getattr(latest, 'health_score', None)
            
            # Get earliest score this week for delta
            earliest = min(proj_runs, key=lambda r: r.created_at)
            earliest_score = getattr(earliest, 'health_score', None)
            
            score_delta = None
            if latest_score is not None and earliest_score is not None:
                score_delta = latest_score - earliest_score
            
            project_summaries.append({
                "name": proj.name,
                "runs_count": len(proj_runs),
                "latest_score": latest_score,
                "score_delta": score_delta,
            })
        
        return {
            "workspace_name": workspace.name,
            "period_start": (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%m月%d日"),
            "period_end": datetime.now(timezone.utc).strftime("%m月%d日"),
            "total_runs": total_runs,
            "projects": project_summaries,
            "has_content": total_runs > 0,
        }
    
    def _render_digest_email(self, digest: Dict, user: User) -> str:
        """Render the HTML email for the weekly digest."""
        user_name = user.full_name or user.email.split("@")[0]
        
        # Build project rows
        project_rows = ""
        for p in digest["projects"]:
            score_display = f"{p['latest_score']}" if p['latest_score'] is not None else "--"
            delta_html = ""
            if p["score_delta"] is not None and p["score_delta"] != 0:
                color = "#22c55e" if p["score_delta"] > 0 else "#ef4444"
                arrow = "↑" if p["score_delta"] > 0 else "↓"
                delta_html = f'<span style="color: {color}; font-size: 12px;"> {arrow}{abs(p["score_delta"]):.0f}</span>'
            
            project_rows += f"""
            <tr>
                <td style="padding: 12px 16px; color: #e2e8f0; font-size: 14px;">{p['name']}</td>
                <td style="padding: 12px 16px; text-align: center; color: #e2e8f0; font-size: 14px;">
                    {score_display}{delta_html}
                </td>
                <td style="padding: 12px 16px; text-align: center; color: #94a3b8; font-size: 14px;">{p['runs_count']}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #0f172a;">
            <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <span style="font-size: 24px; font-weight: bold; color: #6366f1;">FindableX</span>
                    <span style="color: #475569; font-size: 14px; display: block; margin-top: 4px;">周报</span>
                </div>
                
                <div style="background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155;">
                    <h2 style="color: #f1f5f9; margin: 0 0 8px 0; font-size: 18px;">
                        👋 {user_name}，您的 AI 可见性周报来了
                    </h2>
                    <p style="color: #94a3b8; margin: 0 0 20px 0; font-size: 14px;">
                        {digest['period_start']} – {digest['period_end']} · {digest['workspace_name']}
                    </p>
                    
                    <div style="background: #0f172a; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                        <div style="text-align: center;">
                            <span style="color: #6366f1; font-size: 32px; font-weight: bold;">{digest['total_runs']}</span>
                            <span style="color: #94a3b8; font-size: 14px; display: block;">本周体检次数</span>
                        </div>
                    </div>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 1px solid #334155;">
                                <th style="padding: 8px 16px; text-align: left; color: #64748b; font-size: 12px; font-weight: 500;">项目</th>
                                <th style="padding: 8px 16px; text-align: center; color: #64748b; font-size: 12px; font-weight: 500;">评分</th>
                                <th style="padding: 8px 16px; text-align: center; color: #64748b; font-size: 12px; font-weight: 500;">运行</th>
                            </tr>
                        </thead>
                        <tbody>
                            {project_rows}
                        </tbody>
                    </table>
                    
                    <div style="text-align: center; margin-top: 24px;">
                        <a href="https://findablex.com/dashboard" 
                           style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-size: 14px;">
                            查看完整报告
                        </a>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 24px; color: #64748b; font-size: 12px;">
                    <p>您收到此邮件是因为您是 {digest['workspace_name']} 的成员</p>
                    <p>© 2026 FindableX. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _render_digest_text(self, digest: Dict, user: User) -> str:
        """Plain text version of the digest."""
        user_name = user.full_name or user.email.split("@")[0]
        
        lines = [
            f"FindableX 周报 – {digest['workspace_name']}",
            f"{digest['period_start']} – {digest['period_end']}",
            "",
            f"您好 {user_name}，",
            f"本周体检次数: {digest['total_runs']}",
            "",
            "项目摘要:",
        ]
        
        for p in digest["projects"]:
            score = p["latest_score"] if p["latest_score"] is not None else "--"
            delta = ""
            if p["score_delta"] is not None and p["score_delta"] != 0:
                delta = f" ({'↑' if p['score_delta'] > 0 else '↓'}{abs(p['score_delta']):.0f})"
            lines.append(f"  - {p['name']}: 评分 {score}{delta} ({p['runs_count']} 次运行)")
        
        lines.extend([
            "",
            "查看完整报告: https://findablex.com/dashboard",
            "",
            "---",
            "FindableX",
        ])
        
        return "\n".join(lines)


async def send_weekly_digests(db: AsyncSession) -> Dict[str, int]:
    """Entry point for the scheduled task."""
    service = WeeklyDigestService(db)
    return await service.send_all_digests()
