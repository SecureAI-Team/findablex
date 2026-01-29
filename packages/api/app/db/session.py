"""Database session management."""
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool

from app.config import settings

# Determine database URL
db_url = settings.effective_database_url

# SQLite specific configuration
is_sqlite = "sqlite" in db_url

# Ensure data directory exists for SQLite
if is_sqlite:
    os.makedirs("data", exist_ok=True)

# Create async engine with appropriate configuration
if is_sqlite:
    # SQLite doesn't support connection pooling in the same way
    engine = create_async_engine(
        db_url,
        echo=settings.debug,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL configuration
    engine = create_async_engine(
        db_url,
        echo=settings.debug,
        future=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_async_session() -> AsyncSession:
    """Get an async database session."""
    async with async_session_maker() as session:
        yield session


async def init_db():
    """Initialize database tables (for SQLite/development)."""
    if is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
