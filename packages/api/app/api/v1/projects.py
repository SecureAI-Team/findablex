"""Project routes."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.crawler import CrawlTask, CrawlResult
from app.models.project import Project, QueryItem
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    QueryItemBulkCreate,
    QueryItemResponse,
    CheckupTemplateResponse,
)
from app.services.project_service import ProjectService
from app.services.workspace_service import WorkspaceService

# Import template constants
try:
    from geo_types.constants import CHECKUP_TEMPLATES, INDUSTRY_TEMPLATES
except ImportError:
    # Fallback for when shared package is not installed
    CHECKUP_TEMPLATES = {}
    INDUSTRY_TEMPLATES = {}

router = APIRouter()


# ============ Checkup Templates API ============

@router.get("/templates/checkup", response_model=List[dict])
async def list_checkup_templates(
    industry: Optional[str] = None,
) -> List[dict]:
    """
    List available checkup templates.
    
    These are scene-based templates with pre-defined queries tagged by
    stage (awareness/consideration/decision), type, risk level, and target role.
    """
    templates = []
    
    for template_id, template_data in CHECKUP_TEMPLATES.items():
        # Filter by industry if specified
        if industry and template_data.get("industry") != industry and template_data.get("industry") != "general":
            continue
        
        templates.append({
            "id": template_id,
            "name": template_data.get("name", ""),
            "industry": template_data.get("industry", "general"),
            "description": template_data.get("description", ""),
            "query_count": template_data.get("query_count", len(template_data.get("queries", []))),
            "free_preview": template_data.get("free_preview", 10),
            # Only return preview queries (not full list unless authenticated)
            "preview_queries": [
                {
                    "text": q.get("text", q) if isinstance(q, dict) else q,
                    "stage": q.get("stage") if isinstance(q, dict) else None,
                    "type": q.get("type") if isinstance(q, dict) else None,
                    "risk": q.get("risk") if isinstance(q, dict) else None,
                    "role": q.get("role") if isinstance(q, dict) else None,
                }
                for q in template_data.get("queries", [])[:5]  # Only show first 5 as preview
            ],
        })
    
    return templates


@router.get("/templates/checkup/{template_id}")
async def get_checkup_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get a specific checkup template with all queries.
    
    Returns the full query list (up to free_preview count for free users).
    """
    template_data = CHECKUP_TEMPLATES.get(template_id)
    if not template_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    queries = template_data.get("queries", [])
    free_preview = template_data.get("free_preview", 10)
    
    # For now, return all queries (in production, limit based on subscription)
    # TODO: Check user subscription and limit accordingly
    
    return {
        "id": template_id,
        "name": template_data.get("name", ""),
        "industry": template_data.get("industry", "general"),
        "description": template_data.get("description", ""),
        "query_count": len(queries),
        "free_preview": free_preview,
        "queries": [
            {
                "text": q.get("text", q) if isinstance(q, dict) else q,
                "stage": q.get("stage") if isinstance(q, dict) else None,
                "type": q.get("type") if isinstance(q, dict) else None,
                "risk": q.get("risk") if isinstance(q, dict) else None,
                "role": q.get("role") if isinstance(q, dict) else None,
            }
            for q in queries
        ],
    }


@router.get("/templates/industry")
async def list_industry_templates() -> List[dict]:
    """List available industry templates (basic templates)."""
    templates = []
    
    for template_id, template_data in INDUSTRY_TEMPLATES.items():
        templates.append({
            "id": template_id,
            "name": template_data.get("name", ""),
            "description": template_data.get("description", ""),
            "queries": template_data.get("queries", []),
        })
    
    return templates


# ============ Response Schemas for Crawl Data ============

class CrawlResultResponse(BaseModel):
    """Response schema for a single crawl result."""
    id: UUID
    query_item_id: UUID
    query_text: str
    engine: str
    response_text: Optional[str] = None
    citations: List[Dict[str, Any]] = []
    crawled_at: Optional[str] = None
    error: Optional[str] = None
    screenshot_path: Optional[str] = None


