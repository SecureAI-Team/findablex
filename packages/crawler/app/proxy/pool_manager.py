"""Proxy pool manager for rotating proxies."""
import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ProxyPoolManager:
    """
    Manage a pool of rotating proxies with health tracking.
    
    Features:
    - Load proxies from external API or static list
    - Random rotation with failure tracking
    - Automatic proxy health checking
    - Rate limiting per proxy
    """
    
    def __init__(self):
        self.proxies: List[Dict[str, str]] = []
        self.failed_proxies: Dict[str, datetime] = {}  # server -> failure time
        self.usage_count: Dict[str, int] = {}  # server -> usage count
        self.last_refresh: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
        # Configuration
        self.failure_cooldown = timedelta(minutes=5)  # Time before retrying failed proxy
        self.max_failures = 3  # Max failures before longer cooldown
        self.refresh_interval = timedelta(hours=1)  # Auto refresh interval
    
    async def initialize(self, proxy_list: Optional[List[Dict]] = None):
        """
        Initialize proxy pool.
        
        Args:
            proxy_list: Optional static proxy list. If not provided, fetches from URL.
        """
        if proxy_list:
            self._parse_proxy_list(proxy_list)
            return
        
        # Try to fetch from configured URL
        proxy_url = getattr(settings, 'proxy_pool_url', None)
        if not proxy_url:
            logger.info("No proxy pool URL configured, running without proxies")
            return
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(proxy_url)
                if response.status_code == 200:
                    data = response.json()
                    self._parse_proxy_list(data.get("proxies", []))
                    self.last_refresh = datetime.now(timezone.utc)
                    logger.info(f"Loaded {len(self.proxies)} proxies from pool")
        except Exception as e:
            logger.error(f"Failed to initialize proxy pool: {e}")
    
    def _parse_proxy_list(self, proxy_list: List[Dict]):
        """Parse proxy list into standard format."""
        self.proxies = []
        
        for p in proxy_list:
            # Support multiple formats
            if isinstance(p, str):
                # Format: "ip:port" or "ip:port:user:pass"
                parts = p.split(":")
                if len(parts) >= 2:
                    proxy = {"server": f"http://{parts[0]}:{parts[1]}"}
                    if len(parts) >= 4:
                        proxy["username"] = parts[2]
                        proxy["password"] = parts[3]
                    self.proxies.append(proxy)
            elif isinstance(p, dict):
                # Format: {"ip": "...", "port": "...", ...} or {"server": "..."}
                if "server" in p:
                    self.proxies.append(p)
                elif "ip" in p and "port" in p:
                    proxy = {
                        "server": f"http://{p['ip']}:{p['port']}",
                    }
                    if p.get("username"):
                        proxy["username"] = p["username"]
                    if p.get("password"):
                        proxy["password"] = p["password"]
                    self.proxies.append(proxy)
    
    def add_proxy(self, server: str, username: str = None, password: str = None):
        """Add a single proxy to the pool."""
        proxy = {"server": server}
        if username:
            proxy["username"] = username
        if password:
            proxy["password"] = password
        self.proxies.append(proxy)
    
    async def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get the next available proxy.
        
        Uses random selection with failure avoidance.
        
        Returns:
            Proxy dict suitable for Playwright, or None if no proxies available
        """
        if not self.proxies:
            return None
        
        async with self._lock:
            now = datetime.now(timezone.utc)
            
            # Filter out recently failed proxies
            available = []
            for proxy in self.proxies:
                server = proxy["server"]
                
                if server in self.failed_proxies:
                    failure_time = self.failed_proxies[server]
                    if now - failure_time < self.failure_cooldown:
                        continue  # Still in cooldown
                    else:
                        # Cooldown expired, remove from failed
                        del self.failed_proxies[server]
                
                available.append(proxy)
            
            if not available:
                # All proxies failed, reset and try any
                logger.warning("All proxies in cooldown, resetting failure state")
                self.failed_proxies.clear()
                available = self.proxies
            
            # Select proxy with least usage
            min_usage = min(self.usage_count.get(p["server"], 0) for p in available)
            candidates = [p for p in available if self.usage_count.get(p["server"], 0) == min_usage]
            
            proxy = random.choice(candidates)
            self.usage_count[proxy["server"]] = self.usage_count.get(proxy["server"], 0) + 1
            
            return proxy
    
    async def mark_failed(self, proxy: Dict[str, str], error: Optional[str] = None):
        """
        Mark a proxy as failed.
        
        Args:
            proxy: The proxy that failed
            error: Optional error message
        """
        if not proxy:
            return
        
        server = proxy["server"]
        
        async with self._lock:
            self.failed_proxies[server] = datetime.now(timezone.utc)
            logger.warning(f"Proxy marked as failed: {server} - {error or 'unknown error'}")
    
    async def mark_success(self, proxy: Dict[str, str]):
        """
        Mark a proxy as successful.
        
        Args:
            proxy: The proxy that succeeded
        """
        if not proxy:
            return
        
        server = proxy["server"]
        
        async with self._lock:
            # Remove from failed if present
            self.failed_proxies.pop(server, None)
    
    async def refresh(self):
        """Refresh the proxy pool from source."""
        await self.initialize()
    
    async def auto_refresh_if_needed(self):
        """Refresh proxy pool if refresh interval has passed."""
        if self.last_refresh is None:
            return
        
        now = datetime.now(timezone.utc)
        if now - self.last_refresh > self.refresh_interval:
            logger.info("Auto-refreshing proxy pool")
            await self.refresh()
    
    async def health_check(self, proxy: Dict[str, str], test_url: str = "https://httpbin.org/ip") -> bool:
        """
        Check if a proxy is working.
        
        Args:
            proxy: Proxy to test
            test_url: URL to test against
        
        Returns:
            True if proxy is working
        """
        try:
            proxies = {"http://": proxy["server"], "https://": proxy["server"]}
            
            async with httpx.AsyncClient(proxies=proxies, timeout=10.0) as client:
                response = await client.get(test_url)
                return response.status_code == 200
        except Exception:
            return False
    
    async def check_all_proxies(self) -> Dict[str, bool]:
        """
        Check health of all proxies.
        
        Returns:
            Dict of server -> is_healthy
        """
        results = {}
        
        for proxy in self.proxies:
            server = proxy["server"]
            is_healthy = await self.health_check(proxy)
            results[server] = is_healthy
            
            if not is_healthy:
                await self.mark_failed(proxy, "health check failed")
        
        logger.info(f"Proxy health check: {sum(results.values())}/{len(results)} healthy")
        return results
    
    def get_stats(self) -> Dict:
        """Get proxy pool statistics."""
        return {
            "total": len(self.proxies),
            "failed": len(self.failed_proxies),
            "available": len(self.proxies) - len(self.failed_proxies),
            "usage_counts": dict(self.usage_count),
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
        }
    
    @property
    def has_proxies(self) -> bool:
        """Check if any proxies are available."""
        return len(self.proxies) > 0


# Global proxy pool instance
_proxy_pool: Optional[ProxyPoolManager] = None


def get_proxy_pool() -> ProxyPoolManager:
    """Get or create global proxy pool instance."""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPoolManager()
    return _proxy_pool


async def initialize_proxy_pool(proxy_list: Optional[List[Dict]] = None):
    """Initialize the global proxy pool."""
    pool = get_proxy_pool()
    await pool.initialize(proxy_list)
    return pool
