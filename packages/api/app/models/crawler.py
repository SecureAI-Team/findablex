"""CrawlTask, CrawlResult, and CrawlerCredential models."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON as JSONB  # Use JSON for SQLite compatibility
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.workspace import Workspace


class CrawlTask(Base):
    """CrawlTask model for web crawling tasks."""
    
    __tablename__ = "crawl_tasks"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    
    # Task configuration
    engine: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    queries: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    
    # Crawl parameters
    region: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    language: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    device_type: Mapped[str] = mapped_column(
        String(20),
        default="desktop",
        nullable=False,
    )
    use_proxy: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Status management
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    
    # Timing
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Results
    total_queries: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    successful_queries: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_queries: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_log: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    results: Mapped[list["CrawlResult"]] = relationship(
        "CrawlResult",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<CrawlTask {self.engine} status={self.status}>"


class CrawlResult(Base):
    """CrawlResult model for storing crawl results."""
    
    __tablename__ = "crawl_results"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawl_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("query_items.id"),
        nullable=False,
    )
    
    # Result data
    engine: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    raw_html: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    parsed_response: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    citations: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
    )
    
    # Metadata
    response_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    screenshot_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Quality markers
    is_complete: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    has_citations: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    
    # Source tracking
    source: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        default="server",
        comment="Result source: server, agent, browser_extension",
    )
    
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Relationships
    task: Mapped["CrawlTask"] = relationship(
        "CrawlTask",
        back_populates="results",
    )
    
    def __repr__(self) -> str:
        return f"<CrawlResult {self.engine}>"


class CrawlerCredential(Base):
    """
    CrawlerCredential model for storing encrypted credentials.
    
    Stores API keys, cookies, and session tokens for engines requiring authentication.
    Values are encrypted using Fernet symmetric encryption.
    """
    
    __tablename__ = "crawler_credentials"
    
    # Unique constraint on workspace + engine + credential_type
    __table_args__ = (
        UniqueConstraint('workspace_id', 'engine', 'credential_type', name='uq_workspace_engine_cred_type'),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Credential identification
    engine: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="Engine name (perplexity, chatgpt, qwen, etc.)",
    )
    credential_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Type: api_key, cookie, session, oauth_token",
    )
    
    # Encrypted value (using Fernet)
    encrypted_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Fernet-encrypted credential value",
    )
    
    # Optional metadata
    account_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Account identifier for multiple accounts per engine",
    )
    label: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Human-readable label (e.g., 'Production API Key')",
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Last error message if credential failed",
    )
    
    # Expiration (for tokens that expire)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Audit
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    def __repr__(self) -> str:
        return f"<CrawlerCredential {self.engine}/{self.credential_type}>"
    
    @property
    def is_expired(self) -> bool:
        """Check if credential is expired."""
        if self.expires_at is None:
            return False
        from datetime import timezone as tz
        return datetime.now(tz.utc) > self.expires_at
