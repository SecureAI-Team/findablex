"""
User credential service for managing user-level API keys.

Provides secure storage and retrieval of user's own API keys.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from cryptography.fernet import InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserCredential
from app.services.credential_service import get_encryption

logger = logging.getLogger(__name__)


class UserCredentialService:
    """Service for managing user-level API credentials."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.encryption = get_encryption()
    
    async def create(
        self,
        user_id: UUID,
        engine: str,
        value: str,
        label: Optional[str] = None,
    ) -> UserCredential:
        """
        Create a new user credential.
        
        Args:
            user_id: User ID
            engine: Engine name (deepseek, qwen, kimi, perplexity, chatgpt)
            value: API key value (will be encrypted)
            label: Optional human-readable label
        
        Returns:
            Created credential
        """
        # Encrypt the value
        encrypted_value = self.encryption.encrypt(value)
        
        credential = UserCredential(
            user_id=user_id,
            engine=engine.lower(),
            credential_type="api_key",
            encrypted_value=encrypted_value,
            label=label,
        )
        
        self.db.add(credential)
        await self.db.commit()
        await self.db.refresh(credential)
        
        logger.info(f"Created user credential for {engine} for user {user_id}")
        return credential
    
    async def get_by_id(self, credential_id: UUID) -> Optional[UserCredential]:
        """Get credential by ID."""
        result = await self.db.execute(
            select(UserCredential).where(UserCredential.id == credential_id)
        )
        return result.scalar_one_or_none()
    
    async def get_for_user(
        self,
        user_id: UUID,
        engine: Optional[str] = None,
        active_only: bool = True,
    ) -> List[UserCredential]:
        """
        Get credentials for a user.
        
        Args:
            user_id: User ID
            engine: Optional engine filter
            active_only: Only return active credentials
        
        Returns:
            List of matching credentials
        """
        query = select(UserCredential).where(
            UserCredential.user_id == user_id,
        )
        
        if engine:
            query = query.where(UserCredential.engine == engine.lower())
        
        if active_only:
            query = query.where(UserCredential.is_active == True)
        
        query = query.order_by(UserCredential.engine, UserCredential.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_active(
        self,
        user_id: UUID,
        engine: str,
    ) -> Optional[str]:
        """
        Get active decrypted API key for a user and engine.
        
        Args:
            user_id: User ID
            engine: Engine name
        
        Returns:
            Decrypted API key or None
        """
        credentials = await self.get_for_user(user_id, engine, active_only=True)
        
        for cred in credentials:
            try:
                return self.encryption.decrypt(cred.encrypted_value)
            except InvalidToken:
                logger.error(f"Failed to decrypt user credential {cred.id}")
                continue
        
        return None
    
    async def get_decrypted_value(
        self,
        credential_id: UUID,
    ) -> Optional[str]:
        """
        Get decrypted credential value.
        
        Args:
            credential_id: Credential ID
        
        Returns:
            Decrypted value, or None if not found
        """
        credential = await self.get_by_id(credential_id)
        if not credential:
            return None
        
        try:
            return self.encryption.decrypt(credential.encrypted_value)
        except InvalidToken:
            logger.error(f"Failed to decrypt user credential {credential_id}")
            return None
    
    async def update_value(
        self,
        credential_id: UUID,
        value: str,
    ) -> bool:
        """
        Update credential value.
        
        Args:
            credential_id: Credential ID
            value: New API key value (will be encrypted)
        
        Returns:
            True if updated
        """
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False
        
        credential.encrypted_value = self.encryption.encrypt(value)
        credential.last_error = None
        
        await self.db.commit()
        return True
    
    async def update_label(
        self,
        credential_id: UUID,
        label: str,
    ) -> bool:
        """Update credential label."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False
        
        credential.label = label
        await self.db.commit()
        return True
    
    async def mark_used(self, credential_id: UUID):
        """Mark credential as recently used."""
        credential = await self.get_by_id(credential_id)
        if credential:
            credential.last_used_at = datetime.now(timezone.utc)
            await self.db.commit()
    
    async def mark_failed(self, credential_id: UUID, error: str):
        """Mark credential as failed with error message."""
        credential = await self.get_by_id(credential_id)
        if credential:
            credential.last_error = error[:500]
            await self.db.commit()
    
    async def deactivate(self, credential_id: UUID) -> bool:
        """Deactivate a credential."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False
        
        credential.is_active = False
        await self.db.commit()
        return True
    
    async def activate(self, credential_id: UUID) -> bool:
        """Activate a credential."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False
        
        credential.is_active = True
        await self.db.commit()
        return True
    
    async def delete(self, credential_id: UUID) -> bool:
        """Delete a credential."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False
        
        await self.db.delete(credential)
        await self.db.commit()
        return True
    
    async def list_for_user(
        self,
        user_id: UUID,
        include_inactive: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List all credentials for a user (without decrypted values).
        
        Args:
            user_id: User ID
            include_inactive: Include inactive credentials
        
        Returns:
            List of credential info dicts
        """
        query = select(UserCredential).where(
            UserCredential.user_id == user_id
        )
        
        if not include_inactive:
            query = query.where(UserCredential.is_active == True)
        
        query = query.order_by(UserCredential.engine, UserCredential.created_at.desc())
        
        result = await self.db.execute(query)
        credentials = result.scalars().all()
        
        return [
            {
                "id": str(cred.id),
                "engine": cred.engine,
                "credential_type": cred.credential_type,
                "label": cred.label,
                "is_active": cred.is_active,
                "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None,
                "last_error": cred.last_error,
                "created_at": cred.created_at.isoformat(),
                "updated_at": cred.updated_at.isoformat(),
            }
            for cred in credentials
        ]
    
    async def verify_ownership(
        self,
        credential_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Verify that a credential belongs to a user."""
        credential = await self.get_by_id(credential_id)
        return credential is not None and credential.user_id == user_id
