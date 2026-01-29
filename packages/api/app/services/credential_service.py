"""
Credential service for managing encrypted crawler credentials.

Provides secure storage and retrieval of API keys, cookies, and session tokens.
"""
import json
import logging
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.crawler import CrawlerCredential

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """Handle encryption/decryption of credential values."""
    
    def __init__(self, key: Optional[str] = None):
        """
        Initialize encryption handler.
        
        Args:
            key: Fernet encryption key. If not provided, uses settings.secret_key.
        """
        self._key = key or self._derive_key()
        self._fernet = Fernet(self._key)
    
    def _derive_key(self) -> bytes:
        """Derive a Fernet key from the application secret."""
        import hashlib
        
        # Use SHA256 of secret_key, then base64 encode to get Fernet-compatible key
        secret = getattr(settings, 'secret_key', 'default-secret-change-me')
        key_bytes = hashlib.sha256(secret.encode()).digest()
        return urlsafe_b64encode(key_bytes)
    
    def encrypt(self, value: Any) -> str:
        """
        Encrypt a value.
        
        Args:
            value: Value to encrypt (will be JSON serialized if not string)
        
        Returns:
            Encrypted string (base64)
        """
        if not isinstance(value, str):
            value = json.dumps(value)
        
        encrypted = self._fernet.encrypt(value.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt a value.
        
        Args:
            encrypted: Encrypted string
        
        Returns:
            Decrypted string
        
        Raises:
            InvalidToken: If decryption fails
        """
        decrypted = self._fernet.decrypt(encrypted.encode())
        return decrypted.decode()
    
    def decrypt_json(self, encrypted: str) -> Any:
        """
        Decrypt and parse JSON value.
        
        Args:
            encrypted: Encrypted string
        
        Returns:
            Parsed JSON value
        """
        decrypted = self.decrypt(encrypted)
        try:
            return json.loads(decrypted)
        except json.JSONDecodeError:
            return decrypted


# Global encryption instance
_encryption: Optional[CredentialEncryption] = None


def get_encryption() -> CredentialEncryption:
    """Get or create global encryption instance."""
    global _encryption
    if _encryption is None:
        _encryption = CredentialEncryption()
    return _encryption


class CredentialService:
    """Service for managing crawler credentials."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.encryption = get_encryption()
    
    async def create(
        self,
        workspace_id: UUID,
        engine: str,
        credential_type: str,
        value: Any,
        created_by: UUID,
        account_id: Optional[str] = None,
        label: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> CrawlerCredential:
        """
        Create a new credential.
        
        Args:
            workspace_id: Workspace ID
            engine: Engine name (perplexity, chatgpt, etc.)
            credential_type: Type (api_key, cookie, session, oauth_token)
            value: Credential value (will be encrypted)
            created_by: User ID who created this
            account_id: Optional account identifier
            label: Optional human-readable label
            expires_at: Optional expiration time
        
        Returns:
            Created credential
        """
        # Encrypt the value
        encrypted_value = self.encryption.encrypt(value)
        
        credential = CrawlerCredential(
            workspace_id=workspace_id,
            engine=engine,
            credential_type=credential_type,
            encrypted_value=encrypted_value,
            account_id=account_id,
            label=label,
            expires_at=expires_at,
            created_by=created_by,
        )
        
        self.db.add(credential)
        await self.db.commit()
        await self.db.refresh(credential)
        
        logger.info(f"Created credential for {engine}/{credential_type} in workspace {workspace_id}")
        return credential
    
    async def get_by_id(self, credential_id: UUID) -> Optional[CrawlerCredential]:
        """Get credential by ID."""
        result = await self.db.execute(
            select(CrawlerCredential).where(CrawlerCredential.id == credential_id)
        )
        return result.scalar_one_or_none()
    
    async def get_for_engine(
        self,
        workspace_id: UUID,
        engine: str,
        credential_type: Optional[str] = None,
        account_id: Optional[str] = None,
        active_only: bool = True,
    ) -> List[CrawlerCredential]:
        """
        Get credentials for a specific engine.
        
        Args:
            workspace_id: Workspace ID
            engine: Engine name
            credential_type: Optional type filter
            account_id: Optional account filter
            active_only: Only return active credentials
        
        Returns:
            List of matching credentials
        """
        query = select(CrawlerCredential).where(
            CrawlerCredential.workspace_id == workspace_id,
            CrawlerCredential.engine == engine,
        )
        
        if credential_type:
            query = query.where(CrawlerCredential.credential_type == credential_type)
        
        if account_id:
            query = query.where(CrawlerCredential.account_id == account_id)
        
        if active_only:
            query = query.where(CrawlerCredential.is_active == True)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_decrypted_value(
        self,
        credential_id: UUID,
    ) -> Optional[Any]:
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
            return self.encryption.decrypt_json(credential.encrypted_value)
        except InvalidToken:
            logger.error(f"Failed to decrypt credential {credential_id}")
            return None
    
    async def get_active_credential(
        self,
        workspace_id: UUID,
        engine: str,
        credential_type: str = "cookie",
        account_id: str = "default",
    ) -> Optional[Dict[str, Any]]:
        """
        Get an active, non-expired credential with decrypted value.
        
        Args:
            workspace_id: Workspace ID
            engine: Engine name
            credential_type: Credential type
            account_id: Account identifier
        
        Returns:
            Dict with credential info and decrypted value, or None
        """
        credentials = await self.get_for_engine(
            workspace_id,
            engine,
            credential_type,
            account_id,
            active_only=True,
        )
        
        for cred in credentials:
            # Skip expired
            if cred.is_expired:
                continue
            
            try:
                value = self.encryption.decrypt_json(cred.encrypted_value)
                return {
                    "id": cred.id,
                    "engine": cred.engine,
                    "credential_type": cred.credential_type,
                    "account_id": cred.account_id,
                    "value": value,
                    "expires_at": cred.expires_at,
                }
            except InvalidToken:
                continue
        
        return None
    
    async def update_value(
        self,
        credential_id: UUID,
        value: Any,
        expires_at: Optional[datetime] = None,
    ) -> bool:
        """
        Update credential value.
        
        Args:
            credential_id: Credential ID
            value: New value (will be encrypted)
            expires_at: Optional new expiration time
        
        Returns:
            True if updated
        """
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False
        
        credential.encrypted_value = self.encryption.encrypt(value)
        if expires_at is not None:
            credential.expires_at = expires_at
        credential.last_error = None  # Clear any previous error
        
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
    
    async def delete(self, credential_id: UUID) -> bool:
        """Delete a credential."""
        credential = await self.get_by_id(credential_id)
        if not credential:
            return False
        
        await self.db.delete(credential)
        await self.db.commit()
        return True
    
    async def list_for_workspace(
        self,
        workspace_id: UUID,
        include_inactive: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List all credentials for a workspace (without decrypted values).
        
        Args:
            workspace_id: Workspace ID
            include_inactive: Include inactive credentials
        
        Returns:
            List of credential info dicts
        """
        query = select(CrawlerCredential).where(
            CrawlerCredential.workspace_id == workspace_id
        )
        
        if not include_inactive:
            query = query.where(CrawlerCredential.is_active == True)
        
        query = query.order_by(CrawlerCredential.engine, CrawlerCredential.credential_type)
        
        result = await self.db.execute(query)
        credentials = result.scalars().all()
        
        return [
            {
                "id": str(cred.id),
                "engine": cred.engine,
                "credential_type": cred.credential_type,
                "account_id": cred.account_id,
                "label": cred.label,
                "is_active": cred.is_active,
                "is_expired": cred.is_expired,
                "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None,
                "last_error": cred.last_error,
                "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
                "created_at": cred.created_at.isoformat(),
            }
            for cred in credentials
        ]