class QueryWithResultsResponse(BaseModel):
    """Response schema for a query with its crawl results."""
    query_id: UUID
    query_text: str
    query_type: Optional[str] = None
    crawl_count: int = 0
    latest_crawl: Optional[str] = None
    results: List[CrawlResultResponse] = []


class ProjectCrawlTaskResponse(BaseModel):
    """Response schema for crawl tasks in a project."""
    id: UUID
    engine: str
    status: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TargetDomainMatch(BaseModel):
    """A citation that matches a target domain."""
    domain: str
    url: str
    title: Optional[str] = None
    engine: str
    query_text: Optional[str] = None


class CitationSummary(BaseModel):
    """Summary of citations for a project."""
    total_citations: int
    unique_domains: int
    top_domains: List[Dict[str, Any]]
    citations_by_engine: Dict[str, int]
    # Target domain analysis
    target_domains: List[str] = []
    target_domain_citations: int = 0
    visibility_score: float = 0.0  # Percentage of citations matching target domains
    target_domain_matches: List[TargetDomainMatch] = []


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    workspace_id: UUID = None,
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    """List all projects in a workspace. If workspace_id is not provided, use user's default workspace."""
    workspace_service = WorkspaceService(db)
    project_service = ProjectService(db)
    
    # Get workspace_id - use default if not provided
    if workspace_id is None:
        default_workspace = await workspace_service.get_default_workspace(current_user.id)
        if not default_workspace:
            # Return empty list if no workspace
            return []
        workspace_id = default_workspace.id
    
    # Check membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    projects = await project_service.get_workspace_projects(workspace_id, status)
    return projects


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new project."""
    workspace_service = WorkspaceService(db)
    project_service = ProjectService(db)
    
    # Check membership
    membership = await workspace_service.get_membership(data.workspace_id, current_user.id)
    if not membership:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this workspace",
            )
    
    project = await project_service.create(data, current_user.id)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Get project by ID."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Return enriched project data with computed fields
    return await project_service._enrich_project(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Update project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "analyst"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this project",
            )
    
    project = await project_service.update(project, data)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check admin membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role != "admin":
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete projects",
            )
    
    await project_service.delete(project)


@router.get("/{project_id}/queries", response_model=List[QueryItemResponse])
async def list_queries(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[QueryItemResponse]:
    """List all queries in a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    queries = await project_service.get_query_items(project_id)
    return queries


@router.post("/{project_id}/queries/import", response_model=List[QueryItemResponse])
async def import_queries(
    project_id: UUID,
    data: QueryItemBulkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[QueryItemResponse]:
    """Import queries to a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "analyst"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to import queries",
            )
    
    queries = await project_service.add_query_items(project_id, data.queries)
    return queries


# ============ Query Item CRUD Endpoints ============

class QueryItemCreateSingle(BaseModel):
    """Schema for creating a single query item."""
    query_text: str
    query_type: Optional[str] = "informational"


class QueryItemUpdate(BaseModel):
    """Schema for updating a query item."""
    query_text: Optional[str] = None
    query_type: Optional[str] = None


@router.post("/{project_id}/queries", response_model=QueryItemResponse)
async def create_query(
    project_id: UUID,
    data: QueryItemCreateSingle,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueryItemResponse:
    """Add a single query to a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "analyst"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add queries",
            )
    
    # Get max position
    result = await db.execute(
        select(func.max(QueryItem.position)).where(QueryItem.project_id == project_id)
    )
    max_pos = result.scalar() or 0
    
    # Create query item
    query_item = QueryItem(
        project_id=project_id,
        query_text=data.query_text.strip(),
        query_type=data.query_type,
        position=max_pos + 1,
    )
    db.add(query_item)
    await db.commit()
    await db.refresh(query_item)
    
    return QueryItemResponse.model_validate(query_item)


