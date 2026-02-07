"""Database base - import all models here for Alembic."""
from app.db.session import Base  # noqa: F401

# Import all models so Alembic can detect them
from app.models.user import User  # noqa: F401
from app.models.workspace import Workspace, Membership, Tenant  # noqa: F401
from app.models.project import Project, QueryItem  # noqa: F401
from app.models.run import Run, Citation, Metric  # noqa: F401
from app.models.report import Report, ShareLink  # noqa: F401
from app.models.experiment import Variant, ExperimentRun, DriftEvent  # noqa: F401
from app.models.audit import AuditLog, Consent  # noqa: F401
from app.models.crawler import CrawlTask, CrawlResult  # noqa: F401
from app.models.collaboration import Comment, ActivityEvent  # noqa: F401
from app.models.webhook import Webhook, WebhookDelivery  # noqa: F401
