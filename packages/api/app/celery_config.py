"""Celery configuration for the API."""
import os

# Broker settings
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Task settings
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True

# Task routing
task_routes = {
    "app.tasks.ingest.*": {"queue": "ingest"},
    "app.tasks.extract.*": {"queue": "extract"},
    "app.tasks.score.*": {"queue": "score"},
    "app.tasks.report.*": {"queue": "report"},
    "app.tasks.crawl.*": {"queue": "crawl"},
}

# Task result expiration (24 hours)
result_expires = 86400

# Retry settings
task_acks_late = True
task_reject_on_worker_lost = True
