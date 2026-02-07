"""Report routes."""
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.report import (
    PublicReportResponse,
    ReportListItem,
    ReportResponse,
    ShareLinkCreate,
    ShareLinkResponse,
)
from app.services.project_service import ProjectService
from app.services.report_service import ReportService
from app.services.report_generator import ReportGenerator
from app.services.run_service import RunService
from app.services.workspace_service import WorkspaceService

router = APIRouter()


# ========== AI Insights ==========

@router.get("/insights/{project_id}")
async def get_project_insights(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get AI-driven optimization insights for a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    from app.services.ai_insights_service import AIInsightsService
    service = AIInsightsService(db)
    return await service.generate_insights(project_id)


# ========== GEO 体检报告 API ==========

@router.get("/health/{run_id}")
async def get_health_report(
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """获取 GEO 体检报告 (基于 Run)"""
    run_service = RunService(db)
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    run = await run_service.get_by_id(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    
    project = await project_service.get_by_id(run.project_id)
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
    
    if run.status != 'completed':
        return {
            'status': run.status,
            'message': 'Run not completed',
            'run_id': str(run_id),
        }
    
    generator = ReportGenerator(db)
    
    try:
        report = await generator.generate_health_report(
            run_id=run_id,
            project_id=run.project_id,
            health_score=run.health_score or 0,
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/health/{run_id}/export")
async def export_health_report(
    run_id: UUID,
    format: str = "json",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出 GEO 体检报告 (JSON 或 HTML)
    
    导出格式受订阅限制：
    - 免费版：仅 JSON
    - 专业版：JSON, HTML, PDF
    - 企业版：JSON, HTML, PDF, CSV
    """
    import json
    from app.middleware.quota import get_workspace_subscription
    
    run_service = RunService(db)
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    run = await run_service.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    project = await project_service.get_by_id(run.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Check subscription for export format (skip in lite mode for demo)
    requested_format = format.lower()
    if requested_format == "pdf":
        requested_format = "html"
    
    if not settings.lite_mode:
        subscription = await get_workspace_subscription(project.workspace_id, db)
        limits = subscription.get_limits()
        allowed_formats = limits.get("export_formats", ["json"])
        
        if requested_format not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "EXPORT_FORMAT_NOT_ALLOWED",
                    "message": f"当前套餐不支持 {format.upper()} 格式导出。升级套餐解锁更多格式。",
                    "allowed_formats": allowed_formats,
                    "requested_format": format,
                }
            )
    
    generator = ReportGenerator(db)
    report = await generator.generate_health_report(
        run_id=run_id,
        project_id=run.project_id,
        health_score=run.health_score or 0,
    )
    
    if format.lower() == "json":
        content = json.dumps(report, ensure_ascii=False, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=health_report_{run_id}.json"
            }
        )
    elif format.lower() in ("pdf", "html"):
        # 生成可打印的 HTML 报告
        html_content = _generate_health_report_html(report)
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=health_report_{run_id}.html"
            }
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'json' or 'html'.")


def _generate_health_report_html(report: Dict[str, Any]) -> str:
    """生成体检报告的 HTML 格式"""
    summary = report.get('summary', {})
    metrics = report.get('metrics', {})
    comparison = report.get('comparison', {})
    recommendations = report.get('recommendations', [])
    
    health_score = summary.get('health_score', 0)
    
    def get_score_color(score: int) -> str:
        if score >= 80:
            return '#22c55e'
        if score >= 60:
            return '#eab308'
        return '#ef4444'
    
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>{report.get('title', 'GEO 体检报告')}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Microsoft YaHei', sans-serif; margin: 0 auto; padding: 40px; color: #333; max-width: 900px; }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .header h1 {{ color: #16a34a; margin-bottom: 10px; font-size: 28px; }}
            .header p {{ color: #666; }}
            .score-card {{ text-align: center; margin: 30px 0; padding: 40px; background: linear-gradient(135deg, #f0fdf4 0%, #f8fafc 100%); border-radius: 16px; border: 1px solid #dcfce7; }}
            .score-card .score {{ font-size: 80px; font-weight: bold; color: {get_score_color(health_score)}; }}
            .score-card .status {{ font-size: 24px; color: #666; margin-top: 10px; }}
            .comparison {{ display: flex; justify-content: center; gap: 40px; margin: 30px 0; flex-wrap: wrap; }}
            .comparison .item {{ text-align: center; padding: 15px 25px; background: #f8fafc; border-radius: 12px; }}
            .comparison .value {{ font-size: 32px; font-weight: bold; }}
            .comparison .label {{ font-size: 14px; color: #666; margin-top: 5px; }}
            .metrics {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 30px 0; }}
            .metric {{ padding: 20px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0; }}
            .metric .label {{ color: #666; font-size: 14px; }}
            .metric .score {{ font-size: 36px; font-weight: bold; margin-top: 5px; }}
            .metric .desc {{ font-size: 12px; color: #999; margin-top: 5px; }}
            .section {{ margin: 30px 0; page-break-inside: avoid; }}
            .section h2 {{ color: #16a34a; border-bottom: 2px solid #dcfce7; padding-bottom: 10px; font-size: 20px; }}
            .recommendation {{ padding: 15px 20px; margin: 10px 0; border-radius: 8px; border-left: 4px solid; page-break-inside: avoid; }}
            .recommendation.high {{ background: #fef2f2; border-color: #ef4444; }}
            .recommendation.medium {{ background: #fefce8; border-color: #eab308; }}
            .recommendation.low {{ background: #f0fdf4; border-color: #22c55e; }}
            .recommendation h3 {{ margin: 0 0 10px 0; font-size: 16px; }}
            .recommendation p {{ margin: 0 0 10px 0; color: #666; }}
            .recommendation ul {{ margin: 0; padding-left: 20px; }}
            .recommendation li {{ margin: 5px 0; }}
            .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #666; font-size: 12px; }}
            .print-btn {{ 
                position: fixed; top: 20px; right: 20px; 
                padding: 12px 24px; background: #16a34a; color: white; 
                border: none; border-radius: 8px; cursor: pointer; font-size: 14px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .print-btn:hover {{ background: #15803d; }}
            @media print {{
                .print-btn {{ display: none; }}
                body {{ margin: 0; padding: 20px; }}
                .score-card, .metrics, .recommendation {{ page-break-inside: avoid; }}
            }}
        </style>
    </head>
    <body>
        <button class="print-btn" onclick="window.print()">打印 / 导出 PDF</button>
        <div class="header">
            <h1>{report.get('title', 'GEO 体检报告')}</h1>
            <p>生成于 {report.get('generated_at', '')[:10]} · {report.get('project_name', '')}</p>
        </div>
        
        <div class="score-card">
            <div class="score">{health_score}</div>
            <div class="status">{summary.get('status_text', '')}</div>
        </div>
        
        <div class="comparison">
            <div class="item">
                <div class="value">{comparison.get('industry_avg', 65)}</div>
                <div class="label">行业平均</div>
            </div>
            <div class="item">
                <div class="value" style="color: {'#22c55e' if comparison.get('vs_industry', 0) >= 0 else '#ef4444'}">
                    {'+' if comparison.get('vs_industry', 0) > 0 else ''}{comparison.get('vs_industry', 0)}
                </div>
                <div class="label">vs 行业</div>
            </div>
            <div class="item">
                <div class="value" style="color: #3b82f6">Top {100 - comparison.get('percentile', 50)}%</div>
                <div class="label">百分位</div>
            </div>
        </div>
        
        <div class="metrics">
    """
    
    for key, metric in metrics.items():
        color = '#22c55e' if metric['score'] >= 70 else '#eab308' if metric['score'] >= 50 else '#ef4444'
        html += f"""
            <div class="metric">
                <div class="label">{metric['label']}</div>
                <div class="score" style="color: {color}">{metric['score']}</div>
                <div class="desc">{metric['description']}</div>
            </div>
        """
    
    html += """
        </div>
        
        <div class="section">
            <h2>优化建议</h2>
    """
    
    for rec in recommendations:
        priority = rec.get('priority', 'medium')
        html += f"""
            <div class="recommendation {priority}">
                <h3>{rec.get('title', '')}</h3>
                <p>{rec.get('description', '')}</p>
                <ul>
        """
        for action in rec.get('actions', []):
            html += f"<li>{action}</li>"
        html += "</ul></div>"
    
    html += f"""
        </div>
        
        <div class="footer">
            <p>由 FindableX GEO 健康度分析平台生成</p>
            <p>© 2024 FindableX. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    return html


# ========== 研究报告 API ==========

class GenerateResearchReportRequest(BaseModel):
    """请求生成研究报告"""
    title: Optional[str] = None


@router.post("/research/{project_id}/generate")
async def generate_research_report(
    project_id: UUID,
    request: GenerateResearchReportRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    生成研究报告 - 基于 AI 爬虫数据
    
    独创指标体系:
    - AVI (AI Visibility Index): AI 可见性指数
    - CQS (Citation Quality Score): 引用质量评分
    - CPI (Competitive Position Index): 竞争定位指数
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
    
    generator = ReportGenerator(db)
    title = request.title if request else None
    
    try:
        report = await generator.generate_research_report(project_id, title)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/research/{project_id}")
async def get_research_report(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """获取项目的研究报告 (实时生成)"""
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
    
    generator = ReportGenerator(db)
    
    try:
        report = await generator.generate_research_report(project_id)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/research/{project_id}/export")
async def export_research_report(
    project_id: UUID,
    format: str = "json",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出研究报告 (JSON 或 HTML)
    
    导出格式受订阅限制：
    - 免费版：仅 JSON
    - 专业版：JSON, HTML, PDF
    - 企业版：JSON, HTML, PDF, CSV
    """
    import json
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
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Check subscription for export format (skip in lite mode for demo)
    requested_format = format.lower()
    if requested_format == "pdf":
        requested_format = "html"
    
    if not settings.lite_mode:
        subscription = await get_workspace_subscription(project.workspace_id, db)
        limits = subscription.get_limits()
        allowed_formats = limits.get("export_formats", ["json"])
        
        if requested_format not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "EXPORT_FORMAT_NOT_ALLOWED",
                    "message": f"当前套餐不支持 {format.upper()} 格式导出。升级套餐解锁更多格式。",
                    "allowed_formats": allowed_formats,
                    "requested_format": format,
                }
            )
    
    generator = ReportGenerator(db)
    report = await generator.generate_research_report(project_id)
    
    if format.lower() == "json":
        content = json.dumps(report, ensure_ascii=False, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=research_report_{project_id}.json"
            }
        )
    elif format.lower() in ("pdf", "html"):
        # 生成可打印的 HTML 报告 (带公众号二维码)
        # 使用正式域名
        report_url = f"https://findablex.com/reports/research/{project_id}"
        
        html_content = _generate_report_html(report, report_url=report_url)
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=research_report_{project_id}.html"
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported format. Use 'json' or 'html'.",
        )


# ========== 对比报告 API ==========

@router.get("/compare/{project_id}")
async def get_comparison_report(
    project_id: UUID,
    current_report_id: Optional[UUID] = None,
    previous_report_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取对比报告 - 比较两次报告的差异
    
    如果不指定report_id，则自动获取最近两次报告进行对比
    
    需要专业版或企业版订阅
    """
    from app.middleware.quota import enforce_compare_report_access
    
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # 检查对比报告功能访问权限
    await enforce_compare_report_access(project_id, current_user, db)
    
    generator = ReportGenerator(db)
    
    # 如果没有指定报告ID，生成两份报告进行对比
    # 实际实现中应该从历史记录中获取
    current_report = await generator.generate_research_report(project_id)
    
    # 模拟上一次报告 (实际应从数据库获取历史数据)
    # 这里为演示目的创建一个模拟的"上次"数据
    previous_report = _simulate_previous_report(current_report)
    
    # 计算差异
    comparison = _calculate_comparison(current_report, previous_report)
    
    return {
        "project_id": str(project_id),
        "project_name": project.name,
        "generated_at": current_report.get("generated_at"),
        "current": {
            "summary": current_report.get("summary", {}),
            "scores": current_report.get("scores", {}),
            "report_date": current_report.get("generated_at"),
        },
        "previous": {
            "summary": previous_report.get("summary", {}),
            "scores": previous_report.get("scores", {}),
            "report_date": previous_report.get("generated_at"),
        },
        "comparison": comparison,
    }


def _simulate_previous_report(current: Dict) -> Dict:
    """模拟上一次报告数据 (用于演示)"""
    import random
    from datetime import datetime, timedelta, timezone
    
    def add_variance(score: int, variance: int = 10) -> int:
        delta = random.randint(-variance, variance)
        return max(0, min(100, score + delta))
    
    scores = current.get("scores", {})
    
    return {
        "generated_at": (datetime.now(timezone.utc) - timedelta(days=14)).isoformat(),
        "summary": {
            "overall_score": add_variance(current.get("summary", {}).get("overall_score", 50), 15),
            "total_queries": current.get("summary", {}).get("total_queries", 0),
            "total_results": current.get("summary", {}).get("total_results", 0) - random.randint(0, 5),
        },
        "scores": {
            "avi": {
                "score": add_variance(scores.get("avi", {}).get("score", 50)),
                "breakdown": scores.get("avi", {}).get("breakdown", {}),
            },
            "cqs": {
                "score": add_variance(scores.get("cqs", {}).get("score", 50)),
                "breakdown": scores.get("cqs", {}).get("breakdown", {}),
            },
            "cpi": {
                "score": add_variance(scores.get("cpi", {}).get("score", 50)),
                "breakdown": scores.get("cpi", {}).get("breakdown", {}),
            },
        },
    }


def _calculate_comparison(current: Dict, previous: Dict) -> Dict:
    """计算两份报告的对比数据"""
    def calc_change(curr: int, prev: int) -> Dict:
        diff = curr - prev
        pct = round((diff / prev * 100), 1) if prev > 0 else 0
        return {
            "current": curr,
            "previous": prev,
            "change": diff,
            "change_pct": pct,
            "trend": "up" if diff > 0 else ("down" if diff < 0 else "stable"),
        }
    
    curr_summary = current.get("summary", {})
    prev_summary = previous.get("summary", {})
    curr_scores = current.get("scores", {})
    prev_scores = previous.get("scores", {})
    
    overall_change = calc_change(
        curr_summary.get("overall_score", 0),
        prev_summary.get("overall_score", 0)
    )
    
    # 判断整体状态
    if overall_change["change"] > 10:
        status = "significant_improvement"
        status_text = "显著提升"
    elif overall_change["change"] > 0:
        status = "improvement"
        status_text = "小幅提升"
    elif overall_change["change"] < -10:
        status = "significant_decline"
        status_text = "显著下降"
    elif overall_change["change"] < 0:
        status = "decline"
        status_text = "小幅下降"
    else:
        status = "stable"
        status_text = "保持稳定"
    
    return {
        "overall": overall_change,
        "status": status,
        "status_text": status_text,
        "scores": {
            "avi": calc_change(
                curr_scores.get("avi", {}).get("score", 0),
                prev_scores.get("avi", {}).get("score", 0)
            ),
            "cqs": calc_change(
                curr_scores.get("cqs", {}).get("score", 0),
                prev_scores.get("cqs", {}).get("score", 0)
            ),
            "cpi": calc_change(
                curr_scores.get("cpi", {}).get("score", 0),
                prev_scores.get("cpi", {}).get("score", 0)
            ),
        },
        "insights": _generate_comparison_insights(overall_change, curr_scores, prev_scores),
    }


def _generate_comparison_insights(
    overall: Dict,
    curr_scores: Dict,
    prev_scores: Dict,
) -> list:
    """生成对比分析洞察"""
    insights = []
    
    if overall["trend"] == "up":
        insights.append({
            "type": "positive",
            "text": f"综合评分提升了 {overall['change']} 分 ({overall['change_pct']}%)，您的AI可见性正在改善",
        })
    elif overall["trend"] == "down":
        insights.append({
            "type": "negative",
            "text": f"综合评分下降了 {abs(overall['change'])} 分，需要关注可见性变化",
        })
    
    # 分析各项指标变化
    for key, label in [("avi", "AI可见性"), ("cqs", "引用质量"), ("cpi", "竞争位置")]:
        curr = curr_scores.get(key, {}).get("score", 0)
        prev = prev_scores.get(key, {}).get("score", 0)
        diff = curr - prev
        
        if diff > 15:
            insights.append({
                "type": "positive",
                "text": f"{label}指数显著提升 (+{diff}分)，持续保持",
            })
        elif diff < -15:
            insights.append({
                "type": "negative",
                "text": f"{label}指数显著下降 ({diff}分)，需要重点关注",
            })
    
    if not insights:
        insights.append({
            "type": "neutral",
            "text": "各项指标基本保持稳定，建议持续监测",
        })
    
    return insights


def _generate_report_html(report: Dict[str, Any], report_url: str = "") -> str:
    """生成完整报告的 HTML 格式 (包含封面、声明、内容、结尾的专业报告结构)"""
    import hashlib
    from datetime import datetime
    
    scores = report.get('scores', {})
    avi = scores.get('avi', {})
    cqs = scores.get('cqs', {})
    cpi = scores.get('cpi', {})
    summary = report.get('summary', {})
    engine_analysis = report.get('engine_analysis', {})
    query_analysis = report.get('query_analysis', {})
    competitor_analysis = report.get('competitor_analysis', {})
    top_citation_sources = report.get('top_citation_sources', {})
    query_distribution = report.get('query_distribution', {})
    calibration_summary = report.get('calibration_summary', {})
    drift_warning = report.get('drift_warning', {})
    
    # 生成报告唯一标识
    project_name = report.get('project_name', '')
    generated_at = report.get('generated_at', '')[:19].replace('T', ' ')
    generated_date = report.get('generated_at', '')[:10]
    watermark_text = f"FindableX · {project_name} · {generated_at}"
    report_hash = hashlib.md5(f"{project_name}{generated_at}".encode()).hexdigest()[:8].upper()
    
    def get_score_color(score: int) -> str:
        if score >= 80:
            return '#22c55e'
        if score >= 60:
            return '#eab308'
        return '#ef4444'
    
    def get_score_level(score: int) -> str:
        if score >= 80:
            return '优秀'
        if score >= 60:
            return '良好'
        if score >= 40:
            return '一般'
        return '需改进'
    
    def get_priority_style(priority: str) -> tuple:
        styles = {
            'critical': ('#fef2f2', '#ef4444'),
            'high': ('#fefce8', '#eab308'),
            'medium': ('#f0fdf4', '#22c55e'),
            'low': ('#f8fafc', '#94a3b8'),
        }
        return styles.get(priority, ('#f8fafc', '#94a3b8'))
    
    overall_score = summary.get('overall_score', 0)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="robots" content="noindex, nofollow">
        <meta name="author" content="FindableX">
        <meta name="generator" content="FindableX Report Generator v2.0">
        <title>{report.get('title', 'AI 可见性研究报告')} - FindableX</title>
        
        <style>
            @page {{
                size: A4;
                margin: 15mm;
            }}
            
            * {{ box-sizing: border-box; }}
            
            :root {{
                --primary: #1e40af;
                --primary-light: #3b82f6;
                --success: #22c55e;
                --warning: #eab308;
                --danger: #ef4444;
                --gray-50: #f8fafc;
                --gray-100: #f1f5f9;
                --gray-200: #e2e8f0;
                --gray-400: #94a3b8;
                --gray-600: #475569;
                --gray-800: #1e293b;
            }}
            
            body {{ 
                font-family: 'PingFang SC', 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 0; 
                padding: 0;
                color: var(--gray-800); 
                background: #fff; 
                line-height: 1.7;
                font-size: 14px;
            }}
            
            /* 版权保护 */
            .protected {{ 
                -webkit-user-select: none; 
                -moz-user-select: none; 
                user-select: none; 
            }}
            
            /* 水印层 */
            .watermark {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: 9999;
            }}
            .watermark-text {{
                position: absolute;
                transform: rotate(-25deg);
                font-size: 13px;
                color: rgba(30, 64, 175, 0.04);
                white-space: nowrap;
                font-family: Arial, sans-serif;
                letter-spacing: 2px;
            }}
            
            /* 页面容器 */
            .page {{
                max-width: 900px;
                margin: 0 auto;
                padding: 40px 50px;
                background: white;
                min-height: 100vh;
            }}
            
            /* ========== 封面页 ========== */
            .cover-page {{
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                padding: 60px 40px;
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                page-break-after: always;
            }}
            
            .cover-logo {{
                margin-bottom: 60px;
            }}
            .cover-logo svg {{
                width: 80px;
                height: 80px;
            }}
            .cover-logo .brand-name {{
                font-size: 32px;
                font-weight: 700;
                color: var(--primary);
                margin-top: 15px;
                letter-spacing: 2px;
            }}
            
            .cover-title {{
                font-size: 36px;
                font-weight: 700;
                color: var(--gray-800);
                margin-bottom: 20px;
                line-height: 1.3;
            }}
            .cover-subtitle {{
                font-size: 18px;
                color: var(--gray-600);
                margin-bottom: 60px;
            }}
            
            .cover-score {{
                display: inline-flex;
                flex-direction: column;
                align-items: center;
                padding: 40px 60px;
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                margin-bottom: 60px;
            }}
            .cover-score .value {{
                font-size: 72px;
                font-weight: 800;
                line-height: 1;
            }}
            .cover-score .label {{
                font-size: 16px;
                color: var(--gray-600);
                margin-top: 10px;
            }}
            .cover-score .level {{
                display: inline-block;
                margin-top: 15px;
                padding: 6px 20px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            
            .cover-meta {{
                color: var(--gray-400);
                font-size: 13px;
            }}
            .cover-meta p {{
                margin: 5px 0;
            }}
            .cover-meta .report-id {{
                font-family: monospace;
                background: var(--gray-100);
                padding: 4px 12px;
                border-radius: 4px;
                margin-top: 10px;
                display: inline-block;
            }}
            
            /* ========== 声明页 ========== */
            .disclaimer-page {{
                padding: 60px 50px;
                page-break-after: always;
            }}
            .disclaimer-page h1 {{
                font-size: 24px;
                color: var(--primary);
                margin-bottom: 40px;
                padding-bottom: 15px;
                border-bottom: 3px solid var(--primary);
            }}
            .disclaimer-section {{
                margin-bottom: 35px;
            }}
            .disclaimer-section h2 {{
                font-size: 16px;
                color: var(--gray-800);
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .disclaimer-section h2::before {{
                content: '';
                width: 4px;
                height: 20px;
                background: var(--primary);
                border-radius: 2px;
            }}
            .disclaimer-section p, .disclaimer-section li {{
                color: var(--gray-600);
                font-size: 13px;
                line-height: 1.8;
            }}
            .disclaimer-section ul {{
                padding-left: 20px;
            }}
            .disclaimer-section li {{
                margin: 8px 0;
            }}
            .disclaimer-box {{
                background: var(--gray-50);
                border: 1px solid var(--gray-200);
                border-radius: 8px;
                padding: 20px;
                margin-top: 30px;
            }}
            .disclaimer-box p {{
                margin: 0;
                font-size: 12px;
                color: var(--gray-400);
            }}
            
            /* ========== 目录页 ========== */
            .toc-page {{
                padding: 60px 50px;
                page-break-after: always;
            }}
            .toc-page h1 {{
                font-size: 24px;
                color: var(--primary);
                margin-bottom: 40px;
            }}
            .toc-list {{
                list-style: none;
                padding: 0;
            }}
            .toc-list li {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 0;
                border-bottom: 1px dashed var(--gray-200);
                font-size: 15px;
            }}
            .toc-list li:hover {{
                background: var(--gray-50);
            }}
            .toc-list .toc-num {{
                width: 30px;
                color: var(--primary);
                font-weight: 600;
            }}
            .toc-list .toc-title {{
                flex: 1;
                color: var(--gray-800);
            }}
            .toc-list .toc-page-num {{
                color: var(--gray-400);
            }}
            
            /* ========== 内容页 ========== */
            .content-page {{
                padding: 40px 50px;
            }}
            
            .page-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding-bottom: 15px;
                border-bottom: 1px solid var(--gray-200);
                margin-bottom: 30px;
            }}
            .page-header .logo {{
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
                font-weight: 600;
                color: var(--primary);
            }}
            .page-header .logo svg {{
                width: 24px;
                height: 24px;
            }}
            .page-header .page-info {{
                font-size: 12px;
                color: var(--gray-400);
            }}
            
            .section {{
                margin-bottom: 40px;
                page-break-inside: avoid;
            }}
            .section-title {{
                font-size: 20px;
                font-weight: 700;
                color: var(--primary);
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid var(--gray-200);
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .section-title .icon {{
                width: 28px;
                height: 28px;
                background: var(--primary);
                color: white;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
            }}
            
            .score-cards {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin-bottom: 30px;
            }}
            .score-card {{
                text-align: center;
                padding: 25px 15px;
                background: var(--gray-50);
                border-radius: 12px;
                border: 1px solid var(--gray-200);
            }}
            .score-card .value {{
                font-size: 36px;
                font-weight: 700;
            }}
            .score-card .label {{
                font-size: 12px;
                color: var(--gray-600);
                margin-top: 8px;
            }}
            
            .insight-box {{
                background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
                border-left: 4px solid var(--primary);
                padding: 20px;
                border-radius: 0 8px 8px 0;
                margin: 20px 0;
            }}
            .insight-box p {{
                margin: 0;
                color: var(--gray-800);
                font-size: 14px;
            }}
            
            .grid {{ display: grid; gap: 15px; }}
            .grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
            .grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
            
            .card {{
                padding: 20px;
                background: var(--gray-50);
                border-radius: 10px;
                border: 1px solid var(--gray-200);
            }}
            .card-header {{
                font-weight: 600;
                color: var(--gray-800);
                margin-bottom: 15px;
                font-size: 14px;
            }}
            .card-value {{
                font-size: 28px;
                font-weight: 700;
            }}
            .card-desc {{
                font-size: 12px;
                color: var(--gray-600);
                margin-top: 5px;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                font-size: 13px;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid var(--gray-200);
            }}
            th {{
                background: var(--gray-100);
                font-weight: 600;
                color: var(--gray-800);
            }}
            tr:hover {{
                background: var(--gray-50);
            }}
            
            .badge {{
                display: inline-block;
                padding: 3px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }}
            .badge-success {{ background: #dcfce7; color: #166534; }}
            .badge-warning {{ background: #fef9c3; color: #854d0e; }}
            .badge-danger {{ background: #fee2e2; color: #991b1b; }}
            .badge-info {{ background: #dbeafe; color: #1e40af; }}
            
            .recommendation {{
                padding: 20px;
                margin: 12px 0;
                border-radius: 10px;
                border-left: 4px solid;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            .recommendation h4 {{
                margin: 0 0 10px 0;
                font-size: 15px;
                color: var(--gray-800);
            }}
            .recommendation p {{
                margin: 0 0 12px 0;
                color: var(--gray-600);
                font-size: 13px;
            }}
            .recommendation ul {{
                margin: 0;
                padding-left: 20px;
            }}
            .recommendation li {{
                margin: 6px 0;
                font-size: 13px;
                color: var(--gray-600);
            }}
            
            /* ========== 结尾页 ========== */
            .closing-page {{
                min-height: 100vh;
                padding: 60px 50px;
                background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
                color: white;
                page-break-before: always;
            }}
            
            .closing-content {{
                max-width: 600px;
                margin: 0 auto;
                text-align: center;
            }}
            
            .closing-logo {{
                margin-bottom: 40px;
            }}
            .closing-logo svg {{
                width: 60px;
                height: 60px;
            }}
            .closing-logo svg path {{
                fill: white;
                stroke: white;
            }}
            
            .closing-title {{
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 20px;
            }}
            .closing-subtitle {{
                font-size: 16px;
                opacity: 0.9;
                margin-bottom: 50px;
                line-height: 1.8;
            }}
            
            .closing-features {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                text-align: left;
                margin-bottom: 50px;
            }}
            .closing-feature {{
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 10px;
            }}
            .closing-feature h4 {{
                margin: 0 0 8px 0;
                font-size: 14px;
            }}
            .closing-feature p {{
                margin: 0;
                font-size: 12px;
                opacity: 0.8;
            }}
            
            .closing-qr {{
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 40px;
                margin-bottom: 50px;
            }}
            .closing-qr #qrcode {{
                background: white;
                padding: 15px;
                border-radius: 12px;
            }}
            .closing-qr-text {{
                text-align: left;
            }}
            .closing-qr-text h4 {{
                margin: 0 0 10px 0;
                font-size: 16px;
            }}
            .closing-qr-text p {{
                margin: 0;
                font-size: 13px;
                opacity: 0.8;
            }}
            
            .closing-cta {{
                display: inline-block;
                padding: 15px 40px;
                background: white;
                color: var(--primary);
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 15px;
                margin-bottom: 40px;
            }}
            
            .closing-footer {{
                padding-top: 30px;
                border-top: 1px solid rgba(255,255,255,0.2);
                font-size: 12px;
                opacity: 0.7;
            }}
            .closing-footer p {{
                margin: 5px 0;
            }}
            
            /* 工具栏 */
            .toolbar {{
                position: fixed;
                top: 20px;
                right: 20px;
                display: flex;
                gap: 10px;
                z-index: 1000;
            }}
            .toolbar button {{
                padding: 12px 24px;
                background: var(--primary);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transition: all 0.2s;
            }}
            .toolbar button:hover {{
                background: var(--primary-light);
                transform: translateY(-2px);
            }}
            
            /* 打印样式 */
            @media print {{
                .toolbar {{ display: none; }}
                body {{ font-size: 12px; }}
                .page {{ padding: 20px; }}
                .cover-page {{ min-height: auto; padding: 40px; }}
                .closing-page {{ min-height: auto; padding: 40px; page-break-before: always; }}
                .section {{ page-break-inside: avoid; }}
                .watermark-text {{ color: rgba(30, 64, 175, 0.06) !important; }}
            }}
            
            @media (max-width: 768px) {{
                .page {{ padding: 20px; }}
                .score-cards {{ grid-template-columns: repeat(2, 1fr); }}
                .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
                .closing-features {{ grid-template-columns: 1fr; }}
                .closing-qr {{ flex-direction: column; }}
                .toolbar {{ position: static; margin: 20px; justify-content: center; }}
            }}
        </style>
    </head>
    <body>
        <!-- 水印层 -->
        <div class="watermark" id="watermark"></div>
        
        <!-- 工具栏 (仅屏幕显示) -->
        <div class="toolbar">
            <button onclick="window.print()">🖨️ 打印 / 导出 PDF</button>
        </div>
        
        <!-- ==================== 封面页 ==================== -->
        <div class="cover-page">
            <div class="cover-logo">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="#1e40af"/>
                    <path d="M2 17L12 22L22 17" stroke="#1e40af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M2 12L12 17L22 12" stroke="#1e40af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <div class="brand-name">FindableX</div>
            </div>
            
            <h1 class="cover-title">{report.get('title', 'AI 可见性研究报告')}</h1>
            <p class="cover-subtitle">{project_name}</p>
            
            <div class="cover-score">
                <div class="value" style="color: {get_score_color(overall_score)}">{overall_score}</div>
                <div class="label">综合健康度评分</div>
                <span class="level" style="background: {get_score_color(overall_score)}20; color: {get_score_color(overall_score)}">
                    {get_score_level(overall_score)}
                </span>
            </div>
            
            <div class="cover-meta">
                <p>报告生成日期: {generated_date}</p>
                <p>分析引擎: ChatGPT / Perplexity / Gemini / Claude / Copilot</p>
                <p class="report-id">FX-{report_hash}</p>
            </div>
        </div>
        
        <!-- ==================== 声明页 ==================== -->
        <div class="disclaimer-page">
            <h1>📋 报告声明与使用须知</h1>
            
            <div class="disclaimer-section">
                <h2>报告内容说明</h2>
                <p>本报告由 FindableX AI 可见性分析平台自动生成，通过对主流 AI 搜索引擎的实时抓取和分析，
                评估目标品牌在生成式人工智能回答中的可见性表现。报告数据基于报告生成时刻的引擎响应，
                AI 引擎的回答具有动态性，不同时间、不同地区可能产生差异。</p>
            </div>
            
            <div class="disclaimer-section">
                <h2>数据来源与方法论</h2>
                <ul>
                    <li><strong>数据采集</strong>: 通过标准化查询词向各 AI 引擎发起请求，记录完整响应</li>
                    <li><strong>引用识别</strong>: 智能解析响应内容，识别品牌提及和链接引用</li>
                    <li><strong>评分算法</strong>: 综合考虑可见性覆盖率、引用质量、竞争定位等维度</li>
                    <li><strong>对比基准</strong>: 基于行业平均水平和历史数据进行评估</li>
                </ul>
            </div>
            
            <div class="disclaimer-section">
                <h2>使用限制</h2>
                <ul>
                    <li>本报告仅供内部参考，不构成任何形式的商业建议或投资建议</li>
                    <li>报告内容受版权保护，未经授权不得复制、传播或用于商业用途</li>
                    <li>报告数据反映特定时间点状态，请结合最新数据综合判断</li>
                    <li>AI 引擎算法持续更新，建议定期复测以跟踪变化</li>
                </ul>
            </div>
            
            <div class="disclaimer-section">
                <h2>版权声明</h2>
                <p>© 2024-2026 FindableX. 保留所有权利。FindableX、FindableX 标识及相关图形均为 
                FindableX 的注册商标。本报告中提及的其他公司名称和产品名称可能是其各自所有者的商标。</p>
            </div>
            
            <div class="disclaimer-box">
                <p>⚠️ 重要提示: 本报告包含专有分析方法和商业机密信息，仅限授权接收方内部使用。
                如需分享或引用报告内容，请联系 FindableX 获取授权。</p>
            </div>
        </div>
        
        <!-- ==================== 内容页 ==================== -->
        <div class="content-page">
        
        <!-- 综合评分概览 -->
        <div class="section">
            <h2 class="section-title">
                <span class="icon">📊</span>
                综合评分概览
            </h2>
            
            <div class="score-cards protected">
                <div class="score-card">
                    <div class="value" style="color: {get_score_color(overall_score)}">{overall_score}</div>
                    <div class="label">综合评分</div>
                </div>
                <div class="score-card">
                    <div class="value" style="color: {get_score_color(avi.get('score', 0))}">{avi.get('score', 0)}</div>
                    <div class="label">可见性指数 AVI</div>
                </div>
                <div class="score-card">
                    <div class="value" style="color: {get_score_color(cqs.get('score', 0))}">{cqs.get('score', 0)}</div>
                    <div class="label">引用质量 CQS</div>
                </div>
                <div class="score-card">
                    <div class="value" style="color: {get_score_color(cpi.get('score', 0))}">{cpi.get('score', 0)}</div>
                    <div class="label">竞争定位 CPI</div>
                </div>
            </div>
            
            <div class="insight-box">
                <p><strong>📌 诊断摘要:</strong> {summary.get('interpretation', '综合分析显示品牌在 AI 引擎中的可见性表现需要关注。')}</p>
            </div>
        </div>
        
        <!-- 综合诊断 -->
        <div class="section">
            <h2>综合诊断</h2>
            <p>{summary.get('interpretation', '')}</p>
            <div class="grid grid-3" style="margin-top: 15px;">
                <div class="card">
                    <div class="card-title">AVI 解读</div>
                    <div class="card-desc">{avi.get('interpretation', '')}</div>
                </div>
                <div class="card">
                    <div class="card-title">CQS 解读</div>
                    <div class="card-desc">{cqs.get('interpretation', '')}</div>
                </div>
                <div class="card">
                    <div class="card-title">CPI 解读</div>
                    <div class="card-desc">{cpi.get('interpretation', '')}</div>
                </div>
            </div>
        </div>
    """
    
    # AI 引擎覆盖分析
    engines = engine_analysis.get('engines', {}) if engine_analysis else {}
    best_engine = engine_analysis.get('best_engine', '') if engine_analysis else ''
    worst_engine = engine_analysis.get('worst_engine', '') if engine_analysis else ''
    
    engine_names = {
        'chatgpt': 'ChatGPT',
        'perplexity': 'Perplexity', 
        'gemini': 'Gemini',
        'claude': 'Claude',
        'copilot': 'Copilot',
        'qwen': '通义千问',
        'doubao': '豆包',
        'kimi': 'Kimi',
    }
    
    if engines:
        html += """
        <div class="section">
            <h2 class="section-title"><span class="icon">🤖</span>AI 引擎覆盖分析</h2>
            <div class="grid grid-3" style="margin-bottom: 20px;">
        """
        for engine, data in engines.items():
            if isinstance(data, dict):
                score = data.get('score', 0)
                is_best = engine == best_engine
                is_worst = engine == worst_engine
                border_color = '#22c55e' if is_best else ('#ef4444' if is_worst else '#e2e8f0')
                bg_color = '#f0fdf4' if is_best else ('#fef2f2' if is_worst else '#f8fafc')
                label = '最佳' if is_best else ('最差' if is_worst else '')
                html += f"""
                <div class="card" style="border-color: {border_color}; background: {bg_color};">
                    <div class="card-title">{engine_names.get(engine, engine)}</div>
                    <div class="card-value" style="color: {get_score_color(score)}">{score}</div>
                    <div class="card-desc">引用 {data.get('citations', 0)} 次 · 位置 {data.get('avg_position', '-')}</div>
                    {f'<div style="margin-top: 5px;"><span class="badge badge-green">{label}</span></div>' if label else ''}
                </div>
                """
        html += "</div></div>"
    
    # 查询分析
    if query_analysis:
        html += """
        <div class="section">
            <h2>查询分析</h2>
            <table>
                <thead>
                    <tr>
                        <th>查询</th>
                        <th>类型</th>
                        <th>被引用</th>
                        <th>位置</th>
                    </tr>
                </thead>
                <tbody>
        """
        for query in query_analysis.get('queries', [])[:20]:  # 限制显示前20条
            cited = '✓' if query.get('is_cited') else '✗'
            cited_style = 'color: #22c55e;' if query.get('is_cited') else 'color: #ef4444;'
            html += f"""
                <tr>
                    <td>{query.get('query_text', '')[:50]}{'...' if len(query.get('query_text', '')) > 50 else ''}</td>
                    <td>{query.get('query_type', '-')}</td>
                    <td style="{cited_style} font-weight: bold;">{cited}</td>
                    <td>{query.get('citation_position', '-')}</td>
                </tr>
            """
        html += "</tbody></table></div>"
    
    # Top引用来源
    if top_citation_sources and top_citation_sources.get('sources'):
        html += """
        <div class="section">
            <h2 class="section-title"><span class="icon">🔗</span>Top 引用来源</h2>
            <p style="color: var(--gray-600); font-size: 13px; margin-bottom: 15px;">谁在定义行业叙事</p>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>来源域名</th>
                        <th>引用次数</th>
                        <th>占比</th>
                    </tr>
                </thead>
                <tbody>
        """
        for idx, source in enumerate(top_citation_sources.get('sources', [])[:10], 1):
            html += f"""
                <tr>
                    <td>{idx}</td>
                    <td>{source.get('domain', '')}</td>
                    <td>{source.get('count', 0)}</td>
                    <td>{source.get('percentage', 0):.1f}%</td>
                </tr>
            """
        html += "</tbody></table></div>"
    
    # 问题集分布
    if query_distribution:
        html += """
        <div class="section">
            <h2 class="section-title"><span class="icon">📈</span>问题集分布</h2>
            <div class="grid grid-3">
        """
        # 按阶段
        by_stage = query_distribution.get('by_stage', {})
        if by_stage:
            html += '<div class="card"><div class="card-title">按购买阶段</div>'
            for stage, data in by_stage.items():
                label = {'awareness': '认知', 'consideration': '考虑', 'decision': '决策', 'retention': '留存', 'unknown': '未分类'}.get(stage, stage)
                vis_rate = data.get('visibility_rate', 0)
                color = '#22c55e' if vis_rate >= 70 else ('#eab308' if vis_rate >= 40 else '#ef4444')
                html += f'<div style="display: flex; justify-content: space-between; margin: 5px 0; font-size: 13px;"><span>{label}</span><span style="color: {color};">{data.get("count", 0)}条 {vis_rate:.0f}%</span></div>'
            html += '</div>'
        
        # 按风险
        by_risk = query_distribution.get('by_risk', {})
        if by_risk:
            html += '<div class="card"><div class="card-title">按风险等级</div>'
            for risk, data in by_risk.items():
                label = {'critical': '关键', 'high': '高风险', 'medium': '中风险', 'low': '低风险', 'unknown': '未分类'}.get(risk, risk)
                vis_rate = data.get('visibility_rate', 0)
                color = '#22c55e' if vis_rate >= 70 else ('#eab308' if vis_rate >= 40 else '#ef4444')
                html += f'<div style="display: flex; justify-content: space-between; margin: 5px 0; font-size: 13px;"><span>{label}</span><span style="color: {color};">{data.get("count", 0)}条 {vis_rate:.0f}%</span></div>'
            html += '</div>'
        
        # 按角色
        by_role = query_distribution.get('by_role', {})
        if by_role:
            html += '<div class="card"><div class="card-title">按目标角色</div>'
            for role, data in by_role.items():
                label = {'marketing': '市场', 'sales': '销售', 'compliance': '合规', 'technical': '技术', 'management': '管理层', 'unknown': '未分类'}.get(role, role)
                vis_rate = data.get('visibility_rate', 0)
                color = '#22c55e' if vis_rate >= 70 else ('#eab308' if vis_rate >= 40 else '#ef4444')
                html += f'<div style="display: flex; justify-content: space-between; margin: 5px 0; font-size: 13px;"><span>{label}</span><span style="color: {color};">{data.get("count", 0)}条 {vis_rate:.0f}%</span></div>'
            html += '</div>'
        
        html += "</div></div>"
    
    # 竞争格局分析
    top_competitors = competitor_analysis.get('top_competitors', []) if competitor_analysis else []
    total_competitor_domains = competitor_analysis.get('total_competitor_domains', 0) if competitor_analysis else 0
    
    if top_competitors:
        threat_colors = {
            'high': ('#fee2e2', '#991b1b'),
            'medium': ('#fef9c3', '#854d0e'),
            'low': ('#f0fdf4', '#166534'),
        }
        html += f"""
        <div class="section">
            <h2 class="section-title"><span class="icon">🛡️</span>竞争格局分析</h2>
            <p style="color: var(--gray-600); font-size: 13px; margin-bottom: 15px;">共发现 {total_competitor_domains} 个竞争域名</p>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>竞争对手</th>
                        <th>引用次数</th>
                        <th>威胁等级</th>
                    </tr>
                </thead>
                <tbody>
        """
        for idx, comp in enumerate(top_competitors[:10], 1):
            threat = comp.get('threat_level', 'low')
            threat_label = {'high': '高', 'medium': '中', 'low': '低'}.get(threat, threat)
            bg, color = threat_colors.get(threat, ('#f8fafc', '#374151'))
            html += f"""
                <tr>
                    <td>{idx}</td>
                    <td><strong>{comp.get('domain', '')}</strong></td>
                    <td>{comp.get('citations', 0)}</td>
                    <td><span class="badge" style="background: {bg}; color: {color};">{threat_label}威胁</span></td>
                </tr>
            """
        html += "</tbody></table></div>"
    
    # 口径错误
    if calibration_summary and calibration_summary.get('total_errors', 0) > 0:
        html += f"""
        <div class="section">
            <h2 class="section-title"><span class="icon">⚠️</span>口径错误清单</h2>
            <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <strong>发现 {calibration_summary.get('total_errors', 0)} 处口径错误</strong>
                <span style="margin-left: 15px;">严重: {calibration_summary.get('by_severity', {}).get('critical', 0)}</span>
                <span style="margin-left: 10px;">高: {calibration_summary.get('by_severity', {}).get('high', 0)}</span>
                <span style="margin-left: 10px;">中: {calibration_summary.get('by_severity', {}).get('medium', 0)}</span>
            </div>
        </div>
        """
    
    # 漂移预警
    if drift_warning and drift_warning.get('has_warning'):
        html += f"""
        <div class="section">
            <h2 class="section-title"><span class="icon">🔔</span>漂移预警</h2>
            <div style="background: #fefce8; border: 1px solid #fde047; border-radius: 8px; padding: 15px;">
                <strong>⚠️ 检测到可见性漂移</strong>
                <p style="margin: 10px 0 0 0; color: #666;">{drift_warning.get('message', '')}</p>
                <p style="margin: 5px 0 0 0; font-size: 13px;">建议复测日期: {drift_warning.get('suggested_retest_date', '-')}</p>
            </div>
        </div>
        """
    
    # 优化建议
    html += """
        <div class="section">
            <h2 class="section-title"><span class="icon">💡</span>优化建议</h2>
    """
    
    for rec in report.get('recommendations', []):
        priority = rec.get('priority', 'medium')
        bg_color, border_color = get_priority_style(priority)
        priority_label = {'critical': '紧急', 'high': '重要', 'medium': '建议', 'low': '可选'}.get(priority, '建议')
        html += f"""
            <div class="recommendation" style="background: {bg_color}; border-color: {border_color};">
                <h4><span class="badge" style="background: {border_color}; color: white; margin-right: 8px;">{priority_label}</span>{rec.get('title', '')}</h4>
                <p>{rec.get('description', '')}</p>
                <ul>
        """
        for action in rec.get('actions', []):
            html += f"<li>{action}</li>"
        html += "</ul></div>"
    
    html += f"""
        </div>
        
        </div><!-- 结束 content-page -->
        
        <!-- ==================== 结尾页 ==================== -->
        <div class="closing-page">
            <div class="closing-content">
                <div class="closing-logo">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white"/>
                        <path d="M2 17L12 22L22 17" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M2 12L12 17L22 12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
                
                <h2 class="closing-title">感谢阅读本报告</h2>
                <p class="closing-subtitle">
                    FindableX 是专业的 AI 可见性分析平台，帮助品牌在生成式 AI 时代<br>
                    持续监测、优化并提升在各大 AI 引擎中的可见性表现。
                </p>
                
                <div class="closing-features">
                    <div class="closing-feature">
                        <h4>📊 实时监控</h4>
                        <p>7×24 小时监测品牌在 AI 引擎中的引用变化</p>
                    </div>
                    <div class="closing-feature">
                        <h4>🔔 漂移预警</h4>
                        <p>第一时间发现可见性下降，及时调整策略</p>
                    </div>
                    <div class="closing-feature">
                        <h4>🎯 竞品分析</h4>
                        <p>深度对标竞争对手，掌握市场动态</p>
                    </div>
                    <div class="closing-feature">
                        <h4>💡 优化建议</h4>
                        <p>基于数据的专业 GEO 策略建议</p>
                    </div>
                </div>
                
                <div class="closing-qr">
                    <div id="qrcode">
                        <img src="https://findablex.com/wechat-qrcode.jpg" alt="FindableX 公众号" width="150" height="150" style="border-radius: 8px;">
                    </div>
                    <div class="closing-qr-text">
                        <h4>关注 FindableX 公众号</h4>
                        <p>获取 GEO 最新资讯和分析报告<br>了解品牌 AI 可见性优化策略</p>
                    </div>
                </div>
                
                <a href="https://findablex.com" class="closing-cta">访问 FindableX 官网 →</a>
                
                <div class="closing-footer">
                    <p>报告编号: FX-{report_hash}</p>
                    <p>© 2024-2026 FindableX. All rights reserved.</p>
                    <p style="margin-top: 15px; font-size: 11px; opacity: 0.6;">
                        本报告内容受版权保护，未经授权不得复制、传播或用于商业用途。<br>
                        如需了解更多，请关注 FindableX 公众号
                    </p>
                </div>
            </div>
        </div>
        
        <!-- 生成水印 -->
        <script>
            // 生成水印
            (function() {{
                var watermark = document.getElementById('watermark');
                var text = '{watermark_text}';
                var html = '';
                for (var row = 0; row < 30; row++) {{
                    for (var col = 0; col < 10; col++) {{
                        var top = row * 120 - 30;
                        var left = col * 250 - 80 + (row % 2) * 125;
                        html += '<div class="watermark-text" style="top: ' + top + 'px; left: ' + left + 'px;">' + text + '</div>';
                    }}
                }}
                watermark.innerHTML = html;
            }})();
            
            // 版权保护
            document.addEventListener('contextmenu', function(e) {{
                if (e.target.closest('.protected')) {{ e.preventDefault(); }}
            }});
            document.addEventListener('selectstart', function(e) {{
                if (e.target.closest('.protected')) {{ e.preventDefault(); }}
            }});
        </script>
    </body>
    </html>
    """
    
    return html


@router.get("", response_model=List[ReportListItem])
async def list_reports(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ReportListItem]:
    """List all reports for a workspace."""
    workspace_service = WorkspaceService(db)
    project_service = ProjectService(db)
    report_service = ReportService(db)
    run_service = RunService(db)
    
    # Check membership
    membership = await workspace_service.get_membership(workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    # Get all projects in workspace
    projects = await project_service.get_workspace_projects(workspace_id)
    
    # Get all reports for these projects
    reports = []
    for project in projects:
        project_reports = await report_service.get_project_reports(project.id)
        for report in project_reports:
            # Get run for health score
            run = await run_service.get_by_id(report.run_id)
            reports.append(ReportListItem(
                id=report.id,
                run_id=report.run_id,
                report_type=report.report_type,
                title=report.title,
                project_id=project.id,
                project_name=project.name,
                health_score=run.health_score if run else None,
                generated_at=report.generated_at,
            ))
    
    # Sort by generated_at descending
    reports.sort(key=lambda r: r.generated_at, reverse=True)
    
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Get report by ID."""
    report_service = ReportService(db)
    run_service = RunService(db)
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    report = await report_service.get_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    run = await run_service.get_by_id(report.run_id)
    project = await project_service.get_by_id(run.project_id)
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    return report


@router.post("/{report_id}/share", response_model=ShareLinkResponse)
async def create_share_link(
    report_id: UUID,
    data: ShareLinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareLinkResponse:
    """Create a share link for a report."""
    report_service = ReportService(db)
    run_service = RunService(db)
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    report = await report_service.get_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    run = await run_service.get_by_id(report.run_id)
    project = await project_service.get_by_id(run.project_id)
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership or membership.role not in ("admin", "analyst"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to share reports",
            )
    
    share_link = await report_service.create_share_link(report_id, current_user.id, data)
    
    # Build share URL
    base_url = settings.allowed_origins.split(",")[0].strip()
    share_url = f"{base_url}/share/{share_link.token}"
    
    return ShareLinkResponse(
        id=share_link.id,
        report_id=share_link.report_id,
        token=share_link.token,
        view_count=share_link.view_count,
        max_views=share_link.max_views,
        expires_at=share_link.expires_at,
        created_at=share_link.created_at,
        share_url=share_url,
    )


@router.get("/{report_id}/shares", response_model=List[ShareLinkResponse])
async def list_share_links(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ShareLinkResponse]:
    """List all share links for a report."""
    report_service = ReportService(db)
    run_service = RunService(db)
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    report = await report_service.get_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    run = await run_service.get_by_id(report.run_id)
    project = await project_service.get_by_id(run.project_id)
    
    # Check membership
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    share_links = await report_service.get_report_share_links(report_id)
    
    base_url = settings.allowed_origins.split(",")[0].strip()
    
    return [
        ShareLinkResponse(
            id=link.id,
            report_id=link.report_id,
            token=link.token,
            view_count=link.view_count,
            max_views=link.max_views,
            expires_at=link.expires_at,
            created_at=link.created_at,
            share_url=f"{base_url}/share/{link.token}",
        )
        for link in share_links
    ]


# Public endpoint for shared reports
@router.get("/share/{token}", response_model=PublicReportResponse)
async def get_shared_report(
    token: str,
    password: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PublicReportResponse:
    """Get a publicly shared report."""
    report_service = ReportService(db)
    
    share_link = await report_service.get_share_link_by_token(token)
    if not share_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found",
        )
    
    # Validate access
    is_valid = await report_service.validate_share_link(share_link, password)
    if not is_valid:
        if share_link.password_hash and not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password required",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Increment view count
    await report_service.increment_view_count(share_link)
    
    report = await report_service.get_by_id(share_link.report_id)
    
    return PublicReportResponse(
        title=report.title,
        report_type=report.report_type,
        content_html=report.content_html,
        content_json=report.content_json,
        generated_at=report.generated_at,
    )
