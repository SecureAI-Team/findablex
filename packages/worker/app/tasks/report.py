"""Report generation tasks."""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select

from app.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.report.generate_report")
def generate_report(self, run_id: str) -> Dict[str, Any]:
    """Generate a report for a run and save to database."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_generate_report(run_id))
        return result
    finally:
        loop.close()


async def _generate_report(run_id: str) -> Dict[str, Any]:
    """Async implementation of report generation."""
    from app.db import get_db_session
    from app.models import Run, Report
    
    async with get_db_session() as db:
        run_uuid = UUID(run_id)
        
        # Load run with metrics
        run_result = await db.execute(
            select(Run).where(Run.id == run_uuid)
        )
        run = run_result.scalar_one_or_none()
        
        if not run:
            return {"error": f"Run {run_id} not found"}
        
        # Get metrics from run
        metrics = run.summary_metrics or {}
        
        # Generate report content
        report_data = generate_checkup_report(run_id, metrics)
        
        # Save report to database
        report = Report(
            run_id=run_uuid,
            report_type=report_data["report_type"],
            title=report_data["title"],
            content_json=report_data["content_json"],
            content_html=report_data["content_html"],
            generated_at=datetime.now(timezone.utc),
        )
        db.add(report)
        
        # Update run status to completed
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        return {
            "run_id": run_id,
            "report_id": str(report.id),
            "status": "success",
            "title": report_data["title"],
        }


def generate_checkup_report(run_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a checkup report."""
    health_score = metrics.get("health_score", 0)
    
    # Determine health status
    if health_score >= 80:
        status = "excellent"
        status_text = "优秀"
        status_color = "green"
    elif health_score >= 60:
        status = "good"
        status_text = "良好"
        status_color = "blue"
    elif health_score >= 40:
        status = "fair"
        status_text = "一般"
        status_color = "yellow"
    else:
        status = "poor"
        status_text = "需改进"
        status_color = "red"
    
    # Generate recommendations
    recommendations = generate_recommendations(metrics)
    
    # Build report content
    content_json = {
        "summary": {
            "health_score": health_score,
            "status": status,
            "status_text": status_text,
            "status_color": status_color,
        },
        "metrics": {
            "visibility_rate": {
                "value": metrics.get("visibility_rate", 0),
                "label": "可见性覆盖率",
                "format": "percent",
            },
            "avg_position": {
                "value": metrics.get("avg_citation_position", 0),
                "label": "平均引用位置",
                "format": "number",
            },
            "citation_count": {
                "value": metrics.get("citation_count", 0),
                "label": "引用总数",
                "format": "number",
            },
            "target_citation_count": {
                "value": metrics.get("target_citation_count", 0),
                "label": "目标域名引用数",
                "format": "number",
            },
            "top3_rate": {
                "value": metrics.get("top3_rate", 0),
                "label": "Top3 出现率",
                "format": "percent",
            },
            "competitor_share": {
                "value": metrics.get("competitor_share", 0),
                "label": "竞争对手占比",
                "format": "percent",
            },
        },
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Generate HTML content
    content_html = generate_report_html(content_json)
    
    return {
        "title": f"GEO 体检报告 - {datetime.now().strftime('%Y-%m-%d')}",
        "report_type": "checkup",
        "content_json": content_json,
        "content_html": content_html,
    }


def generate_recommendations(metrics: Dict[str, Any]) -> list:
    """Generate recommendations based on metrics."""
    recommendations = []
    
    visibility_rate = metrics.get("visibility_rate", 0)
    avg_position = metrics.get("avg_citation_position", 0)
    top3_rate = metrics.get("top3_rate", 0)
    competitor_share = metrics.get("competitor_share", 0)
    
    if visibility_rate < 0.5:
        recommendations.append({
            "priority": "high",
            "category": "visibility",
            "title": "提升内容可见性",
            "description": "您的内容在生成式引擎中的可见性较低，建议优化内容结构和关键词覆盖。",
            "actions": [
                "增加结构化数据标记",
                "优化标题和描述的关键词密度",
                "提高内容的E-E-A-T信号",
            ],
        })
    
    if avg_position > 5:
        recommendations.append({
            "priority": "medium",
            "category": "position",
            "title": "提升引用位置",
            "description": "您的内容虽然被引用，但位置较靠后，建议提高内容权威性。",
            "actions": [
                "获取更多高质量外链",
                "提升内容深度和专业性",
                "增加作者专家背景展示",
            ],
        })
    
    if top3_rate < 0.3:
        recommendations.append({
            "priority": "medium",
            "category": "top_ranking",
            "title": "争取Top3位置",
            "description": "建议针对高价值查询优化内容，争取更靠前的引用位置。",
            "actions": [
                "分析Top3竞争对手的内容策略",
                "优化内容的直接回答性",
                "增加FAQ结构化内容",
            ],
        })
    
    if competitor_share > 0.7:
        recommendations.append({
            "priority": "high",
            "category": "competition",
            "title": "应对竞争压力",
            "description": "竞争对手在相关查询中占据主导位置，需要加强差异化策略。",
            "actions": [
                "分析竞争对手内容优势",
                "强化品牌独特价值主张",
                "增加原创研究和数据支撑",
            ],
        })
    
    if not recommendations:
        recommendations.append({
            "priority": "low",
            "category": "maintenance",
            "title": "保持优势",
            "description": "您的GEO表现良好，建议持续监测并保持内容更新。",
            "actions": [
                "定期更新内容保持时效性",
                "监控竞争对手动态",
                "设置定期复测计划",
            ],
        })
    
    return recommendations


def generate_report_html(content: Dict[str, Any]) -> str:
    """Generate HTML content for report."""
    summary = content.get("summary", {})
    metrics = content.get("metrics", {})
    recommendations = content.get("recommendations", [])
    
    # Build metrics HTML
    metrics_html = ""
    for key, m in metrics.items():
        if m.get('format') == 'percent':
            value_display = f"{m.get('value', 0) * 100:.1f}%"
        else:
            value_display = f"{m.get('value', 0):.1f}" if isinstance(m.get('value'), float) else str(m.get('value', 0))
        
        metrics_html += f'''
        <div class="metric-card">
            <div class="metric-value">{value_display}</div>
            <div class="metric-label">{m.get('label', '')}</div>
        </div>
        '''
    
    # Build recommendations HTML
    recommendations_html = ""
    for r in recommendations:
        actions_html = "".join(f'<li>{action}</li>' for action in r.get('actions', []))
        recommendations_html += f'''
        <div class="recommendation priority-{r.get('priority', 'low')}">
            <h3>{r.get('title', '')}</h3>
            <p>{r.get('description', '')}</p>
            <ul>{actions_html}</ul>
        </div>
        '''
    
    html = f"""
    <div class="geo-report">
        <div class="report-header">
            <h1>GEO 体检报告</h1>
            <div class="health-score health-{summary.get('status', 'unknown')}">
                <span class="score">{summary.get('health_score', 0)}</span>
                <span class="label">{summary.get('status_text', '未知')}</span>
            </div>
        </div>
        
        <div class="metrics-grid">
            {metrics_html}
        </div>
        
        <div class="recommendations">
            <h2>优化建议</h2>
            {recommendations_html}
        </div>
    </div>
    """
    
    return html