@router.put("/{project_id}/queries/{query_id}", response_model=QueryItemResponse)
async def update_query(
    project_id: UUID,
    query_id: UUID,
    data: QueryItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueryItemResponse:
    """Update a query item."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "analyst"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update queries",
            )
    
    # Get query item
    result = await db.execute(
        select(QueryItem).where(
            QueryItem.id == query_id,
            QueryItem.project_id == project_id
        )
    )
    query_item = result.scalar_one_or_none()
    
    if not query_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found",
        )
    
    # Update fields
    if data.query_text is not None:
        query_item.query_text = data.query_text.strip()
    if data.query_type is not None:
        query_item.query_type = data.query_type
    
    await db.commit()
    await db.refresh(query_item)
    
    return QueryItemResponse.model_validate(query_item)


@router.delete("/{project_id}/queries/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(
    project_id: UUID,
    query_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a query item."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "analyst"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete queries",
            )
    
    # Get query item
    result = await db.execute(
        select(QueryItem).where(
            QueryItem.id == query_id,
            QueryItem.project_id == project_id
        )
    )
    query_item = result.scalar_one_or_none()
    
    if not query_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found",
        )
    
    await db.delete(query_item)
    await db.commit()


# ============ Query from Template Endpoint ============

class QueryFromTemplateRequest(BaseModel):
    """Request to create queries from a checkup template."""
    template_id: str


@router.post("/{project_id}/queries/from-template")
async def create_queries_from_template(
    project_id: UUID,
    data: QueryFromTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create queries from a checkup template.
    
    This loads the full query list from the specified template and adds them to the project.
    For free users, only the first `free_preview` queries are added.
    """
    from app.middleware.quota import get_workspace_subscription
    
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "analyst"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add queries",
            )
    
    # Get template
    template_data = CHECKUP_TEMPLATES.get(data.template_id)
    if not template_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{data.template_id}' not found",
        )
    
    # Get subscription to determine query limit
    subscription = await get_workspace_subscription(project.workspace_id, db)
    limits = subscription.get_limits()
    query_limit = limits.get("queries_per_project", 10)
    
    # Get template queries
    template_queries = template_data.get("queries", [])
    free_preview = template_data.get("free_preview", 10)
    
    # Apply limit based on subscription
    if query_limit == -1:
        # Unlimited - use all queries
        queries_to_add = template_queries
    else:
        # Limited - use min of free_preview and subscription limit
        max_queries = min(free_preview, query_limit) if subscription.plan_code == "free" else len(template_queries)
        queries_to_add = template_queries[:max_queries]
    
    # Get max position
    result = await db.execute(
        select(func.max(QueryItem.position)).where(QueryItem.project_id == project_id)
    )
    max_pos = result.scalar() or 0
    
    # Create query items
    created_count = 0
    for i, q in enumerate(queries_to_add):
        query_text = q.get("text", q) if isinstance(q, dict) else q
        query_item = QueryItem(
            project_id=project_id,
            query_text=query_text.strip(),
            query_type=q.get("type", "informational") if isinstance(q, dict) else "informational",
            stage=q.get("stage") if isinstance(q, dict) else None,
            risk_level=q.get("risk") if isinstance(q, dict) else None,
            target_role=q.get("role") if isinstance(q, dict) else None,
            position=max_pos + i + 1,
        )
        db.add(query_item)
        created_count += 1
    
    await db.commit()
    
    return {
        "success": True,
        "template_id": data.template_id,
        "template_name": template_data.get("name", ""),
        "queries_added": created_count,
        "total_in_template": len(template_queries),
        "limited_by_subscription": created_count < len(template_queries),
    }


# ============ Crawl Results Endpoints ============

