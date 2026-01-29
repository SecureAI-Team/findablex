"""Project routes."""
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
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
