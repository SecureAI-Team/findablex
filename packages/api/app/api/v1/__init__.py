"""API v1 routes."""
from fastapi import APIRouter

from app.api.v1 import auth, projects, runs, reports, workspaces, admin, crawler, settings, invite_codes, calibration, subscriptions, analytics, drift_events, credentials, auto_checkup, payment, notifications, collaboration, webhooks

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
router.include_router(projects.router, prefix="/projects", tags=["Projects"])
router.include_router(auto_checkup.router, prefix="/projects", tags=["Auto Checkup"])
router.include_router(runs.router, prefix="/runs", tags=["Runs"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])
router.include_router(crawler.router, prefix="/crawler", tags=["Crawler"])
router.include_router(admin.router, prefix="/admin", tags=["Admin"])
router.include_router(settings.router, tags=["Admin Settings"])
router.include_router(invite_codes.router, prefix="/invite-codes", tags=["Invite Codes"])
router.include_router(calibration.router, prefix="/calibration", tags=["Calibration"])
router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
router.include_router(drift_events.router, prefix="/projects", tags=["Drift Events"])
router.include_router(credentials.router, tags=["Credentials"])
router.include_router(payment.router, prefix="/payment", tags=["Payment"])
router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
router.include_router(collaboration.router, prefix="/projects", tags=["Collaboration"])
router.include_router(webhooks.router, tags=["Webhooks"])