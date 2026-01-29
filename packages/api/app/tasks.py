"""
Celery task dispatchers for the API.

This module provides functions to dispatch tasks to the Celery worker.
In lite_mode, tasks are executed synchronously without Celery/Redis.
"""
from app.config import settings

if settings.lite_mode:
    # Use lite queue for local development
    from app.db.lite_queue import get_lite_celery
    celery_app = get_lite_celery()
else:
    # Use real Celery for production
    from celery import Celery
    celery_app = Celery(
        "findablex",
        broker=settings.celery_broker_url,
        backend=settings.redis_url,
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )


# Task signatures for dispatching to worker
# These don't execute the task, they just send a message to the worker

process_crawl_task = celery_app.signature("app.tasks.crawl.process_crawl_task")
consume_crawl_results = celery_app.signature("app.tasks.crawl.consume_crawl_results")
save_crawl_results_to_db = celery_app.signature("app.tasks.crawl.save_crawl_results_to_db")

parse_import = celery_app.signature("app.tasks.ingest.parse_import")
process_run = celery_app.signature("app.tasks.ingest.process_run")

extract_citations = celery_app.signature("app.tasks.extract.extract_citations")

calculate_metrics = celery_app.signature("app.tasks.score.calculate_metrics")

generate_report = celery_app.signature("app.tasks.report.generate_report")
