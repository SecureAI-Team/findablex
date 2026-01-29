"""Shared model enums and types."""
from enum import Enum


class QueryIntent(str, Enum):
    """Query intent classification."""
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    TRANSACTIONAL = "transactional"
    COMMERCIAL = "commercial"
    LOCAL = "local"


class MetricType(str, Enum):
    """Metric type enum."""
    VISIBILITY_RATE = "visibility_rate"
    AVG_CITATION_POSITION = "avg_citation_position"
    CITATION_COUNT = "citation_count"
    TOP3_RATE = "top3_rate"
    COMPETITOR_SHARE = "competitor_share"
    HEALTH_SCORE = "health_score"


class RunStatus(str, Enum):
    """Run status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunType(str, Enum):
    """Run type enum."""
    CHECKUP = "checkup"
    RETEST = "retest"
    EXPERIMENT = "experiment"


class Role(str, Enum):
    """User role enum."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class DriftType(str, Enum):
    """Drift event type."""
    POSITION_DROP = "position_drop"
    VISIBILITY_LOSS = "visibility_loss"
    NEW_COMPETITOR = "new_competitor"


class DriftSeverity(str, Enum):
    """Drift event severity."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
