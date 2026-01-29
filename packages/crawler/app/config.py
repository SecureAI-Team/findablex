"""Crawler configuration."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Crawler settings.
    
    Static settings from .env. For dynamic settings (rate limits, etc.),
    query the system_settings via Redis.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Database
    database_url: str = "postgresql+asyncpg://findablex:devpassword@localhost:5432/findablex"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Browser settings (static)
    headless: bool = True
    browser_timeout: int = 30000
    
    # Human behavior simulation (static)
    typing_speed_min: int = 80
    typing_speed_max: int = 150
    session_duration_min: int = 5
    session_duration_max: int = 30
    
    # Data storage (static, server paths)
    data_dir: str = "/app/data"
    screenshot_dir: str = "/app/screenshots"
    
    # Session storage
    session_storage_path: str = "data/sessions"
    session_ttl_hours: int = 24
    
    # Anti-detection settings
    rotate_user_agent: bool = True
    rotate_proxy: bool = True
    stealth_level: str = "high"  # low, medium, high
    
    # CAPTCHA handling
    captcha_solver: str = "manual"  # manual, wait_and_retry, 2captcha
    captcha_api_key: str = ""  # API key for third-party solvers
    captcha_max_wait: int = 300  # Max seconds to wait for manual solve
    
    # Proxy settings
    proxy_pool_url: Optional[str] = None  # URL to fetch proxy list
    
    # Rate limiting
    crawler_rate_limit: float = 0.2  # Requests per second (default: 1 every 5 seconds)
    
    # Secret key for decrypting settings
    secret_key: str = "change-me-in-production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings."""
    return Settings()


settings = get_settings()


# =============================================================================
# Dynamic Settings Access
# =============================================================================

import hashlib
import json
from base64 import b64decode, b64encode
from cryptography.fernet import Fernet
import redis.asyncio as aioredis


class CrawlerDynamicSettings:
    """
    Access dynamic settings from Redis for the crawler.
    
    This is an async version for the crawler service.
    """
    
    CACHE_PREFIX = "settings:"
    
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._fernet = self._init_fernet()
        self._local_cache: dict = {}
    
    def _init_fernet(self) -> Fernet:
        """Initialize Fernet encryption using derived key from SECRET_KEY."""
        key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
        fernet_key = b64encode(key_bytes)
        return Fernet(fernet_key)
    
    async def _get_redis(self) -> aioredis.Redis:
        """Get Redis client."""
        if self._redis is None:
            self._redis = aioredis.from_url(settings.redis_url)
        return self._redis
    
    def _decrypt_value(self, encrypted_value: str):
        """Decrypt a secret value."""
        if encrypted_value is None:
            return None
        try:
            encrypted_bytes = b64decode(encrypted_value.encode())
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception:
            return encrypted_value
    
    async def get(self, key: str, default=None, decrypt: bool = True):
        """
        Get a dynamic setting value.
        """
        try:
            r = await self._get_redis()
            cached = await r.get(f"{self.CACHE_PREFIX}{key}")
            if cached:
                data = json.loads(cached)
                value = data.get("value")
                is_secret = data.get("is_secret", False)
                
                if is_secret and decrypt and value:
                    value = self._decrypt_value(value)
                
                return value if value is not None else default
        except Exception:
            pass
        
        return self._local_cache.get(key, default)
    
    async def get_crawler_config(self) -> dict:
        """Get crawler configuration settings."""
        return {
            "enabled": await self.get("crawler.enabled", False),
            "rate_limit": await self.get("crawler.rate_limit", 0.2),
            "daily_limit": await self.get("crawler.daily_limit", 500),
            "proxy_pool_url": await self.get("crawler.proxy_pool_url"),
        }
    
    async def is_enabled(self) -> bool:
        """Check if crawler is enabled."""
        return await self.get("crawler.enabled", False)
    
    async def get_rate_limit(self) -> float:
        """Get crawler rate limit (requests per second)."""
        return await self.get("crawler.rate_limit", 0.2)
    
    async def get_daily_limit(self) -> int:
        """Get daily query limit."""
        return await self.get("crawler.daily_limit", 500)
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Global instance for crawler
crawler_dynamic_settings = CrawlerDynamicSettings()
