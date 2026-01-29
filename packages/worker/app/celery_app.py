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
    "check-drift-daily": {
        "task": "app.tasks.score.detect_drift_all",
        "schedule": crontab(hour=2, minute=0),
    },
    "cleanup-old-results": {
        "task": "app.tasks.cleanup.cleanup_old_results",
        "schedule": crontab(hour=3, minute=0),
    },
}

# Task routes
celery_app.conf.task_routes = {
    "app.tasks.crawl.*": {"queue": "crawler"},
    "app.tasks.report.*": {"queue": "reports"},
    "app.tasks.*": {"queue": "default"},
}
