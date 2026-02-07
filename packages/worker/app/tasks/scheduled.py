"""
Scheduled tasks for FindableX.

These tasks run periodically via Celery Beat:
- Auto GEO checkup (configurable per-project)
- Drift detection comparison
- Usage quota reset
- Subscription expiry checks
- Retest reminders
- Weekly digest generation
"""
import logging
from datetime import datetime, timezone, timedelta

from app.celery_app import celery_app
from app.db import get_session

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.scheduled.auto_checkup_projects")
def auto_checkup_projects():
    """
    Run scheduled auto-checkup for projects that have it enabled.
    
    Checks for projects with schedule_interval set and creates
    crawl tasks if the last checkup was older than the interval.
    """
    import asyncio
    asyncio.run(_auto_checkup_projects_async())


async def _auto_checkup_projects_async():
    """Async implementation of auto-checkup."""
    async with get_session() as db:
        from sqlalchemy import select, and_
        from app.models.project import Project
        from app.models.crawler import CrawlTask
        
        # Find projects that need auto-checkup
        # Look for projects with no recent completed crawl tasks (>7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        result = await db.execute(
            select(Project).where(Project.status == "active")
        )
        projects = result.scalars().all()
        
        for project in projects:
            # Check last crawl task
            task_result = await db.execute(
                select(CrawlTask)
                .where(
                    and_(
                        CrawlTask.project_id == project.id,
                        CrawlTask.status == "completed",
                    )
                )
                .order_by(CrawlTask.completed_at.desc())
                .limit(1)
            )
            last_task = task_result.scalar_one_or_none()
            
            if last_task and last_task.completed_at and last_task.completed_at > week_ago:
                continue  # Recent checkup exists, skip
            
            # Check if project has queries
            from app.models.project import QueryItem
            query_count_result = await db.execute(
                select(QueryItem.id).where(QueryItem.project_id == project.id).limit(1)
            )
            if not query_count_result.scalar_one_or_none():
                continue  # No queries, skip
            
            logger.info(f"Scheduling auto-checkup for project {project.id}: {project.name}")
            
            # Create a crawl task with default engine
            task = CrawlTask(
                project_id=project.id,
                engine="deepseek",  # Default API engine
                status="pending",
                total_queries=0,  # Will be set when task starts
                successful_queries=0,
                failed_queries=0,
                created_at=datetime.now(timezone.utc),
            )
            db.add(task)
            
            # Dispatch to worker
            try:
                from app.tasks.crawl import process_crawl_task
                await db.commit()
                await db.refresh(task)
                process_crawl_task.delay(str(task.id))
            except Exception as e:
                logger.error(f"Failed to dispatch auto-checkup for project {project.id}: {e}")
                await db.rollback()


@celery_app.task(name="app.tasks.scheduled.check_drift_all")
def check_drift_all():
    """
    Run drift detection across all projects.
    
    Compares the latest two completed runs for each project
    and generates drift events for significant changes.
    """
    import asyncio
    asyncio.run(_check_drift_all_async())


async def _check_drift_all_async():
    """Async drift detection implementation."""
    async with get_session() as db:
        from sqlalchemy import select
        from app.models.project import Project
        
        result = await db.execute(
            select(Project).where(Project.status == "active")
        )
        projects = result.scalars().all()
        
        for project in projects:
            try:
                await _check_project_drift(db, project)
            except Exception as e:
                logger.error(f"Drift check failed for project {project.id}: {e}")


async def _check_project_drift(db, project):
    """Check drift for a single project."""
    from sqlalchemy import select, and_
    from app.models.run import Run
    
    # Get the last 2 completed runs
    result = await db.execute(
        select(Run)
        .where(
            and_(
                Run.project_id == project.id,
                Run.status == "completed",
            )
        )
        .order_by(Run.completed_at.desc())
        .limit(2)
    )
    runs = list(result.scalars().all())
    
    if len(runs) < 2:
        return  # Need at least 2 runs to compare
    
    current_run, previous_run = runs[0], runs[1]
    
    if current_run.health_score is None or previous_run.health_score is None:
        return
    
    # Calculate drift
    score_change = current_run.health_score - previous_run.health_score
    change_percent = (score_change / previous_run.health_score * 100) if previous_run.health_score > 0 else 0
    
    # Significant change threshold: 10% or more
    if abs(change_percent) >= 10:
        severity = "critical" if abs(change_percent) >= 20 else "warning"
        
        logger.info(
            f"Drift detected for project {project.name}: "
            f"health score changed by {change_percent:.1f}% "
            f"({previous_run.health_score} -> {current_run.health_score})"
        )
        
        # Send notification
        try:
            from app.services.notification_service import NotificationService
            from app.models.workspace import Membership
            from app.models.user import User
            
            # Get workspace admin users
            members_result = await db.execute(
                select(User)
                .join(Membership, Membership.user_id == User.id)
                .where(
                    and_(
                        Membership.workspace_id == project.workspace_id,
                        Membership.role.in_(["admin", "analyst"]),
                    )
                )
            )
            users = members_result.scalars().all()
            
            from app.services.email_service import email_service
            for user in users:
                await email_service.send_drift_warning_email(
                    to_email=user.email,
                    user_name=user.full_name,
                    project_name=project.name,
                    drift_events=[{
                        "metric_name": "健康度",
                        "severity": severity,
                        "change_percent": change_percent,
                    }],
                )
        except Exception as e:
            logger.error(f"Failed to send drift notification: {e}")


@celery_app.task(name="app.tasks.scheduled.reset_monthly_usage")
def reset_monthly_usage():
    """Reset monthly usage counters for all subscriptions."""
    import asyncio
    asyncio.run(_reset_monthly_usage_async())


