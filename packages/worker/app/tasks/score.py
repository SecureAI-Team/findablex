"""Metric calculation tasks."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select

from app.celery_app import celery_app
from app.db import sync_engine
from app.models import Run, DriftEvent


@celery_app.task(bind=True, name="app.tasks.score.calculate_metrics")
def calculate_metrics(self, run_id: str) -> Dict[str, Any]:
    """Calculate metrics for a run."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_calculate_metrics(run_id))
        return result
    finally:
        loop.close()


async def _calculate_metrics(run_id: str) -> Dict[str, Any]:
    """Async implementation of metric calculation."""
    from app.db import get_db_session
    from app.models import Run, Project, Citation, Metric
    
    async with get_db_session() as db:
        run_uuid = UUID(run_id)
        
        # Load run
        run_result = await db.execute(
            select(Run).where(Run.id == run_uuid)
        )
        run = run_result.scalar_one_or_none()
        
        if not run:
            return {"error": f"Run {run_id} not found"}
        
        # Load project for target domains
        project_result = await db.execute(
            select(Project).where(Project.id == run.project_id)
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            return {"error": f"Project not found for run {run_id}"}
        
        target_domains = project.target_domains or []
        
        # Load citations for this run
        citations_result = await db.execute(
            select(Citation).where(Citation.run_id == run_uuid)
        )
        citations = citations_result.scalars().all()
        
        # Calculate metrics
        metrics_data = calculate_all_metrics(citations, target_domains)
        
        # Save metrics to database
        for metric_type, metric_value in metrics_data.items():
            if isinstance(metric_value, (int, float, Decimal)):
                metric = Metric(
                    run_id=run_uuid,
                    query_item_id=None,  # Aggregate metric
                    metric_type=metric_type,
                    metric_value=Decimal(str(metric_value)),
                    metric_details={"target_domains": target_domains},
                    calculated_at=datetime.now(timezone.utc),
                )
                db.add(metric)
        
        # Update run with health score
        health_score = int(metrics_data.get("health_score", 0))
        run.health_score = health_score
        run.summary_metrics = metrics_data
        
        await db.commit()
        
        # Trigger report generation
        from app.tasks.report import generate_report
        generate_report.delay(run_id)
        
        return {
            "run_id": run_id,
            "status": "success",
            "metrics": metrics_data,
            "health_score": health_score,
        }


def calculate_all_metrics(
    citations: List[Any],
    target_domains: List[str],
) -> Dict[str, Any]:
    """Calculate all metrics for citations."""
    if not citations:
        return {
            "visibility_rate": 0.0,
            "avg_citation_position": 0.0,
            "citation_count": 0,
            "target_citation_count": 0,
            "top3_rate": 0.0,
            "competitor_share": 0.0,
            "health_score": 0.0,
        }
    
    # Convert target domains to lowercase for comparison
    target_domains_lower = [d.lower() for d in target_domains]
    
    # Get unique query items
    query_ids = set(c.query_item_id for c in citations)
    total_queries = max(len(query_ids), 1)
    
    # Count target domain citations
    target_citations = [
        c for c in citations 
        if c.is_target_domain or (c.source_domain and c.source_domain.lower() in target_domains_lower)
    ]
    target_count = len(target_citations)
    
    # Queries with target domain citation
    queries_with_target = set(c.query_item_id for c in target_citations)
    visibility_rate = len(queries_with_target) / total_queries
    
    # Average position (0-indexed, so lower is better)
    positions = [c.position for c in target_citations if c.position is not None]
    avg_position = sum(positions) / len(positions) if positions else 0
    
    # Top 3 rate (position 0, 1, 2)
    top3_citations = [c for c in target_citations if c.position is not None and c.position < 3]
    top3_rate = len(top3_citations) / target_count if target_count > 0 else 0
    
    # Competitor share (non-target citations)
    competitor_count = len(citations) - target_count
    competitor_share = competitor_count / len(citations) if citations else 0
    
    # Health score (weighted combination, 0-100 scale)
    # Higher visibility = better
    # Lower position = better (normalize to 0-1 where 1 is best)
    position_score = max(0, 1 - (avg_position / 10)) if avg_position >= 0 else 1
    
    health_score = (
        visibility_rate * 40 +
        position_score * 30 +
        top3_rate * 20 +
        (1 - competitor_share) * 10
    )
    
    return {
        "visibility_rate": round(visibility_rate, 4),
        "avg_citation_position": round(avg_position, 2),
        "citation_count": len(citations),
        "target_citation_count": target_count,
        "top3_rate": round(top3_rate, 4),
        "competitor_share": round(competitor_share, 4),
        "health_score": round(health_score, 2),
    }


@celery_app.task(bind=True, name="app.tasks.score.detect_drift")
def detect_drift(
    self,
    current_run_id: str,
    baseline_run_id: str,
) -> Dict[str, Any]:
    """Detect drift between two runs."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_detect_drift(current_run_id, baseline_run_id))
        return result
    finally:
        loop.close()


async def _detect_drift(current_run_id: str, baseline_run_id: str) -> Dict[str, Any]:
    """Async implementation of drift detection."""
    from app.db import get_db_session
    from app.models import Run
    
    async with get_db_session() as db:
        current_uuid = UUID(current_run_id)
        baseline_uuid = UUID(baseline_run_id)
        
        # Load both runs
        current_result = await db.execute(
            select(Run).where(Run.id == current_uuid)
        )
        current_run = current_result.scalar_one_or_none()
        
        baseline_result = await db.execute(
            select(Run).where(Run.id == baseline_uuid)
        )
        baseline_run = baseline_result.scalar_one_or_none()
        
        if not current_run or not baseline_run:
            return {"error": "Run not found"}
        
        # Calculate drift
        drift_events = calculate_drift(
            baseline_run.summary_metrics or {},
            current_run.summary_metrics or {},
        )
        
        return {
            "current_run_id": current_run_id,
            "baseline_run_id": baseline_run_id,
            "drift_events": drift_events,
        }


@celery_app.task(bind=True, name="app.tasks.score.detect_drift_all")
def detect_drift_all(self) -> Dict[str, Any]:
    """Periodic task to detect drift for all active projects.
    
    Runs daily to check for significant metric changes since last run.
    """
    from sqlalchemy import select, func, and_
    from sqlalchemy.orm import Session
    from datetime import datetime, timedelta
    
    projects_checked = 0
    drift_events_created = 0
    errors = []
    
    with Session(sync_engine) as session:
        try:
            # Query active projects (projects with runs in last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Get distinct project_ids with recent runs
            project_ids_query = (
                select(Run.project_id)
                .where(Run.completed_at >= cutoff_date)
                .distinct()
            )
            result = session.execute(project_ids_query)
            project_ids = [row[0] for row in result.fetchall()]
            
            for project_id in project_ids:
                projects_checked += 1
                
                try:
                    # Get the two most recent completed runs for this project
                    runs_query = (
                        select(Run)
                        .where(
                            and_(
                                Run.project_id == project_id,
                                Run.status == "completed",
                                Run.summary_metrics.isnot(None),
                            )
                        )
                        .order_by(Run.completed_at.desc())
                        .limit(2)
                    )
                    runs_result = session.execute(runs_query)
                    runs = runs_result.scalars().all()
                    
                    if len(runs) < 2:
                        # Need at least 2 runs to compare
                        continue
                    
                    current_run = runs[0]
                    baseline_run = runs[1]
                    
                    # Calculate drift
                    drift_events = calculate_drift(
                        baseline_run.summary_metrics or {},
                        current_run.summary_metrics or {},
                    )
                    
                    # Save drift events
                    for event_data in drift_events:
                        drift_event = DriftEvent(
                            project_id=project_id,
                            baseline_run_id=baseline_run.id,
                            compare_run_id=current_run.id,
                            drift_type=event_data.get("drift_type", "unknown"),
                            severity=event_data.get("severity", "warning"),
                            metric_name=event_data.get("metric", "unknown"),
                            baseline_value=event_data.get("baseline_value", 0),
                            current_value=event_data.get("current_value", 0),
                            change_percent=event_data.get("change_percent", 0),
                            detected_at=datetime.utcnow(),
                        )
                        session.add(drift_event)
                        drift_events_created += 1
                    
                except Exception as e:
                    errors.append(f"Project {project_id}: {str(e)}")
                    continue
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            return {
                "status": "error",
                "error": str(e),
                "projects_checked": projects_checked,
                "drift_events_created": drift_events_created,
            }
    
    return {
        "status": "success",
        "projects_checked": projects_checked,
        "drift_events_created": drift_events_created,
        "errors": errors if errors else None,
    }


def calculate_drift(
    baseline_metrics: Dict[str, float],
    current_metrics: Dict[str, float],
    thresholds: Dict[str, float] = None,
) -> List[Dict[str, Any]]:
    """Calculate drift between two sets of metrics."""
    if thresholds is None:
        thresholds = {
            "visibility_rate": 0.1,  # 10% drop
            "avg_citation_position": 2.0,  # 2 position drop
            "health_score": 10.0,  # 10 point drop
        }
    
    drift_events = []
    
    for metric, threshold in thresholds.items():
        baseline_value = baseline_metrics.get(metric, 0)
        current_value = current_metrics.get(metric, 0)
        
        # Calculate change
        if baseline_value > 0:
            change = current_value - baseline_value
            change_percent = (change / baseline_value) * 100
        else:
            change = current_value
            change_percent = 0
        
        # Check threshold (negative change for metrics where higher is better)
        if metric == "avg_citation_position":
            # Lower is better for position
            if change > threshold:
                drift_events.append({
                    "metric": metric,
                    "drift_type": "position_drop",
                    "severity": "warning" if change < threshold * 2 else "critical",
                    "baseline_value": baseline_value,
                    "current_value": current_value,
                    "change_percent": change_percent,
                })
        else:
            # Higher is better
            if change < -threshold:
                drift_events.append({
                    "metric": metric,
                    "drift_type": "visibility_loss",
                    "severity": "warning" if abs(change) < threshold * 2 else "critical",
                    "baseline_value": baseline_value,
                    "current_value": current_value,
                    "change_percent": change_percent,
                })
    
    return drift_events
