"""
Quota middleware for subscription limit enforcement.

用于检查用户订阅限制的依赖注入函数。
"""
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.project import Project, QueryItem
from app.models.subscription import Subscription, PLANS
from app.services.workspace_service import WorkspaceService


async def get_workspace_subscription(
    workspace_id: UUID,
    db: AsyncSession,
) -> Subscription:
    """获取工作区的订阅信息，如果不存在则创建免费订阅"""
    result = await db.execute(
        select(Subscription).where(Subscription.workspace_id == workspace_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        subscription = Subscription(
            workspace_id=workspace_id,
            plan_code="free",
            status="active",
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
    
    return subscription


async def check_query_limit(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    检查是否可以在项目中创建新的查询词
    
    Returns:
        dict with can_create, current_count, limit, remaining
    
    Raises:
        HTTPException if limit exceeded
    """
    # 获取项目
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 获取订阅
    subscription = await get_workspace_subscription(project.workspace_id, db)
    limits = subscription.get_limits()
    query_limit = limits.get("queries_per_project", 10)
    
    # 获取当前查询词数量
    count_result = await db.execute(
        select(func.count(QueryItem.id)).where(QueryItem.project_id == project_id)
    )
    current_count = count_result.scalar() or 0
    
    # unlimited
    if query_limit == -1:
        return {
            "can_create": True,
            "current_count": current_count,
            "limit": -1,
            "remaining": -1,
        }
    
    remaining = query_limit - current_count
    can_create = remaining > 0
    
    return {
        "can_create": can_create,
        "current_count": current_count,
        "limit": query_limit,
        "remaining": remaining,
    }


async def enforce_query_limit(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    强制检查查询词限制，超出则抛出异常
    """
    quota = await check_query_limit(project_id, current_user, db)
    
    if not quota["can_create"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "QUERY_LIMIT_EXCEEDED",
                "message": f"已达到查询词数量上限 ({quota['limit']} 条)。升级套餐解锁更多。",
                "current": quota["current_count"],
                "limit": quota["limit"],
            }
        )
    
    return quota


async def check_feature_access(
    feature: str,
    workspace_id: UUID,
    db: AsyncSession,
) -> bool:
    """检查功能是否可用"""
    subscription = await get_workspace_subscription(workspace_id, db)
    return subscription.is_feature_enabled(feature)


async def enforce_compare_report_access(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    强制检查对比报告访问权限
    """
    # 获取项目
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    has_access = await check_feature_access("compare_reports", project.workspace_id, db)
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "FEATURE_NOT_AVAILABLE",
                "message": "对比报告功能需要升级到专业版或企业版",
                "feature": "compare_reports",
            }
        )
    
    return {"has_access": True}


async def check_run_quota(
    workspace_id: UUID,
    db: AsyncSession,
) -> dict:
    """
    检查运行配额
    """
    subscription = await get_workspace_subscription(workspace_id, db)
    remaining = subscription.get_remaining_runs()
    
    return {
        "can_run": subscription.can_run(),
        "remaining": remaining,
        "bonus": subscription.bonus_runs,
    }


async def enforce_run_quota(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    强制检查运行配额
    """
    quota = await check_run_quota(workspace_id, db)
    
    if not quota["can_run"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "RUN_LIMIT_EXCEEDED",
                "message": "本月运行次数已用尽。升级套餐获取更多次数。",
                "remaining": quota["remaining"],
            }
        )
    
    return quota


async def increment_run_usage(
    workspace_id: UUID,
    db: AsyncSession,
) -> None:
    """增加运行次数计数"""
    subscription = await get_workspace_subscription(workspace_id, db)
    subscription.increment_usage("runs_this_month")
    await db.commit()
