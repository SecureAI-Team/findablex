"""Settings service with Redis caching and encryption for secrets."""
import hashlib
import json
from base64 import b64decode, b64encode
from typing import Any, Dict, List, Optional
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.models.settings import DEFAULT_SETTINGS, SystemSetting, SystemSettingAudit


class SettingsService:
    """Service for managing system settings with caching and encryption."""
    
    CACHE_PREFIX = "settings:"
    CACHE_TTL = 60  # seconds
    ALL_SETTINGS_KEY = "settings:all"
    
    def __init__(self, db: AsyncSession, redis_client: Optional[Any] = None):
        self.db = db
        self.redis = redis_client
        self._fernet = self._init_fernet()
    
    def _init_fernet(self) -> Fernet:
        """Initialize Fernet encryption using derived key from SECRET_KEY."""
        # Derive a 32-byte key from SECRET_KEY using SHA256
        key_bytes = hashlib.sha256(app_settings.secret_key.encode()).digest()
        fernet_key = b64encode(key_bytes)
        return Fernet(fernet_key)
    
    def _encrypt_value(self, value: Any) -> str:
        """Encrypt a value for secret storage."""
        if value is None:
            return None
        json_str = json.dumps(value)
        encrypted = self._fernet.encrypt(json_str.encode())
        return b64encode(encrypted).decode()
    
    def _decrypt_value(self, encrypted_value: str) -> Any:
        """Decrypt a secret value."""
        if encrypted_value is None:
            return None
        try:
            encrypted_bytes = b64decode(encrypted_value.encode())
            decrypted = self._fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception:
            # If decryption fails, return as-is (might be plain value)
            return encrypted_value
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        if not self.redis:
            return None
        try:
            cached = await self.redis.get(f"{self.CACHE_PREFIX}{key}")
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        return None
    
    async def _set_cache(self, key: str, value: Any, ttl: int = None):
        """Set value in Redis cache."""
        if not self.redis:
            return
        try:
            await self.redis.setex(
                f"{self.CACHE_PREFIX}{key}",
                ttl or self.CACHE_TTL,
                json.dumps(value),
            )
        except Exception:
            pass
    
    async def _invalidate_cache(self, key: str = None):
        """Invalidate cache for a key or all settings."""
        if not self.redis:
            return
        try:
            if key:
                await self.redis.delete(f"{self.CACHE_PREFIX}{key}")
            await self.redis.delete(self.ALL_SETTINGS_KEY)
        except Exception:
            pass
    
    async def get_setting(
        self,
        key: str,
        decrypt_secrets: bool = True,
    ) -> Optional[SystemSetting]:
        """Get a single setting by key."""
        # Try cache first
        cached = await self._get_from_cache(key)
        if cached:
            # Create a mock object for cached data
            setting = SystemSetting(**cached)
            if setting.is_secret and decrypt_secrets and setting.value:
                setting.value = self._decrypt_value(setting.value)
            return setting
        
        # Query database
        result = await self.db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            # Cache the result (with encrypted value for secrets)
            cache_data = {
                "id": str(setting.id),
                "key": setting.key,
                "category": setting.category,
                "value": setting.value,
                "value_type": setting.value_type,
                "is_secret": setting.is_secret,
                "description": setting.description,
            }
            await self._set_cache(key, cache_data)
            
            # Decrypt if needed
            if setting.is_secret and decrypt_secrets and setting.value:
                setting.value = self._decrypt_value(setting.value)
        
        return setting
    
    async def get_setting_value(
        self,
        key: str,
        default: Any = None,
        decrypt_secrets: bool = True,
    ) -> Any:
        """Get just the value of a setting."""
        setting = await self.get_setting(key, decrypt_secrets)
        if setting is None:
            return default
        return setting.value if setting.value is not None else default
    
    async def get_settings_by_category(
        self,
        category: str,
        mask_secrets: bool = True,
    ) -> List[SystemSetting]:
        """Get all settings in a category."""
        result = await self.db.execute(
            select(SystemSetting)
            .where(SystemSetting.category == category)
            .order_by(SystemSetting.key)
        )
        settings = result.scalars().all()
        
        if mask_secrets:
            for setting in settings:
                if setting.is_secret and setting.value:
                    setting.value = "******"
        
        return list(settings)
    
    async def get_all_settings(
        self,
        mask_secrets: bool = True,
    ) -> Dict[str, List[SystemSetting]]:
        """Get all settings grouped by category."""
        result = await self.db.execute(
            select(SystemSetting).order_by(SystemSetting.category, SystemSetting.key)
        )
        settings = result.scalars().all()
        
        grouped: Dict[str, List[SystemSetting]] = {}
        for setting in settings:
            if mask_secrets and setting.is_secret and setting.value:
                setting.value = "******"
            
            if setting.category not in grouped:
                grouped[setting.category] = []
            grouped[setting.category].append(setting)
        
        return grouped
    
    async def set_setting(
        self,
        key: str,
        value: Any,
        user_id: UUID = None,
    ) -> SystemSetting:
        """Set a setting value with audit logging."""
        # Get existing setting
        result = await self.db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            raise ValueError(f"Setting '{key}' not found")
        
        # Store old value for audit (don't decrypt secrets in audit log)
        old_value = setting.value
        
        # Encrypt if secret
        if setting.is_secret and value is not None:
            new_value = self._encrypt_value(value)
        else:
            new_value = value
        
        # Update setting
        setting.value = new_value
        setting.updated_by = user_id
        
        # Create audit log
        audit = SystemSettingAudit(
            setting_id=setting.id,
            key=key,
            old_value="[REDACTED]" if setting.is_secret else old_value,
            new_value="[REDACTED]" if setting.is_secret else new_value,
            changed_by=user_id,
        )
        self.db.add(audit)
        
        await self.db.commit()
        await self.db.refresh(setting)
        
        # Invalidate cache
        await self._invalidate_cache(key)
        
        return setting
    
    async def bulk_update_settings(
        self,
        updates: List[Dict[str, Any]],
        user_id: UUID = None,
    ) -> List[Dict[str, Any]]:
        """Bulk update multiple settings."""
        results = []
        
        for update in updates:
            key = update.get("key")
            value = update.get("value")
            
            try:
                await self.set_setting(key, value, user_id)
                results.append({"key": key, "success": True, "error": None})
            except Exception as e:
                results.append({"key": key, "success": False, "error": str(e)})
        
        return results
    
    async def get_audit_log(
        self,
        key: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SystemSettingAudit]:
        """Get audit log for settings changes."""
        query = select(SystemSettingAudit).order_by(
            SystemSettingAudit.changed_at.desc()
        )
        
        if key:
            query = query.where(SystemSettingAudit.key == key)
        
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def initialize_default_settings(self):
        """Initialize default settings if they don't exist."""
        for setting_data in DEFAULT_SETTINGS:
            # Check if setting exists
            result = await self.db.execute(
                select(SystemSetting).where(
                    SystemSetting.key == setting_data["key"]
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                # Encrypt secret values
                value = setting_data["value"]
                if setting_data.get("is_secret") and value is not None:
                    value = self._encrypt_value(value)
                
                setting = SystemSetting(
                    key=setting_data["key"],
                    category=setting_data["category"],
                    value=value,
                    value_type=setting_data["value_type"],
                    is_secret=setting_data.get("is_secret", False),
                    description=setting_data.get("description"),
                )
                self.db.add(setting)
        
        await self.db.commit()


# Global settings cache for synchronous access
class DynamicSettings:
    """
    Dynamic settings accessor that combines static (.env) and dynamic (DB) settings.
    
    Usage:
        from app.services.settings_service import dynamic_settings
        
        # Get dynamic setting (with fallback to default)
        api_key = await dynamic_settings.get("ai.qwen_api_key")
        
        # Or for sync access (uses cached values)
        api_key = dynamic_settings.get_cached("ai.qwen_api_key", default="")
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self, db: AsyncSession, redis_client: Any = None):
        """Initialize cache from database."""
        service = SettingsService(db, redis_client)
        all_settings = await service.get_all_settings(mask_secrets=False)
        
        for category_settings in all_settings.values():
            for setting in category_settings:
                value = setting.value
                if setting.is_secret and value and value != "******":
                    value = service._decrypt_value(value)
                self._cache[setting.key] = value
        
        self._initialized = True
    
    def get_cached(self, key: str, default: Any = None) -> Any:
        """Get a cached setting value (synchronous)."""
        return self._cache.get(key, default)
    
    def set_cached(self, key: str, value: Any):
        """Update a cached setting value."""
        self._cache[key] = value
    
    def invalidate(self, key: str = None):
        """Invalidate cache."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
            self._initialized = False


# Global instance
dynamic_settings = DynamicSettings()
