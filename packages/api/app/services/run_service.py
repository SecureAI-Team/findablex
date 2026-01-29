"""Run service for business logic."""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.run import Run, Citation, Metric
from app.schemas.run import RunCreate


class RunService:
    """Service for run operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, run_id: UUID) -> Optional[Run]:
        """Get run by ID."""
        result = await self.db.execute(
            select(Run)
            .where(Run.id == run_id)
            .options(
                selectinload(Run.citations),
                selectinload(Run.metrics),
            )
        )
        return result.scalar_one_or_none()
    
    async def get_project_runs(
        self,
        project_id: UUID,
        status: Optional[str] = None,
    ) -> List[Run]:
        """Get all runs for a project."""
        query = select(Run).where(Run.project_id == project_id)
        if status:
            query = query.where(Run.status == status)
        query = query.order_by(Run.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, data: RunCreate, user_id: UUID) -> Run:
        """Create a new run."""
        # Get next run number
        result = await self.db.execute(
            select(func.coalesce(func.max(Run.run_number), 0))
            .where(Run.project_id == data.project_id)
        )
        next_number = result.scalar() + 1
        
        run = Run(
            project_id=data.project_id,
            run_number=next_number,
            run_type=data.run_type,
            input_method=data.input_method,
            parameters=data.parameters,
            region=data.region,
            language=data.language,
            created_by=user_id,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run
    
    async def update_status(
        self,
        run: Run,
        status: str,
        error_message: Optional[str] = None,
    ) -> Run:
        """Update run status."""
        run.status = status
        if status == "running":
            run.started_at = datetime.now(timezone.utc)
        elif status in ("completed", "failed"):
            run.completed_at = datetime.now(timezone.utc)
        if error_message:
            run.error_message = error_message
        
        await self.db.commit()
        await self.db.refresh(run)
        return run
    
    async def add_citation(
        self,
        run_id: UUID,
        query_item_id: UUID,
        position: int,
        source_url: Optional[str],
        source_domain: Optional[str],
        source_title: Optional[str],
        snippet: Optional[str],
        is_target_domain: bool = False,
        raw_response: Optional[dict] = None,
    ) -> Citation:
        """Add a citation to a run."""
        citation = Citation(
            run_id=run_id,
            query_item_id=query_item_id,
            position=position,
            source_url=source_url,
            source_domain=source_domain,
            source_title=source_title,
            snippet=snippet,
            is_target_domain=is_target_domain,
            raw_response=raw_response,
        )
        self.db.add(citation)
        await self.db.commit()
        await self.db.refresh(citation)
        return citation
    
    async def add_metric(
        self,
        run_id: UUID,
        metric_type: str,
        metric_value: float,
        query_item_id: Optional[UUID] = None,
        metric_details: Optional[dict] = None,
    ) -> Metric:
        """Add a metric to a run."""
        metric = Metric(
            run_id=run_id,
            query_item_id=query_item_id,
            metric_type=metric_type,
            metric_value=metric_value,
            metric_details=metric_details,
        )
        self.db.add(metric)
        await self.db.commit()
        await self.db.refresh(metric)
        return metric
    
    async def get_citations(self, run_id: UUID) -> List[Citation]:
        """Get all citations for a run."""
        result = await self.db.execute(
            select(Citation)
            .where(Citation.run_id == run_id)
            .order_by(Citation.position)
        )
        return list(result.scalars().all())
    
    async def get_metrics(self, run_id: UUID) -> List[Metric]:
        """Get all metrics for a run."""
        result = await self.db.execute(
            select(Metric).where(Metric.run_id == run_id)
        )
        return list(result.scalars().all())