async def _reset_monthly_usage_async():
    """Async monthly usage reset."""
    async with get_session() as db:
        from sqlalchemy import select
        from app.models.subscription import Subscription
        
        result = await db.execute(select(Subscription))
        subscriptions = result.scalars().all()
        
        now = datetime.now(timezone.utc)
        
        for sub in subscriptions:
            usage = sub.usage or {}
            last_reset = usage.get("last_reset_at")
            
            if last_reset:
                try:
                    last_reset_date = datetime.fromisoformat(last_reset.replace("Z", "+00:00"))
                    # Only reset if last reset was more than 25 days ago
                    if (now - last_reset_date).days < 25:
                        continue
                except (ValueError, TypeError):
                    pass
            
            sub.usage = {
                "runs_this_month": 0,
                "queries_created": usage.get("queries_created", 0),
                "reports_generated": usage.get("reports_generated", 0),
                "last_reset_at": now.isoformat(),
            }
            
            logger.info(f"Reset monthly usage for workspace {sub.workspace_id}")
        
        await db.commit()


@celery_app.task(name="app.tasks.scheduled.check_subscription_expiry")
def check_subscription_expiry():
    """Check for expiring subscriptions and send renewal reminders."""
    import asyncio
    asyncio.run(_check_subscription_expiry_async())


async def _check_subscription_expiry_async():
    """Async subscription expiry check."""
    async with get_session() as db:
        from sqlalchemy import select, and_
        from app.models.subscription import Subscription, PLANS
        from app.models.workspace import Membership
        from app.models.user import User
        
        now = datetime.now(timezone.utc)
        
        # Find subscriptions expiring in the next 7 days
        expiry_threshold = now + timedelta(days=7)
        
        result = await db.execute(
            select(Subscription).where(
                and_(
                    Subscription.status == "active",
                    Subscription.expires_at.isnot(None),
                    Subscription.expires_at <= expiry_threshold,
                    Subscription.plan_code != "free",
                )
            )
        )
        subscriptions = result.scalars().all()
        
        for sub in subscriptions:
            days_until_expiry = max(0, (sub.expires_at - now).days)
            plan_data = PLANS.get(sub.plan_code, {})
            plan_name = plan_data.get("name", sub.plan_code)
            
            # Only send reminders at 7, 3, 1, 0 days
            if days_until_expiry not in [7, 3, 1, 0]:
                continue
            
            # Get workspace admins
            members_result = await db.execute(
                select(User)
                .join(Membership, Membership.user_id == User.id)
                .where(
                    and_(
                        Membership.workspace_id == sub.workspace_id,
                        Membership.role == "admin",
                    )
                )
            )
            users = members_result.scalars().all()
            
            from app.services.notification_service import NotificationService
            notification_service = NotificationService(db)
            
            for user in users:
                try:
                    await notification_service.send_renewal_reminder(
                        user_email=user.email,
                        user_name=user.full_name,
                        plan_name=plan_name,
                        expires_at=sub.expires_at.strftime("%Y-%m-%d"),
                        days_until_expiry=days_until_expiry,
                    )
                except Exception as e:
                    logger.error(f"Failed to send renewal reminder: {e}")


@celery_app.task(name="app.tasks.scheduled.send_retest_reminders")
def send_retest_reminders():
    """Send retest reminders for projects that haven't been tested recently."""
    import asyncio
    asyncio.run(_send_retest_reminders_async())


async def _send_retest_reminders_async():
    """Async retest reminder implementation."""
    async with get_session() as db:
        from sqlalchemy import select, and_
        from app.models.project import Project
        from app.models.run import Run
        from app.models.workspace import Membership
        from app.models.user import User
        
        two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
        
        result = await db.execute(
            select(Project).where(Project.status == "active")
        )
        projects = result.scalars().all()
        
        from app.services.email_service import email_service
        
        for project in projects:
            # Get last completed run
            run_result = await db.execute(
                select(Run)
                .where(
                    and_(
                        Run.project_id == project.id,
                        Run.status == "completed",
                    )
                )
                .order_by(Run.completed_at.desc())
                .limit(1)
            )
            last_run = run_result.scalar_one_or_none()
            
            if not last_run or not last_run.completed_at:
                continue
            
            if last_run.completed_at > two_weeks_ago:
                continue  # Recent run exists
            
            days_since_test = (datetime.now(timezone.utc) - last_run.completed_at).days
            
            # Get workspace admins
            members_result = await db.execute(
                select(User)
                .join(Membership, Membership.user_id == User.id)
                .where(
                    and_(
                        Membership.workspace_id == project.workspace_id,
                        Membership.role.in_(["admin", "analyst"]),
                    )
                )
            )
            users = members_result.scalars().all()
            
            for user in users:
                try:
                    await email_service.send_retest_reminder_email(
                        to_email=user.email,
                        user_name=user.full_name,
                        project_name=project.name,
                        days_until_retest=0,
                        last_test_date=last_run.completed_at.strftime("%Y-%m-%d"),
                    )
                except Exception as e:
                    logger.error(f"Failed to send retest reminder: {e}")


@celery_app.task(name="app.tasks.cleanup.cleanup_old_results")
def cleanup_old_results():
    """Clean up old crawl results and temporary data."""
    import asyncio
    asyncio.run(_cleanup_old_results_async())


async def _cleanup_old_results_async():
    """Async cleanup implementation."""
    async with get_session() as db:
        from sqlalchemy import select, and_, delete
        from app.models.audit import AuditLog
        
        # Delete events older than 90 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        
        await db.execute(
            delete(AuditLog).where(
                and_(
                    AuditLog.resource_type == "event",
                    AuditLog.created_at < cutoff,
                )
            )
        )
        
        await db.commit()
        logger.info("Cleaned up old audit events")
