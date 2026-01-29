"""FastAPI application entry point."""
import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import router as api_v1_router
from app.config import settings
from app.core.rate_limiter import limiter
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    from app.db.session import async_session_maker, init_db, is_sqlite
    from app.services.settings_service import dynamic_settings
    
    # Initialize database tables for SQLite (lite mode)
    if is_sqlite:
        print(f"[Lite Mode] Using SQLite database")
        await init_db()
        print("[Lite Mode] Database tables created")
    
    # Initialize dynamic settings cache
    try:
        if settings.lite_mode:
            from app.db.lite_queue import get_lite_redis
            redis_client = get_lite_redis()
        else:
            from app.deps import get_redis
            redis_client = await get_redis()
        
        async with async_session_maker() as db:
            await dynamic_settings.initialize(db, redis_client)
            print("Dynamic settings initialized")
    except Exception as e:
        print(f"Warning: Could not initialize dynamic settings: {e}")
    
    yield
    
    # Shutdown
    if not settings.lite_mode:
        from app.deps import close_redis
        await close_redis()
    await engine.dispose()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="GEO 体检型 SaaS + 科研实验平台 API",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )
    
    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Global exception handler for debugging
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_traceback = traceback.format_exc()
        print(f"=== EXCEPTION ===\n{error_traceback}\n=================")
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "traceback": error_traceback if settings.debug else None}
        )
    
    # CORS middleware - must be added BEFORE other middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods including OPTIONS
        allow_headers=["*"],  # Allow all headers
    )
    
    # Include routers
    app.include_router(api_v1_router, prefix="/api/v1")
    
    return app


app = create_application()


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "env": settings.env,
    }


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
