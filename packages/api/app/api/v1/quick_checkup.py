"""Quick checkup API – one-click brand visibility scan.

User provides a brand name (and optional domain).  Backend:
1. Auto-generates a set of typical AI-search query templates
2. Creates a new project with those queries
3. Triggers auto-checkup (reuses auto_checkup logic)
"""
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.project import Project, QueryItem
from app.models.user import User
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────

class QuickCheckupRequest(BaseModel):
    """Input for a one-click checkup."""
    brand_name: str = Field(..., min_length=1, max_length=100, description="品牌名称")
    domain: str = Field("", max_length=200, description="官网域名（可选）")
    industry: str = Field("", max_length=50, description="行业（可选，用于优化查询词）")
    max_engines: int = Field(3, ge=1, le=8, description="使用的引擎数量")


class QuickCheckupResponse(BaseModel):
    """Output after quick checkup initiation."""
    project_id: str
    project_name: str
    queries_generated: int
    engines_used: List[str]
    tasks_created: int
    estimated_time_minutes: int
    message: str


# ── Query Generation ─────────────────────────────────────────────────

GENERIC_TEMPLATES = [
    "{brand} 是什么",
    "{brand} 怎么样",
    "推荐 {brand} 吗",
    "{brand} 有哪些优势",
    "{brand} 和竞品对比",
    "{brand} 用户评价",
    "{brand} 最新动态",
]

INDUSTRY_TEMPLATES = {
    "saas": [
        "最好的{industry}SaaS工具",
        "{brand} SaaS 好用吗",
        "{industry}软件推荐",
    ],
    "ecommerce": [
        "在{brand}购物靠谱吗",
        "{brand} 和淘宝哪个好",
        "网上购物平台推荐",
    ],
    "education": [
        "{brand} 课程质量怎么样",
        "在线教育平台哪个好",
        "{brand} 值不值得报名",
    ],
    "finance": [
        "{brand} 理财安全吗",
        "{brand} 利率怎么样",
        "金融产品推荐",
    ],
    "health": [
        "{brand} 效果好吗",
        "健康产品推荐",
        "{brand} 有副作用吗",
    ],
}

DOMAIN_TEMPLATES = [
    "{domain} 官网是什么",
    "{domain} 是做什么的",
]


def generate_queries(
    brand_name: str,
    domain: str = "",
    industry: str = "",
) -> List[str]:
    """Generate search queries from brand name, domain, and industry."""
    queries: List[str] = []
    
    # Generic brand queries
    for tpl in GENERIC_TEMPLATES:
        queries.append(tpl.format(brand=brand_name))
    
    # Domain-specific queries
    if domain:
        clean_domain = re.sub(r'^https?://', '', domain).rstrip('/')
        for tpl in DOMAIN_TEMPLATES:
            queries.append(tpl.format(domain=clean_domain))
    
    # Industry-specific queries
    industry_key = industry.lower().strip() if industry else ""
    if industry_key in INDUSTRY_TEMPLATES:
        for tpl in INDUSTRY_TEMPLATES[industry_key]:
            queries.append(tpl.format(brand=brand_name, industry=industry))
    
    # Deduplicate while preserving order
    seen = set()
    unique: List[str] = []
    for q in queries:
        q_clean = q.strip()
        if q_clean and q_clean not in seen:
            seen.add(q_clean)
            unique.append(q_clean)
    
    return unique


# ── Endpoint ─────────────────────────────────────────────────────────

@router.post("/quick-checkup", response_model=QuickCheckupResponse)
async def quick_checkup(
    data: QuickCheckupRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuickCheckupResponse:
    """
    One-click brand checkup.
    
    1. Generates queries from brand name
    2. Creates a project
    3. Starts auto-checkup
    """
    workspace_service = WorkspaceService(db)
    
    # Get default workspace
    default_ws = await workspace_service.get_default_workspace(current_user.id)
    if not default_ws:
        raise HTTPException(status_code=404, detail="No workspace found")
    
    workspace_id = default_ws.id
    
    # Check project limit
    try:
        from app.middleware.quota import get_workspace_subscription
        subscription = await get_workspace_subscription(workspace_id, db)
        limits = subscription.get_limits()
        project_limit = limits.get("projects", 1)
        
        if project_limit != -1:
            count_result = await db.execute(
                select(func.count(Project.id)).where(
                    Project.workspace_id == workspace_id
                )
            )
            project_count = count_result.scalar() or 0
            if project_count >= project_limit:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "code": "PROJECT_LIMIT_EXCEEDED",
                        "message": f"项目数量已达上限 ({project_limit})，升级套餐创建更多项目。",
                        "current": project_count,
                        "limit": project_limit,
                    },
                )
    except HTTPException:
        raise
    except Exception:
        pass  # Non-critical
    
    # Generate queries
    query_texts = generate_queries(data.brand_name, data.domain, data.industry)
    
    if not query_texts:
        raise HTTPException(status_code=400, detail="无法生成查询词")
    
    # Create project
    project = Project(
        workspace_id=workspace_id,
        name=f"{data.brand_name} - AI 可见性体检",
        description=f"一键体检: {data.brand_name}" + (f" ({data.domain})" if data.domain else ""),
        target_domains=[data.domain] if data.domain else [],
        settings={"source": "quick_checkup", "brand_name": data.brand_name},
        status="active",
        created_by=current_user.id,
    )
    db.add(project)
    await db.flush()
    
    # Add queries
    for i, q_text in enumerate(query_texts):
        qi = QueryItem(
            project_id=project.id,
            text=q_text,
            position=i,
        )
        db.add(qi)
    
    await db.commit()
    await db.refresh(project)
    
    # Trigger auto-checkup (reuse logic from auto_checkup module)
    from app.api.v1.auto_checkup import select_engines, AVAILABLE_ENGINES
    from app.models.crawler import CrawlTask
    from datetime import datetime, timezone
    
    engines = select_engines(max_engines=data.max_engines)
    
    task_ids = []
    for engine_info in engines:
        task = CrawlTask(
            project_id=project.id,
            engine=engine_info["id"],
            status="pending",
            total_queries=len(query_texts),
            successful_queries=0,
            failed_queries=0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(task)
        await db.flush()
        task_ids.append(str(task.id))
    
    await db.commit()
    
    # Dispatch to worker
    for task_id in task_ids:
        try:
            from app.tasks import process_crawl_task
            process_crawl_task.delay(task_id)
        except Exception:
            pass
    
    # Track event
    try:
        from app.services.analytics_service import AnalyticsService
        analytics = AnalyticsService(db)
        await analytics.track_event(
            "quick_checkup_started",
            user_id=current_user.id,
            workspace_id=workspace_id,
            properties={
                "brand_name": data.brand_name,
                "domain": data.domain,
                "queries_count": len(query_texts),
                "engines": [e["id"] for e in engines],
            },
        )
    except Exception:
        pass
    
    estimated_time = max(1, (len(query_texts) * len(engines) * 5) // 60)
    
    return QuickCheckupResponse(
        project_id=str(project.id),
        project_name=project.name,
        queries_generated=len(query_texts),
        engines_used=[e["id"] for e in engines],
        tasks_created=len(task_ids),
        estimated_time_minutes=estimated_time,
        message=f"已为「{data.brand_name}」生成 {len(query_texts)} 个查询词，正在使用 {len(engines)} 个引擎进行体检",
    )
