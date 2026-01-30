"""
Analytics Service - 埋点与事件追踪

追踪关键用户行为以支持产品增长决策:

激活事件:
- user_registered: 用户注册
- template_selected: 选择模板
- queries_generated: 生成查询词
- first_crawl_completed: 首次爬取完成

价值事件:
- report_viewed: 查看报告
- report_exported: 导出报告
- calibration_reviewed: 复核口径错误
- share_link_created: 创建分享链接

转化事件:
- upgrade_clicked: 点击升级
- contact_sales_clicked: 点击联系销售
- payment_initiated: 发起支付

留存事件:
- retest_triggered: 触发复测
- team_member_invited: 邀请团队成员
- workspace_created: 创建工作区
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


# 事件类型定义
EVENT_TYPES = {
    # 页面访问 - PV/UV 追踪
    "page_view": {"category": "traffic", "description": "页面访问"},
    
    # 激活 - 注册→选择模板→生成query→导入1条答案
    "user_registered": {"category": "activation", "description": "用户注册"},
    "template_selected": {"category": "activation", "description": "选择模板"},
    "queries_generated": {"category": "activation", "description": "生成查询词"},
    "first_answer_imported": {"category": "activation", "description": "导入第一条答案"},
    "first_crawl_completed": {"category": "activation", "description": "首次爬取完成"},
    "first_report_viewed": {"category": "activation", "description": "首次查看报告"},
    "activation_10min": {"category": "activation", "description": "10分钟内完成激活"},
    
    # 价值 - 报告页停留、口径错误点击、导出/分享率
    "report_viewed": {"category": "value", "description": "查看报告"},
    "report_dwell_time": {"category": "value", "description": "报告页停留时长"},
    "report_exported": {"category": "value", "description": "导出报告"},
    "report_shared": {"category": "value", "description": "分享报告"},
    "calibration_error_clicked": {"category": "value", "description": "点击口径错误"},
    "calibration_reviewed": {"category": "value", "description": "复核口径错误"},
    "compare_report_viewed": {"category": "value", "description": "查看对比报告"},
    
    # 转化 - 解锁点击、复测对比点击、漂移预警点击、联系销售点击
    "upgrade_clicked": {"category": "conversion", "description": "点击升级"},
    "unlock_queries_clicked": {"category": "conversion", "description": "解锁更多问题条数点击"},
    "retest_compare_clicked": {"category": "conversion", "description": "复测对比点击"},
    "drift_warning_clicked": {"category": "conversion", "description": "漂移预警点击"},
    "plan_viewed": {"category": "conversion", "description": "查看套餐"},
    "contact_sales_clicked": {"category": "conversion", "description": "联系销售"},
    "contact_sales_submitted": {"category": "conversion", "description": "提交联系销售表单"},
    "payment_initiated": {"category": "conversion", "description": "发起支付"},
    "payment_completed": {"category": "conversion", "description": "支付完成"},
    
    # 留存 - 次月复测、团队邀请
    "retest_triggered": {"category": "retention", "description": "触发复测"},
    "monthly_retest": {"category": "retention", "description": "次月复测完成"},
    "team_member_invited": {"category": "retention", "description": "邀请成员"},
    "team_member_joined": {"category": "retention", "description": "成员加入"},
    "project_created": {"category": "retention", "description": "创建项目"},
    "login": {"category": "retention", "description": "登录"},
    "workspace_created": {"category": "retention", "description": "创建工作区"},
}


class AnalyticsService:
    """事件追踪服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def track_event(
        self,
        event_type: str,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        记录用户行为事件
        
        Args:
            event_type: 事件类型 (如 'user_registered')
            user_id: 用户ID
            workspace_id: 工作区ID
            properties: 事件属性
        """
        event_info = EVENT_TYPES.get(event_type, {})
        
        # 使用 AuditLog 存储事件 (复用已有模型)
        event = AuditLog(
            user_id=user_id,
            action=event_type,
            resource_type="event",
            new_values={
                "category": event_info.get("category", "unknown"),
                "description": event_info.get("description", ""),
                "workspace_id": str(workspace_id) if workspace_id else None,
                "properties": properties or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        
        return event
    
    async def get_user_events(
        self,
        user_id: UUID,
        event_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """获取用户的事件历史"""
        query = select(AuditLog).where(
            and_(
                AuditLog.user_id == user_id,
                AuditLog.resource_type == "event",
            )
        )
        
        if event_type:
            query = query.where(AuditLog.action == event_type)
        
        query = query.order_by(AuditLog.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_event_counts(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """获取事件统计"""
        query = select(
            AuditLog.action,
            func.count(AuditLog.id)
        ).where(AuditLog.resource_type == "event")
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.group_by(AuditLog.action)
        
        result = await self.db.execute(query)
        return dict(result.all())
    
    async def get_funnel_metrics(
        self,
        start_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取漏斗指标
        
        激活漏斗: 注册 -> 选模板 -> 生成query -> 首次爬取
        转化漏斗: 查看报告 -> 点击升级 -> 联系销售 -> 支付
        """
        counts = await self.get_event_counts(start_date)
        
        # 激活漏斗
        registered = counts.get("user_registered", 0)
        template_selected = counts.get("template_selected", 0)
        queries_generated = counts.get("queries_generated", 0)
        first_crawl = counts.get("first_crawl_completed", 0)
        
        activation_rate = round(first_crawl / registered * 100, 1) if registered > 0 else 0
        
        # 转化漏斗
        report_viewed = counts.get("report_viewed", 0)
        upgrade_clicked = counts.get("upgrade_clicked", 0)
        contact_sales = counts.get("contact_sales_clicked", 0)
        payment_completed = counts.get("payment_completed", 0)
        
        conversion_rate = round(payment_completed / report_viewed * 100, 1) if report_viewed > 0 else 0
        
        return {
            "activation_funnel": {
                "stages": [
                    {"name": "注册", "count": registered, "rate": 100},
                    {"name": "选模板", "count": template_selected, "rate": round(template_selected / registered * 100, 1) if registered > 0 else 0},
                    {"name": "生成Query", "count": queries_generated, "rate": round(queries_generated / registered * 100, 1) if registered > 0 else 0},
                    {"name": "首次爬取", "count": first_crawl, "rate": round(first_crawl / registered * 100, 1) if registered > 0 else 0},
                ],
                "overall_rate": activation_rate,
            },
            "conversion_funnel": {
                "stages": [
                    {"name": "查看报告", "count": report_viewed, "rate": 100},
                    {"name": "点击升级", "count": upgrade_clicked, "rate": round(upgrade_clicked / report_viewed * 100, 1) if report_viewed > 0 else 0},
                    {"name": "联系销售", "count": contact_sales, "rate": round(contact_sales / report_viewed * 100, 1) if report_viewed > 0 else 0},
                    {"name": "完成支付", "count": payment_completed, "rate": round(payment_completed / report_viewed * 100, 1) if report_viewed > 0 else 0},
                ],
                "overall_rate": conversion_rate,
            },
            "key_metrics": {
                "total_registered": registered,
                "activation_rate": activation_rate,
                "conversion_rate": conversion_rate,
                "reports_generated": counts.get("report_viewed", 0),
            },
        }
    
    async def check_user_activation(self, user_id: UUID) -> Dict[str, bool]:
        """检查用户的激活状态"""
        events = await self.get_user_events(user_id, limit=500)
        event_types = {e.action for e in events}
        
        return {
            "registered": "user_registered" in event_types,
            "selected_template": "template_selected" in event_types,
            "generated_queries": "queries_generated" in event_types,
            "completed_first_crawl": "first_crawl_completed" in event_types,
            "viewed_first_report": "first_report_viewed" in event_types,
            "is_activated": "first_crawl_completed" in event_types,
        }
    
    async def get_traffic_metrics(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        获取流量指标 (PV/UV/DAU)
        
        - PV (Page Views): 页面浏览量，每次访问计数
        - UV (Unique Visitors): 独立访客数，按 user_id 或 IP 去重
        - DAU (Daily Active Users): 日活跃用户，按天计算登录用户
        """
        from sqlalchemy import cast, Date, distinct
        from sqlalchemy.dialects.postgresql import JSONB
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # PV - 页面访问总次数
        pv_query = select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.action == "page_view",
                AuditLog.resource_type == "event",
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date,
            )
        )
        pv_result = await self.db.execute(pv_query)
        total_pv = pv_result.scalar() or 0
        
        # UV - 独立访客数 (按 user_id 去重)
        uv_query = select(func.count(distinct(AuditLog.user_id))).where(
            and_(
                AuditLog.action == "page_view",
                AuditLog.resource_type == "event",
                AuditLog.user_id.isnot(None),
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date,
            )
        )
        uv_result = await self.db.execute(uv_query)
        total_uv = uv_result.scalar() or 0
        
        # DAU - 日活跃用户 (今日登录用户数)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        dau_query = select(func.count(distinct(AuditLog.user_id))).where(
            and_(
                AuditLog.action.in_(["login", "page_view"]),
                AuditLog.resource_type == "event",
                AuditLog.user_id.isnot(None),
                AuditLog.created_at >= today_start,
            )
        )
        dau_result = await self.db.execute(dau_query)
        today_dau = dau_result.scalar() or 0
        
        # 按日统计 PV 趋势
        daily_pv_query = select(
            func.date_trunc('day', AuditLog.created_at).label('date'),
            func.count(AuditLog.id).label('pv'),
        ).where(
            and_(
                AuditLog.action == "page_view",
                AuditLog.resource_type == "event",
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date,
            )
        ).group_by(
            func.date_trunc('day', AuditLog.created_at)
        ).order_by(
            func.date_trunc('day', AuditLog.created_at)
        )
        daily_pv_result = await self.db.execute(daily_pv_query)
        daily_pv = [
            {"date": row.date.strftime("%Y-%m-%d") if row.date else None, "pv": row.pv}
            for row in daily_pv_result
        ]
        
        # 按日统计 UV 趋势
        daily_uv_query = select(
            func.date_trunc('day', AuditLog.created_at).label('date'),
            func.count(distinct(AuditLog.user_id)).label('uv'),
        ).where(
            and_(
                AuditLog.action == "page_view",
                AuditLog.resource_type == "event",
                AuditLog.user_id.isnot(None),
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date,
            )
        ).group_by(
            func.date_trunc('day', AuditLog.created_at)
        ).order_by(
            func.date_trunc('day', AuditLog.created_at)
        )
        daily_uv_result = await self.db.execute(daily_uv_query)
        daily_uv = [
            {"date": row.date.strftime("%Y-%m-%d") if row.date else None, "uv": row.uv}
            for row in daily_uv_result
        ]
        
        # 按日统计 DAU 趋势 (有登录或访问行为的用户)
        daily_dau_query = select(
            func.date_trunc('day', AuditLog.created_at).label('date'),
            func.count(distinct(AuditLog.user_id)).label('dau'),
        ).where(
            and_(
                AuditLog.action.in_(["login", "page_view"]),
                AuditLog.resource_type == "event",
                AuditLog.user_id.isnot(None),
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date,
            )
        ).group_by(
            func.date_trunc('day', AuditLog.created_at)
        ).order_by(
            func.date_trunc('day', AuditLog.created_at)
        )
        daily_dau_result = await self.db.execute(daily_dau_query)
        daily_dau = [
            {"date": row.date.strftime("%Y-%m-%d") if row.date else None, "dau": row.dau}
            for row in daily_dau_result
        ]
        
        # 计算平均值
        avg_daily_pv = round(total_pv / max(days, 1), 1)
        avg_daily_uv = round(total_uv / max(days, 1), 1) if daily_uv else 0
        avg_daily_dau = round(sum(d["dau"] for d in daily_dau) / max(len(daily_dau), 1), 1) if daily_dau else 0
        
        # 热门页面
        top_pages_query = select(
            AuditLog.new_values['properties']['page_name'].label('page_name'),
            func.count(AuditLog.id).label('count'),
        ).where(
            and_(
                AuditLog.action == "page_view",
                AuditLog.resource_type == "event",
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date,
            )
        ).group_by(
            AuditLog.new_values['properties']['page_name']
        ).order_by(
            func.count(AuditLog.id).desc()
        ).limit(10)
        
        try:
            top_pages_result = await self.db.execute(top_pages_query)
            top_pages = [
                {"page": row.page_name or "unknown", "count": row.count}
                for row in top_pages_result
            ]
        except Exception:
            # JSONB 查询可能失败，返回空列表
            top_pages = []
        
        return {
            "summary": {
                "total_pv": total_pv,
                "total_uv": total_uv,
                "today_dau": today_dau,
                "avg_daily_pv": avg_daily_pv,
                "avg_daily_uv": avg_daily_uv,
                "avg_daily_dau": avg_daily_dau,
            },
            "trends": {
                "daily_pv": daily_pv,
                "daily_uv": daily_uv,
                "daily_dau": daily_dau,
            },
            "top_pages": top_pages,
            "period_days": days,
        }
