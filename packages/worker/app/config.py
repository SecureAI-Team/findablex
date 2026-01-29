"""Worker configuration."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Worker settings.
    
    Static settings from .env. For dynamic settings (AI keys, etc.),
    query the API's system_settings table via Redis or direct DB access.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Lite mode: Use SQLite + sync execution (no Docker needed)
    lite_mode: bool = True
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/findablex.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    
    # Environment
    env: str = "development"
    
    # Secret key for decrypting settings
    secret_key: str = "change-me-in-production"
    
    @property
    def effective_database_url(self) -> str:
        """Get effective database URL based on mode."""
        if self.lite_mode and "postgresql" in self.database_url:
            return "sqlite+aiosqlite:///./data/findablex.db"
        return self.database_url


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
import redis


class WorkerDynamicSettings:
    """
    Access dynamic settings from Redis/PostgreSQL.
    
    This is a synchronous version for Celery workers.
    """
    
    CACHE_PREFIX = "settings:"
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._fernet = self._init_fernet()
        self._local_cache: dict = {}
    
    def _init_fernet(self) -> Fernet:
        """Initialize Fernet encryption using derived key from SECRET_KEY."""
        key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
        fernet_key = b64encode(key_bytes)
        return Fernet(fernet_key)
    
    def _get_redis(self) -> redis.Redis:
        """Get Redis client."""
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url)
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
    
    def get(self, key: str, default=None, decrypt: bool = True):
        """
        Get a dynamic setting value.
        
        Tries Redis cache first, falls back to local cache.
        """
        try:
            r = self._get_redis()
            cached = r.get(f"{self.CACHE_PREFIX}{key}")
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
    
    def get_ai_config(self) -> dict:
        """Get AI configuration settings."""
        return {
            "qwen_api_key": self.get("ai.qwen_api_key"),
            "qwen_model": self.get("ai.qwen_model", "qwen-max"),
            "openai_api_key": self.get("ai.openai_api_key"),
            "openai_model": self.get("ai.openai_model", "gpt-4-turbo"),
            "user_can_provide_key": self.get("ai.user_can_provide_key", True),
        }
    
    def get_limits_config(self) -> dict:
        """Get limits configuration settings."""
        return {
            "max_upload_size_mb": self.get("limits.max_upload_size_mb", 10),
            "rate_limit_per_minute": self.get("limits.rate_limit_per_minute", 100),
            "free_projects_limit": self.get("limits.free_projects_limit", 3),
            "free_runs_per_month": self.get("limits.free_runs_per_month", 10),
        }


# Global instance for workers
worker_dynamic_settings = WorkerDynamicSettings()
