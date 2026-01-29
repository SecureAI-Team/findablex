"""
Session storage for persisting browser sessions.

Allows crawlers to maintain logged-in state across restarts.
"""
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.async_api import BrowserContext

from app.config import settings

logger = logging.getLogger(__name__)


class SessionStore:
    """
    Persist and restore browser sessions for authenticated crawling.
    
    Sessions are stored as JSON files containing:
    - Cookies
    - Local storage
    - Session storage (via Playwright's storage_state)
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize session store.
        
        Args:
            storage_path: Directory to store session files.
                         Defaults to settings.session_storage_path or 'data/sessions'
        """
        self.storage_path = Path(
            storage_path or 
            getattr(settings, 'session_storage_path', 'data/sessions')
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Session TTL in hours
        self.session_ttl = getattr(settings, 'session_ttl_hours', 24)
    
    def _get_session_path(self, engine: str, account_id: str = "default") -> Path:
        """Get path for a session file."""
        # Sanitize inputs
        safe_engine = "".join(c for c in engine if c.isalnum() or c == "_")
        safe_account = "".join(c for c in account_id if c.isalnum() or c == "_")
        return self.storage_path / f"{safe_engine}_{safe_account}.json"
    
    def _get_metadata_path(self, engine: str, account_id: str = "default") -> Path:
        """Get path for session metadata file."""
        session_path = self._get_session_path(engine, account_id)
        return session_path.with_suffix(".meta.json")
    
    async def save_session(
        self,
        context: BrowserContext,
        engine: str,
        account_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save browser session to file.
        
        Args:
            context: Playwright browser context
            engine: Engine name (perplexity, chatgpt, etc.)
            account_id: Account identifier for multiple accounts
            metadata: Optional metadata to store with session
        
        Returns:
            True if saved successfully
        """
        try:
            session_path = self._get_session_path(engine, account_id)
            
            # Get storage state from Playwright
            storage_state = await context.storage_state()
            
            # Save session data
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(storage_state, f, ensure_ascii=False, indent=2)
            
            # Save metadata
            meta = {
                "engine": engine,
                "account_id": account_id,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=self.session_ttl)).isoformat(),
                "cookies_count": len(storage_state.get("cookies", [])),
                "origins_count": len(storage_state.get("origins", [])),
                **(metadata or {}),
            }
            
            metadata_path = self._get_metadata_path(engine, account_id)
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Session saved for {engine}/{account_id}: {len(storage_state.get('cookies', []))} cookies")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session for {engine}/{account_id}: {e}")
            return False
    
    async def load_session(
        self,
        engine: str,
        account_id: str = "default",
    ) -> Optional[Dict[str, Any]]:
        """
        Load browser session from file.
        
        Args:
            engine: Engine name
            account_id: Account identifier
        
        Returns:
            Storage state dict suitable for Playwright's new_context(storage_state=...),
            or None if no valid session exists
        """
        try:
            session_path = self._get_session_path(engine, account_id)
            
            if not session_path.exists():
                logger.debug(f"No session file for {engine}/{account_id}")
                return None
            
            # Check if session is expired
            if not await self.is_session_valid(engine, account_id):
                logger.info(f"Session expired for {engine}/{account_id}")
                await self.delete_session(engine, account_id)
                return None
            
            # Load session data
            with open(session_path, "r", encoding="utf-8") as f:
                storage_state = json.load(f)
            
            logger.info(f"Session loaded for {engine}/{account_id}")
            return storage_state
            
        except Exception as e:
            logger.error(f"Failed to load session for {engine}/{account_id}: {e}")
            return None
    
    async def is_session_valid(
        self,
        engine: str,
        account_id: str = "default",
    ) -> bool:
        """
        Check if a session is still valid (exists and not expired).
        
        Args:
            engine: Engine name
            account_id: Account identifier
        
        Returns:
            True if session is valid
        """
        try:
            session_path = self._get_session_path(engine, account_id)
            metadata_path = self._get_metadata_path(engine, account_id)
            
            if not session_path.exists():
                return False
            
            # Check metadata for expiration
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                
                expires_at = meta.get("expires_at")
                if expires_at:
                    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) > expiry:
                        return False
            
            # Check file age as fallback
            file_mtime = datetime.fromtimestamp(
                session_path.stat().st_mtime,
                tz=timezone.utc
            )
            max_age = timedelta(hours=self.session_ttl)
            if datetime.now(timezone.utc) - file_mtime > max_age:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking session validity: {e}")
            return False
    
    async def delete_session(
        self,
        engine: str,
        account_id: str = "default",
    ) -> bool:
        """
        Delete a session.
        
        Args:
            engine: Engine name
            account_id: Account identifier
        
        Returns:
            True if deleted successfully
        """
        try:
            session_path = self._get_session_path(engine, account_id)
            metadata_path = self._get_metadata_path(engine, account_id)
            
            if session_path.exists():
                session_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            
            logger.info(f"Session deleted for {engine}/{account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    async def list_sessions(self) -> list:
        """
        List all stored sessions.
        
        Returns:
            List of session info dicts
        """
        sessions = []
        
        try:
            for meta_file in self.storage_path.glob("*.meta.json"):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    
                    # Check validity
                    engine = meta.get("engine", "unknown")
                    account_id = meta.get("account_id", "default")
                    is_valid = await self.is_session_valid(engine, account_id)
                    
                    sessions.append({
                        **meta,
                        "is_valid": is_valid,
                    })
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
        
        return sessions
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions removed
        """
        removed = 0
        
        try:
            for session_file in self.storage_path.glob("*.json"):
                if session_file.suffix == ".json" and ".meta" not in session_file.name:
                    # Extract engine and account from filename
                    name_parts = session_file.stem.rsplit("_", 1)
                    if len(name_parts) == 2:
                        engine, account_id = name_parts
                        if not await self.is_session_valid(engine, account_id):
                            await self.delete_session(engine, account_id)
                            removed += 1
                            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info(f"Cleaned up {removed} expired sessions")
        return removed


# Global session store instance
_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """Get or create global session store instance."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
