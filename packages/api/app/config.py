"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    These are STATIC settings that are loaded at startup and cannot be changed
    without restarting the application. For dynamic settings that can be
    changed at runtime, use the SettingsService.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # ==========================================================================
    # STATIC SETTINGS (from .env, cannot change at runtime)
    # ==========================================================================
    
    # Application
    app_name: str = "FindableX"
    env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    
    # Lite mode: Use SQLite + in-memory queue (no Docker needed)
    lite_mode: bool = True
    
    # Database (lite_mode uses SQLite by default)
    database_url: str = "sqlite+aiosqlite:///./data/findablex.db"
    
    # Redis (not used in lite_mode)
    redis_url: str = "redis://localhost:6379/0"
    
    @property
    def effective_database_url(self) -> str:
        """Get effective database URL based on mode."""
        if self.lite_mode and "postgresql" in self.database_url:
            return "sqlite+aiosqlite:///./data/findablex.db"
        return self.database_url
    
    # JWT Authentication (secret must be static for token validation)
    jwt_secret: str = "jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours
    jwt_refresh_expire_days: int = 7
    
    # Registration settings
    invite_code_required: bool = False  # Set to True to require invite codes for registration
    
    # CORS (tied to deployment domain)
    allowed_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:8000"
    
    # Storage paths (server filesystem)
    upload_dir: str = "/app/uploads"
    data_dir: str = "/app/data"
    screenshot_dir: str = "./data/screenshots"
    
    # Crawler settings
    headless: bool = True  # Set to False to see browser (for debugging)
    crawler_rate_limit: float = 0.2  # Requests per second
    
    # Crawler Agent settings (for remote browser agents)
    crawler_agent_enabled: bool = False  # Enable remote browser agent feature
    crawler_agent_token: str = ""  # Token for agent authentication
    
    # CAPTCHA/Challenge handling settings
    captcha_strategy: str = "smart"  # manual, auto_wait, api, smart
    twocaptcha_api_key: str = ""  # 2Captcha API key (for API strategy)
    captcha_manual_timeout: int = 300  # Manual solve timeout in seconds
    captcha_auto_wait_timeout: int = 30  # Auto-wait timeout for JS challenges
    
    # Session persistence settings
    session_dir: str = "./data/sessions"  # Directory to store session files
    session_ttl_hours: int = 24  # Session validity period in hours
    
    # Browser profile settings
    browser_profile_dir: str = "./data/browser_profiles"  # Persistent browser profiles
    use_persistent_context: bool = False  # Use persistent browser context
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()


# =============================================================================
# DYNAMIC SETTINGS HELPER
# =============================================================================

class DynamicSettingsHelper:
    """
    Helper class to access dynamic settings from database.
    
    For settings that can be changed at runtime by platform administrators,
    use this helper instead of the static Settings class.
    
    Usage:
        from app.config import dynamic
        
        # Async access (preferred, always fresh)
        api_key = await dynamic.get("ai.qwen_api_key")
        
        # Sync access (uses cached value, might be stale)
        api_key = dynamic.cached("ai.qwen_api_key", default="")
    
    Available dynamic settings:
    
    Platform:
        - platform.name: str - Platform display name
        - platform.logo_url: str - Logo URL
        - platform.support_email: str - Support email
    
    Auth:
        - auth.registration_enabled: bool - Allow new registrations
        - auth.invite_code_required: bool - Require invite code
        - auth.default_invite_code: str - Default invite code
        - auth.jwt_expire_minutes: int - JWT expiration time
    
    AI:
        - ai.qwen_api_key: str - Qwen API key
        - ai.qwen_model: str - Qwen model name
        - ai.openai_api_key: str - OpenAI API key
        - ai.openai_model: str - OpenAI model name
        - ai.user_can_provide_key: bool - Allow user-provided keys
    
    Crawler:
        - crawler.enabled: bool - Enable crawler
        - crawler.rate_limit: float - Requests per second
        - crawler.daily_limit: int - Daily request limit
        - crawler.proxy_pool_url: str - Proxy pool URL
    
    Limits:
        - limits.max_upload_size_mb: int - Max upload size in MB
        - limits.rate_limit_per_minute: int - API rate limit
        - limits.free_projects_limit: int - Free tier project limit
        - limits.free_runs_per_month: int - Free tier monthly runs
    
    Email:
        - email.smtp_host: str - SMTP server
        - email.smtp_port: int - SMTP port
        - email.smtp_user: str - SMTP username
        - email.smtp_password: str - SMTP password
        - email.from_address: str - From address
    
    Features:
        - features.research_mode: bool - Enable research mode
        - features.crawler_for_researchers: bool - Crawler for researchers
        - features.export_enabled: bool - Enable data export
    """
    
    _cache: dict = {}
    _initialized: bool = False
    
    async def get(self, key: str, default=None):
        """
        Get a dynamic setting value (async, always fresh from DB/cache).
        
        This method queries the database or Redis cache for the current value.
        Use this when you need the most up-to-date value.
        """
        from app.services.settings_service import dynamic_settings
        
        if not dynamic_settings._initialized:
            return default
        
        value = dynamic_settings.get_cached(key)
        return value if value is not None else default
    
    def cached(self, key: str, default=None):
        """
        Get a cached dynamic setting value (sync, might be stale).
        
        This method returns a cached value without querying the database.
        Use this for performance when slight staleness is acceptable.
        """
        from app.services.settings_service import dynamic_settings
        return dynamic_settings.get_cached(key, default)
    
    async def refresh(self, db_session=None, redis_client=None):
        """
        Refresh all dynamic settings from database.
        
        Call this after bulk updates or when cache might be stale.
        """
        from app.services.settings_service import dynamic_settings
        
        if db_session:
            await dynamic_settings.initialize(db_session, redis_client)


# Global dynamic settings accessor
dynamic = DynamicSettingsHelper()
