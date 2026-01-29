"""Project service for business logic."""
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, QueryItem
from app.models.run import Run
from app.schemas.project import ProjectCreate, ProjectUpdate, QueryItemCreate


class ProjectService:
    """Service for project operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, project_id: UUID, enrich: bool = False) -> Optional[Project | Dict[str, Any]]:
        """Get project by ID."""
        result = await self.db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.query_items))
        )
        project = result.scalar_one_or_none()
        
        if project and enrich:
            return await self._enrich_project(project)
        return project
    
    async def get_workspace_projects(
        self,
        workspace_id: UUID,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all projects in a workspace with computed fields."""
        query = select(Project).where(Project.workspace_id == workspace_id)
        if status:
            query = query.where(Project.status == status)
        query = query.order_by(Project.created_at.desc())
        
        result = await self.db.execute(query)
        projects = list(result.scalars().all())
        
        # Enrich with computed fields
        enriched_projects = []
        for project in projects:
            project_data = await self._enrich_project(project)
            enriched_projects.append(project_data)
        
        return enriched_projects
    
    async def _enrich_project(self, project: Project) -> Dict[str, Any]:
        """Add computed fields to project data."""
        # Get run statistics
        run_stats = await self.db.execute(
            select(
                func.count(Run.id).label("run_count"),
                func.max(Run.created_at).label("last_run_at"),
            ).where(Run.project_id == project.id)
        )
        stats = run_stats.first()
        
        # Get latest completed run health score
        latest_run_result = await self.db.execute(
            select(Run.health_score)
            .where(Run.project_id == project.id, Run.status == "completed")
            .order_by(desc(Run.completed_at))
            .limit(1)
        )
        latest_run = latest_run_result.scalar_one_or_none()
        
        return {
            "id": project.id,
            "workspace_id": project.workspace_id,
            "name": project.name,
            "description": project.description,
            "industry_template": project.industry_template,
            "target_domains": project.target_domains,
            "settings": project.settings,
            "status": project.status,
            "created_by": project.created_by,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "health_score": latest_run,
            "run_count": stats.run_count if stats else 0,
            "last_run_at": stats.last_run_at if stats else None,
        }
    
    async def create(self, data: ProjectCreate, user_id: UUID) -> Project:
        """Create a new project."""
        project = Project(
            workspace_id=data.workspace_id,
            name=data.name,
            description=data.description,
            industry_template=data.industry_template,
            target_domains=data.target_domains,
            created_by=user_id,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project
    
    async def update(self, project: Project, data: ProjectUpdate) -> Project:
        """Update a project."""
        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description
        if data.target_domains is not None:
            project.target_domains = data.target_domains
        if data.settings is not None:
            project.settings = data.settings
        
        await self.db.commit()
        await self.db.refresh(project)
        return project
    
    async def delete(self, project: Project) -> None:
        """Delete a project."""
        await self.db.delete(project)
        await self.db.commit()
    
    async def add_query_items(
        self,
        project_id: UUID,
        items: List[QueryItemCreate],
    ) -> List[QueryItem]:
        """Add query items to a project."""
        query_items = []
        for i, item in enumerate(items):
            query_item = QueryItem(
                project_id=project_id,
                query_text=item.query_text,
                query_type=item.query_type,
                intent_category=item.intent_category,
                expected_citations=item.expected_citations,
                metadata=item.metadata,
                position=i,
            )
            self.db.add(query_item)
            query_items.append(query_item)
        
        await self.db.commit()
        for item in query_items:
            await self.db.refresh(item)
        return query_items
    
    async def get_query_items(self, project_id: UUID) -> List[QueryItem]:
        """Get all query items for a project."""
        result = await self.db.execute(
            select(QueryItem)
            .where(QueryItem.project_id == project_id)
            .order_by(QueryItem.position)
        )
        return list(result.scalars().all())
