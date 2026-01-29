"""Database session helper for worker tasks."""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings

# Determine database URL
db_url = settings.effective_database_url
is_sqlite = "sqlite" in db_url

# Ensure data directory exists for SQLite
if is_sqlite:
    os.makedirs("data", exist_ok=True)

# Create async engine with appropriate configuration
if is_sqlite:
    engine = create_async_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Sync engine for non-async tasks (convert aiosqlite URL to sqlite)
    sync_db_url = db_url.replace("sqlite+aiosqlite", "sqlite")
    sync_engine = create_engine(
        sync_db_url,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    # Sync engine for non-async tasks (convert asyncpg URL to psycopg2)
    sync_db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    sync_engine = create_engine(
        sync_db_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=5,
    )

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session for worker tasks."""
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session (for dependency injection pattern)."""
    async with get_db_session() as session:
        yield session


# Import models to ensure they are registered with SQLAlchemy
from app.models import Base, Run, Project, QueryItem, Citation, Metric, Report
