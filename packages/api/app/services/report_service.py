"""Report service for business logic."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password, verify_password
from app.models.report import Report, ShareLink
from app.models.run import Run
from app.schemas.report import ShareLinkCreate


class ReportService:
    """Service for report operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, report_id: UUID) -> Optional[Report]:
        """Get report by ID."""
        result = await self.db.execute(
            select(Report).where(Report.id == report_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_run_id(self, run_id: UUID) -> Optional[Report]:
        """Get report by run ID."""
        result = await self.db.execute(
            select(Report).where(Report.run_id == run_id)
        )
        return result.scalar_one_or_none()
    
    async def get_project_reports(self, project_id: UUID) -> List[Report]:
        """Get all reports for a project."""
        # Get all runs for the project, then their reports
        result = await self.db.execute(
            select(Report)
            .join(Run, Report.run_id == Run.id)
            .where(Run.project_id == project_id)
            .order_by(Report.generated_at.desc())
        )
        return list(result.scalars().all())
    
    async def create(
        self,
        run_id: UUID,
        title: str,
        report_type: str = "checkup",
        content_html: Optional[str] = None,
        content_json: Optional[dict] = None,
    ) -> Report:
        """Create a new report."""
        report = Report(
            run_id=run_id,
            title=title,
            report_type=report_type,
            content_html=content_html,
            content_json=content_json or {},
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report
    
    async def create_share_link(
        self,
        report_id: UUID,
        user_id: UUID,
        data: ShareLinkCreate,
    ) -> ShareLink:
        """Create a share link for a report."""
        token = secrets.token_urlsafe(32)
        
        expires_at = None
        if data.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)
        
        password_hash = None
        if data.password:
            password_hash = hash_password(data.password)
        
        share_link = ShareLink(
            report_id=report_id,
            token=token,
            password_hash=password_hash,
            max_views=data.max_views,
            expires_at=expires_at,
            created_by=user_id,
        )
        self.db.add(share_link)
        await self.db.commit()
        await self.db.refresh(share_link)
        return share_link
    
    async def get_share_link_by_token(self, token: str) -> Optional[ShareLink]:
        """Get share link by token."""
        result = await self.db.execute(
            select(ShareLink).where(ShareLink.token == token)
        )
        return result.scalar_one_or_none()
    
    async def validate_share_link(
        self,
        share_link: ShareLink,
        password: Optional[str] = None,
    ) -> bool:
        """Validate share link access."""
        # Check expiry
        if share_link.expires_at and share_link.expires_at < datetime.now(timezone.utc):
            return False
        
        # Check max views
        if share_link.max_views and share_link.view_count >= share_link.max_views:
            return False
        
        # Check password
        if share_link.password_hash:
            if not password:
                return False
            if not verify_password(password, share_link.password_hash):
                return False
        
        return True
    
    async def increment_view_count(self, share_link: ShareLink) -> None:
        """Increment view count for share link."""
        share_link.view_count += 1
        await self.db.commit()
    
    async def get_report_share_links(self, report_id: UUID) -> List[ShareLink]:
        """Get all share links for a report."""
        result = await self.db.execute(
            select(ShareLink)
            .where(ShareLink.report_id == report_id)
            .order_by(ShareLink.created_at.desc())
        )
        return list(result.scalars().all())
