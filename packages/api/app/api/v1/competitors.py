"""
Competitor tracking and comparison API.

Allows users to add competitor brands to a project and automatically
compare AI visibility metrics side-by-side.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.project import Project
from app.models.user import User
from app.services.project_service import ProjectService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────

class CompetitorCreate(BaseModel):
    brand_name: str = Field(..., min_length=1, max_length=100)
    domain: str = Field("", max_length=200)
    notes: str = Field("", max_length=500)


class CompetitorResponse(BaseModel):
    id: str
    brand_name: str
    domain: str
    notes: str
    last_checked_at: Optional[str] = None


class ComparisonResponse(BaseModel):
    project_name: str
    your_brand: Dict[str, Any]
    competitors: List[Dict[str, Any]]


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/{project_id}/competitors")
async def list_competitors(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List competitors for a project."""
    project = await _verify_project_access(project_id, current_user, db)
    
    settings = project.settings or {}
    competitors = settings.get("competitors", [])
    
    return {"competitors": competitors}


@router.post("/{project_id}/competitors")
async def add_competitor(
    project_id: UUID,
    data: CompetitorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Add a competitor to track."""
    project = await _verify_project_access(project_id, current_user, db)
    
    settings = project.settings or {}
    competitors = settings.get("competitors", [])
    
    # Max 5 competitors per project
    if len(competitors) >= 5:
        raise HTTPException(
            status_code=400,
            detail="最多可追踪 5 个竞品品牌",
        )
    
    # Check duplicate
    for c in competitors:
        if c["brand_name"].lower() == data.brand_name.lower():
            raise HTTPException(status_code=400, detail="该竞品已添加")
    
    import uuid
    new_competitor = {
        "id": str(uuid.uuid4()),
        "brand_name": data.brand_name,
        "domain": data.domain,
        "notes": data.notes,
        "added_at": __import__("datetime").datetime.now().isoformat(),
    }
    
    competitors.append(new_competitor)
    project.settings = {**settings, "competitors": competitors}
    
    await db.commit()
    
    return {"status": "ok", "competitor": new_competitor}


@router.delete("/{project_id}/competitors/{competitor_id}")
async def remove_competitor(
    project_id: UUID,
    competitor_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Remove a competitor."""
    project = await _verify_project_access(project_id, current_user, db)
    
    settings = project.settings or {}
    competitors = settings.get("competitors", [])
    
    updated = [c for c in competitors if c.get("id") != competitor_id]
    
    if len(updated) == len(competitors):
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    project.settings = {**settings, "competitors": updated}
    await db.commit()
    
    return {"status": "ok"}


@router.get("/{project_id}/comparison")
async def get_comparison(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get a side-by-side comparison of your brand vs competitors.
    
    This analyzes crawl results where competitor brands appear in
    the same AI engine responses.
    """
    project = await _verify_project_access(project_id, current_user, db)
    
    settings = project.settings or {}
    competitors = settings.get("competitors", [])
    
    # Get crawl results for this project
    from app.models.crawler import CrawlResult, CrawlTask
    from sqlalchemy import desc
    
    task_result = await db.execute(
        select(CrawlTask)
        .where(CrawlTask.project_id == project_id)
        .order_by(desc(CrawlTask.created_at))
        .limit(10)
    )
    tasks = list(task_result.scalars().all())
    task_ids = [t.id for t in tasks]
    
    your_brand = {
        "brand_name": project.name,
        "engines_covered": len(set(t.engine for t in tasks)),
        "total_results": sum(t.successful_queries for t in tasks),
    }
    
    # For each competitor, check if they're mentioned in results
    competitor_data = []
    if task_ids:
        cr_result = await db.execute(
            select(CrawlResult)
            .where(CrawlResult.task_id.in_(task_ids))
            .limit(200)
        )
        all_results = list(cr_result.scalars().all())
        
        for comp in competitors:
            comp_name = comp["brand_name"].lower()
            mentions = 0
            for r in all_results:
                content = ""
                if hasattr(r, 'data') and r.data:
                    content = str(r.data.get("response_text", "")).lower()
                if comp_name in content:
                    mentions += 1
            
            competitor_data.append({
                "brand_name": comp["brand_name"],
                "domain": comp.get("domain", ""),
                "mentions_in_results": mentions,
                "mention_rate": mentions / len(all_results) if all_results else 0,
            })
    else:
        competitor_data = [
            {
                "brand_name": c["brand_name"],
                "domain": c.get("domain", ""),
                "mentions_in_results": 0,
                "mention_rate": 0,
            }
            for c in competitors
        ]
    
    return {
        "project_name": project.name,
        "your_brand": your_brand,
        "competitors": competitor_data,
        "total_results_analyzed": sum(t.successful_queries for t in tasks),
    }


async def _verify_project_access(
    project_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> Project:
    """Verify project exists and user has access."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await workspace_service.get_membership(
        project.workspace_id, current_user.id
    )
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return project
