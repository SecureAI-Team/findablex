"""Celery application configuration."""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Create Celery app
celery_app = Celery(
    "findablex",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.ingest",
        "app.tasks.extract",
        "app.tasks.score",
        "app.tasks.report",
        "app.tasks.crawl",
        "app.tasks.scheduled",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
    
    # Rate limiting
    worker_prefetch_multiplier=1,
    task_annotations={
        "app.tasks.crawl.*": {"rate_limit": "10/m"},
    },
    
    # Result settings
    result_expires=3600,
    
    # Worker settings
    worker_max_tasks_per_child=100,
    worker_disable_rate_limits=False,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Daily drift detection at 2 AM UTC
    "check-drift-daily": {
        "task": "app.tasks.scheduled.check_drift_all",
        "schedule": crontab(hour=2, minute=0),
    },
    # Cleanup old data at 3 AM UTC
    "cleanup-old-results": {
        "task": "app.tasks.scheduled.cleanup_old_results",
        "schedule": crontab(hour=3, minute=0),
    },
    # Auto-checkup for projects at 4 AM UTC (daily)
    "auto-checkup-projects": {
        "task": "app.tasks.scheduled.auto_checkup_projects",
        "schedule": crontab(hour=4, minute=0),
    },
    # Reset monthly usage on the 1st of each month at midnight UTC
    "reset-monthly-usage": {
        "task": "app.tasks.scheduled.reset_monthly_usage",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),
    },
    # Check subscription expiry daily at 8 AM UTC
    "check-subscription-expiry": {
        "task": "app.tasks.scheduled.check_subscription_expiry",
        "schedule": crontab(hour=8, minute=0),
    },
    # Send retest reminders weekly on Monday at 9 AM UTC
    "send-retest-reminders": {
        "task": "app.tasks.scheduled.send_retest_reminders",
        "schedule": crontab(day_of_week=1, hour=9, minute=0),
    },
}

# Task routes
celery_app.conf.task_routes = {
    "app.tasks.crawl.*": {"queue": "crawler"},
    "app.tasks.report.*": {"queue": "reports"},
    "app.tasks.*": {"queue": "default"},
}