@router.get("/{project_id}/crawl-tasks", response_model=List[ProjectCrawlTaskResponse])
async def list_project_crawl_tasks(
    project_id: UUID,
    status_filter: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectCrawlTaskResponse]:
    """List all crawl tasks for a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Query crawl tasks for this project
    query = select(CrawlTask).where(CrawlTask.project_id == project_id)
    if status_filter:
        query = query.where(CrawlTask.status == status_filter)
    query = query.order_by(CrawlTask.created_at.desc())
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return [
        ProjectCrawlTaskResponse(
            id=task.id,
            engine=task.engine,
            status=task.status,
            total_queries=task.total_queries,
            successful_queries=task.successful_queries,
            failed_queries=task.failed_queries,
            created_at=task.created_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
        )
        for task in tasks
    ]


@router.get("/{project_id}/crawl-results", response_model=List[QueryWithResultsResponse])
async def list_project_crawl_results(
    project_id: UUID,
    engine: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[QueryWithResultsResponse]:
    """
    Get all crawl results for a project, grouped by query.
    
    Returns each query with all its associated crawl results from different engines/tasks.
    """
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Get all queries for this project
    query_result = await db.execute(
        select(QueryItem)
        .where(QueryItem.project_id == project_id)
        .order_by(QueryItem.position, QueryItem.created_at)
    )
    queries = query_result.scalars().all()
    
    if not queries:
        return []
    
    query_ids = [q.id for q in queries]
    
    # Get all crawl results for these queries
    result_query = select(CrawlResult).where(CrawlResult.query_item_id.in_(query_ids))
    if engine:
        result_query = result_query.where(CrawlResult.engine == engine)
    result_query = result_query.order_by(CrawlResult.crawled_at.desc())
    
    crawl_result = await db.execute(result_query)
    results = crawl_result.scalars().all()
    
    # Group results by query_item_id
    results_by_query = {}
    for r in results:
        if r.query_item_id not in results_by_query:
            results_by_query[r.query_item_id] = []
        results_by_query[r.query_item_id].append(r)
    
    # Build response
    response = []
    for query in queries:
        query_results = results_by_query.get(query.id, [])
        
        result_responses = [
            CrawlResultResponse(
                id=r.id,
                query_item_id=r.query_item_id,
                query_text=query.query_text,
                engine=r.engine,
                response_text=r.parsed_response.get("response_text", "") if r.parsed_response else None,
                citations=r.citations or [],
                crawled_at=r.crawled_at.isoformat() if r.crawled_at else None,
                error=r.parsed_response.get("error") if r.parsed_response else None,
                screenshot_path=r.screenshot_path,
            )
            for r in query_results
        ]
        
        response.append(QueryWithResultsResponse(
            query_id=query.id,
            query_text=query.query_text,
            query_type=query.query_type,
            crawl_count=len(query_results),
            latest_crawl=query_results[0].crawled_at.isoformat() if query_results and query_results[0].crawled_at else None,
            results=result_responses,
        ))
    
    return response


@router.get("/{project_id}/citations-summary", response_model=CitationSummary)
async def get_project_citations_summary(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CitationSummary:
    """
    Get aggregated citation statistics for a project.
    
    Returns:
    - Total citations count
    - Unique domains count
    - Top 10 most cited domains
    - Citations by engine
    """
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Get all queries for this project
    query_result = await db.execute(
        select(QueryItem.id).where(QueryItem.project_id == project_id)
    )
    query_ids = [row[0] for row in query_result]
    
    # Get target domains from project
    target_domains = project.target_domains or []
    
    if not query_ids:
        return CitationSummary(
            total_citations=0,
            unique_domains=0,
            top_domains=[],
            citations_by_engine={},
            target_domains=target_domains,
            target_domain_citations=0,
            visibility_score=0.0,
            target_domain_matches=[],
        )
    
    # Get all crawl results for these queries with query text
    result = await db.execute(
        select(CrawlResult, QueryItem.query_text)
        .join(QueryItem, CrawlResult.query_item_id == QueryItem.id)
        .where(CrawlResult.query_item_id.in_(query_ids))
    )
    results = result.all()
    
    # Aggregate citations
    all_citations = []
    citations_by_engine = {}
    domain_counts = {}
    target_domain_matches = []
    target_domain_citation_count = 0
    
    def domain_matches_target(domain: str, targets: List[str]) -> bool:
        """Check if domain matches any target domain (supports subdomains)."""
        domain_lower = domain.lower()
        for target in targets:
            target_lower = target.lower()
            # Exact match or subdomain match
            if domain_lower == target_lower or domain_lower.endswith('.' + target_lower):
                return True
        return False
    
    for crawl_result, query_text in results:
        citations = crawl_result.citations or []
        engine = crawl_result.engine
        
        if engine not in citations_by_engine:
            citations_by_engine[engine] = 0
        citations_by_engine[engine] += len(citations)
        
        for citation in citations:
            all_citations.append(citation)
            # Extract domain
            url = citation.get("url", "")
            domain = citation.get("domain", "")
            title = citation.get("title", "")
            
            if not domain and url:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                except:
                    domain = url
            
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                
                # Check if matches target domain
                if target_domains and domain_matches_target(domain, target_domains):
                    target_domain_citation_count += 1
                    target_domain_matches.append(TargetDomainMatch(
                        domain=domain,
                        url=url,
                        title=title,
                        engine=engine,
                        query_text=query_text,
                    ))
    
    # Get top domains
    top_domains = sorted(
        [{"domain": d, "count": c} for d, c in domain_counts.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:10]
    
    # Calculate visibility score
    visibility_score = 0.0
    if len(all_citations) > 0:
        visibility_score = round((target_domain_citation_count / len(all_citations)) * 100, 1)
    
    return CitationSummary(
        total_citations=len(all_citations),
        unique_domains=len(domain_counts),
        top_domains=top_domains,
        citations_by_engine=citations_by_engine,
        target_domains=target_domains,
        target_domain_citations=target_domain_citation_count,
        visibility_score=visibility_score,
        target_domain_matches=target_domain_matches,
    )


@router.get("/{project_id}/queries/{query_id}/results", response_model=List[CrawlResultResponse])
async def get_query_crawl_results(
    project_id: UUID,
    query_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CrawlResultResponse]:
    """Get all crawl results for a specific query."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Verify query belongs to project
    query_result = await db.execute(
        select(QueryItem).where(
            QueryItem.id == query_id,
            QueryItem.project_id == project_id
        )
    )
    query_item = query_result.scalar_one_or_none()
    
    if not query_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found in this project",
        )
    
    # Get crawl results
    result = await db.execute(
        select(CrawlResult)
        .where(CrawlResult.query_item_id == query_id)
        .order_by(CrawlResult.crawled_at.desc())
    )
    results = result.scalars().all()
    
    return [
        CrawlResultResponse(
            id=r.id,
            query_item_id=r.query_item_id,
            query_text=query_item.query_text,
            engine=r.engine,
            response_text=r.parsed_response.get("response_text", "") if r.parsed_response else None,
            citations=r.citations or [],
            crawled_at=r.crawled_at.isoformat() if r.crawled_at else None,
            error=r.parsed_response.get("error") if r.parsed_response else None,
            screenshot_path=r.screenshot_path,
        )
        for r in results
    ]


@router.get("/{project_id}/crawl-results/export")
async def export_project_crawl_results(
    project_id: UUID,
    format: str = "json",
    engine: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all crawl results for a project in JSON or CSV format."""
    from fastapi.responses import Response
    import json
    import csv
    import io
    
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Get all queries for this project
    query_result = await db.execute(
        select(QueryItem)
        .where(QueryItem.project_id == project_id)
        .order_by(QueryItem.position, QueryItem.created_at)
    )
    queries = query_result.scalars().all()
    
    if not queries:
        return Response(
            content="[]" if format.lower() != "csv" else "",
            media_type="application/json" if format.lower() != "csv" else "text/csv",
        )
    
    query_ids = [q.id for q in queries]
    query_map = {q.id: q.query_text for q in queries}
    
    # Get all crawl results for these queries
    result_query = select(CrawlResult).where(CrawlResult.query_item_id.in_(query_ids))
    if engine:
        result_query = result_query.where(CrawlResult.engine == engine)
    result_query = result_query.order_by(CrawlResult.crawled_at.desc())
    
    crawl_result = await db.execute(result_query)
    results = crawl_result.scalars().all()
    
    # Build export data
    export_data = []
    for r in results:
        query_text = query_map.get(r.query_item_id, "")
        response_text = r.parsed_response.get("response_text", "") if r.parsed_response else ""
        citations = r.citations or []
        
        export_data.append({
            "query": query_text,
            "response": response_text,
            "engine": r.engine,
            "citations_count": len(citations),
            "citations": [c.get("url", "") for c in citations],
            "crawled_at": r.crawled_at.isoformat() if r.crawled_at else None,
            "error": r.parsed_response.get("error") if r.parsed_response else None,
        })
    
    if format.lower() == "csv":
        # Generate CSV
        output = io.StringIO()
        fieldnames = ["query", "response", "engine", "citations_count", "citations", "crawled_at", "error"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in export_data:
            row["citations"] = "; ".join(row["citations"])  # Join URLs for CSV
            writer.writerow(row)
        
        content = output.getvalue()
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=project_{project_id}_results.csv"
            }
        )
    else:
        # Default to JSON
        content = json.dumps(export_data, ensure_ascii=False, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=project_{project_id}_results.json"
            }
        )


# ========== Project Trends & Dashboard Data ==========

class TrendDataPoint(BaseModel):
    """Single data point for trend chart."""
    date: str
    engine: str
    visibility_score: float
    citations_count: int
    queries_total: int


class EngineSummary(BaseModel):
    """Per-engine summary for radar chart."""
    engine: str
    engine_label: str
    visibility_score: float
    citation_rate: float
    avg_response_time: Optional[float] = None
    total_citations: int
    total_queries: int


class ProjectTrendsResponse(BaseModel):
    """Response for project trends data."""
    trend_data: List[Dict[str, Any]]
    engine_summaries: List[EngineSummary]
    health_history: List[Dict[str, Any]]
    summary: Dict[str, Any]


ENGINE_LABELS = {
    "deepseek": "DeepSeek",
    "kimi": "Kimi",
    "doubao": "豆包",
    "chatglm": "ChatGLM",
    "chatgpt": "ChatGPT",
    "qwen": "通义千问",
    "perplexity": "Perplexity",
    "google_sge": "Google SGE",
    "bing_copilot": "Bing Copilot",
}


@router.get("/{project_id}/trends", response_model=ProjectTrendsResponse)
async def get_project_trends(
    project_id: UUID,
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectTrendsResponse:
    """
    Get project trend data for dashboard charts.
    
    Returns:
    - trend_data: Time-series data for line chart (visibility per engine over time)
    - engine_summaries: Per-engine metrics for radar chart
    - health_history: Health score history from runs
    - summary: Overall metrics summary
    """
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    
    target_domains = project.target_domains or []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get all query IDs for this project
    query_result = await db.execute(
        select(QueryItem.id).where(QueryItem.project_id == project_id)
    )
    query_ids = [row[0] for row in query_result]
    
    # 1. Health history from crawl tasks (completed ones)
    health_history = []
    tasks_result = await db.execute(
        select(CrawlTask)
        .where(
            and_(
                CrawlTask.project_id == project_id,
                CrawlTask.status == "completed",
                CrawlTask.completed_at >= cutoff,
            )
        )
        .order_by(CrawlTask.completed_at)
    )
    tasks = tasks_result.scalars().all()
    
    for task in tasks:
        if task.total_queries > 0:
            success_rate = (task.successful_queries / task.total_queries) * 100
            health_history.append({
                "date": task.completed_at.strftime("%m-%d"),
                "datetime": task.completed_at.isoformat(),
                "engine": task.engine,
                "engine_label": ENGINE_LABELS.get(task.engine, task.engine),
                "success_rate": round(success_rate, 1),
                "successful": task.successful_queries,
                "total": task.total_queries,
            })
    
    # 2. Per-engine visibility (from crawl results)
    engine_summaries = []
    trend_data = []
    
    if query_ids:
        # Get per-engine stats
        engine_stats_query = (
            select(
                CrawlResult.engine,
                func.count(CrawlResult.id).label("total_results"),
                func.sum(case((CrawlResult.has_citations == True, 1), else_=0)).label("with_citations"),
                func.avg(CrawlResult.response_time_ms).label("avg_response_time"),
            )
            .where(
                and_(
                    CrawlResult.query_item_id.in_(query_ids),
                    CrawlResult.crawled_at >= cutoff,
                )
            )
            .group_by(CrawlResult.engine)
        )
        engine_stats_result = await db.execute(engine_stats_query)
        engine_stats = engine_stats_result.all()
        
        for row in engine_stats:
            engine = row[0]
            total = row[1] or 0
            with_citations_count = row[2] or 0
            avg_rt = float(row[3]) if row[3] else None
            
            # Count target domain citations for this engine
            target_citation_count = 0
            if target_domains:
                citations_result = await db.execute(
                    select(CrawlResult.citations)
                    .where(
                        and_(
                            CrawlResult.query_item_id.in_(query_ids),
                            CrawlResult.engine == engine,
                            CrawlResult.has_citations == True,
                            CrawlResult.crawled_at >= cutoff,
                        )
                    )
                )
                for (citations,) in citations_result:
                    if citations:
                        for citation in citations:
                            url = citation.get("url", "") if isinstance(citation, dict) else str(citation)
                            for domain in target_domains:
                                if domain in url:
                                    target_citation_count += 1
                                    break
            
            visibility = (target_citation_count / total * 100) if total > 0 else 0
            citation_rate = (with_citations_count / total * 100) if total > 0 else 0
            
            engine_summaries.append(EngineSummary(
                engine=engine,
                engine_label=ENGINE_LABELS.get(engine, engine),
                visibility_score=round(visibility, 1),
                citation_rate=round(citation_rate, 1),
                avg_response_time=round(avg_rt, 0) if avg_rt else None,
                total_citations=target_citation_count,
                total_queries=total,
            ))
        
        # 3. Time-series trend data (group by date + engine)
        # Get daily visibility by engine
        for task in tasks:
            if task.total_queries > 0 and task.completed_at:
                date_str = task.completed_at.strftime("%m-%d")
                
                # Count target domain citations for this task
                task_citations = 0
                if target_domains:
                    task_results = await db.execute(
                        select(CrawlResult.citations)
                        .where(
                            and_(
                                CrawlResult.query_item_id.in_(query_ids),
                                CrawlResult.engine == task.engine,
                                CrawlResult.has_citations == True,
                            )
                            # Use task's results - filter by task_id
                        )
                        .where(CrawlResult.task_id == task.id)
                    )
                    for (citations,) in task_results:
                        if citations:
                            for citation in citations:
                                url = citation.get("url", "") if isinstance(citation, dict) else str(citation)
                                for domain in target_domains:
                                    if domain in url:
                                        task_citations += 1
                                        break
                
                visibility = (task_citations / task.total_queries * 100) if task.total_queries > 0 else 0
                
                trend_data.append({
                    "date": date_str,
                    "datetime": task.completed_at.isoformat(),
                    "engine": task.engine,
                    "engine_label": ENGINE_LABELS.get(task.engine, task.engine),
                    "visibility": round(visibility, 1),
                    "citations": task_citations,
                    "queries": task.total_queries,
                })
    
    # 4. Summary metrics
    total_engines = len(engine_summaries)
    avg_visibility = (
        sum(e.visibility_score for e in engine_summaries) / total_engines
        if total_engines > 0 else 0
    )
    total_citations = sum(e.total_citations for e in engine_summaries)
    best_engine = max(engine_summaries, key=lambda e: e.visibility_score) if engine_summaries else None
    
    summary = {
        "engines_tested": total_engines,
        "avg_visibility": round(avg_visibility, 1),
        "total_citations": total_citations,
        "best_engine": best_engine.engine_label if best_engine else None,
        "best_engine_score": best_engine.visibility_score if best_engine else 0,
        "total_tasks": len(tasks),
        "period_days": days,
    }
    
    return ProjectTrendsResponse(
        trend_data=trend_data,
        engine_summaries=[s.model_dump() for s in engine_summaries],
        health_history=health_history,
        summary=summary,
    )
