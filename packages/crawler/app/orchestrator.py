"""Crawler orchestrator for managing crawl tasks."""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from app.config import settings
from app.browser.playwright_manager import PlaywrightManager
from app.browser.human_simulator import HumanSimulator
from app.browser.user_agents import get_user_agent_for_engine
from app.engines import EngineFactory
from app.proxy.pool_manager import ProxyPoolManager, get_proxy_pool
from app.auth.session_store import SessionStore, get_session_store
from app.auth.login_handler import LoginHandler

logger = logging.getLogger(__name__)


# ============================================================================
# CHALLENGE HANDLING FOR PRODUCTION CRAWLER
# ============================================================================

class ChallengeType(Enum):
    """Types of challenges that can be detected."""
    NONE = "none"
    CLOUDFLARE_JS = "cloudflare_js"
    CLOUDFLARE_CAPTCHA = "cloudflare_captcha"
    RECAPTCHA_V2 = "recaptcha_v2"
    HCAPTCHA = "hcaptcha"
    LOGIN_REQUIRED = "login_required"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"


class ProductionChallengeHandler:
    """
    Challenge handler for production crawler.
    
    In production, uses auto-wait strategy for JS challenges and
    reports CAPTCHA challenges for manual intervention or API solving.
    """
    
    CLOUDFLARE_INDICATORS = [
        "checking your browser",
        "please wait",
        "just a moment",
        "ddos protection by",
        "cf-browser-verification",
        "verifying you are human",
    ]
    
    CLOUDFLARE_SELECTORS = [
        "#cf-spinner",
        ".cf-browser-verification",
        "#challenge-running",
        "#challenge-form",
        'iframe[src*="challenges.cloudflare.com"]',
        "#turnstile-wrapper",
    ]
    
    def __init__(self, auto_wait_timeout: int = 30):
        self.auto_wait_timeout = auto_wait_timeout
    
    async def detect(self, page) -> ChallengeType:
        """Detect challenge type on page."""
        try:
            page_text = (await page.inner_text("body")).lower()
            
            # Check Cloudflare
            for indicator in self.CLOUDFLARE_INDICATORS:
                if indicator in page_text:
                    if await self._has_cloudflare_captcha(page):
                        return ChallengeType.CLOUDFLARE_CAPTCHA
                    return ChallengeType.CLOUDFLARE_JS
            
            for selector in self.CLOUDFLARE_SELECTORS:
                try:
                    if await page.query_selector(selector):
                        if selector in ['iframe[src*="challenges.cloudflare.com"]', "#turnstile-wrapper"]:
                            return ChallengeType.CLOUDFLARE_CAPTCHA
                        return ChallengeType.CLOUDFLARE_JS
                except:
                    pass
            
            # Check rate limiting
            if any(x in page_text for x in ["rate limit", "too many requests", "请求过于频繁"]):
                return ChallengeType.RATE_LIMITED
            
            # Check blocked
            if any(x in page_text for x in ["access denied", "blocked", "forbidden"]):
                return ChallengeType.BLOCKED
            
            return ChallengeType.NONE
            
        except Exception as e:
            logger.warning(f"Challenge detection error: {e}")
            return ChallengeType.NONE
    
    async def _has_cloudflare_captcha(self, page) -> bool:
        """Check if Cloudflare includes CAPTCHA."""
        selectors = [
            'iframe[src*="challenges.cloudflare.com"]',
            "#turnstile-wrapper",
            ".cf-turnstile",
        ]
        for selector in selectors:
            try:
                if await page.query_selector(selector):
                    return True
            except:
                pass
        return False
    
    async def handle(self, page, context, engine_name: str) -> bool:
        """
        Handle detected challenge.
        
        Returns True if challenge resolved, False otherwise.
        """
        challenge_type = await self.detect(page)
        
        if challenge_type == ChallengeType.NONE:
            return True
        
        logger.info(f"[ChallengeHandler] Detected {challenge_type.value} for {engine_name}")
        
        if challenge_type == ChallengeType.CLOUDFLARE_JS:
            # Auto-wait for JS challenges
            return await self._auto_wait(page)
        
        elif challenge_type == ChallengeType.CLOUDFLARE_CAPTCHA:
            # For CAPTCHA, try auto-wait first (sometimes passes)
            if await self._auto_wait(page, timeout=15):
                return True
            
            logger.warning(f"[ChallengeHandler] CAPTCHA requires manual solving for {engine_name}")
            return False
        
        elif challenge_type == ChallengeType.RATE_LIMITED:
            logger.warning("[ChallengeHandler] Rate limited - backing off")
            await asyncio.sleep(30)
            return False
        
        elif challenge_type == ChallengeType.BLOCKED:
            logger.error("[ChallengeHandler] IP blocked")
            return False
        
        return True
    
    async def _auto_wait(self, page, timeout: Optional[int] = None) -> bool:
        """Wait for auto-resolving challenges."""
        timeout = timeout or self.auto_wait_timeout
        start = time.time()
        
        while time.time() - start < timeout:
            await asyncio.sleep(1)
            
            if await self.detect(page) == ChallengeType.NONE:
                logger.info(f"[ChallengeHandler] Challenge auto-resolved in {time.time()-start:.1f}s")
                return True
            
            # Check for cf_clearance cookie
            cookies = await page.context.cookies()
            if any(c["name"] == "cf_clearance" for c in cookies):
                logger.info("[ChallengeHandler] Cloudflare clearance obtained")
                return True
        
        return False


class CrawlOrchestrator:
    """
    Orchestrate crawl tasks across multiple engines.
    
    Features:
    - Proxy rotation per task/query
    - Session management for authenticated crawling
    - Human behavior simulation
    - Rate limiting and retry logic
    - Challenge detection and handling (Cloudflare, CAPTCHA)
    """
    
    def __init__(self):
        self.browser_manager: Optional[PlaywrightManager] = None
        self.redis_client: Optional[redis.Redis] = None
        self.proxy_pool: Optional[ProxyPoolManager] = None
        self.session_store: Optional[SessionStore] = None
        self.login_handler: Optional[LoginHandler] = None
        self.challenge_handler: Optional[ProductionChallengeHandler] = None
        self.running = False
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self.stats = {
            "tasks_processed": 0,
            "queries_processed": 0,
            "queries_failed": 0,
            "challenges_detected": 0,
            "challenges_resolved": 0,
            "started_at": None,
        }
    
    async def start(self):
        """Start the orchestrator with all components."""
        self.running = True
        self.stats["started_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info("Starting CrawlOrchestrator...")
        
        # Initialize browser
        self.browser_manager = PlaywrightManager()
        await self.browser_manager.start()
        logger.info("Browser manager started")
        
        # Initialize proxy pool
        self.proxy_pool = get_proxy_pool()
        await self.proxy_pool.initialize()
        if self.proxy_pool.has_proxies:
            logger.info(f"Proxy pool initialized with {len(self.proxy_pool.proxies)} proxies")
        else:
            logger.warning("Running without proxies")
        
        # Initialize session store
        self.session_store = get_session_store()
        logger.info("Session store initialized")
        
        # Initialize login handler
        self.login_handler = LoginHandler(self.session_store)
        logger.info("Login handler initialized")
        
        # Initialize challenge handler
        auto_wait_timeout = getattr(settings, 'captcha_auto_wait_timeout', 30)
        self.challenge_handler = ProductionChallengeHandler(auto_wait_timeout=auto_wait_timeout)
        logger.info("Challenge handler initialized")
        
        # Connect to Redis
        self.redis_client = redis.from_url(settings.redis_url)
        logger.info(f"Connected to Redis: {settings.redis_url}")
        
        # Start task processing loop
        await self._process_tasks()
    
    async def shutdown(self):
        """Shutdown the orchestrator gracefully."""
        logger.info("Shutting down CrawlOrchestrator...")
        self.running = False
        
        # Cancel active tasks
        for task_id, task in self.active_tasks.items():
            task.cancel()
            logger.info(f"Cancelled task: {task_id}")
        
        # Close browser
        if self.browser_manager:
            await self.browser_manager.close()
            logger.info("Browser manager closed")
        
        # Close Redis
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
        
        logger.info(f"Orchestrator stats: {self.stats}")
    
    async def _process_tasks(self):
        """Main task processing loop."""
        logger.info("Starting task processing loop")
        
        while self.running:
            try:
                # Auto-refresh proxy pool if needed
                if self.proxy_pool:
                    await self.proxy_pool.auto_refresh_if_needed()
                
                # Get task from Redis queue
                task_data = await self.redis_client.lpop("crawler:tasks")
                
                if task_data:
                    await self._handle_task(task_data)
                else:
                    # No tasks, wait a bit
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                logger.info("Task processing cancelled")
                break
            except Exception as e:
                logger.error(f"Error in task processing loop: {e}")
                await asyncio.sleep(5)
    
    async def _handle_task(self, task_data: bytes):
        """Handle a single crawl task with full anti-detection."""
        task = json.loads(task_data)
        task_id = task.get("id")
        engine_name = task.get("engine")
        queries = task.get("queries", [])
        config = task.get("config", {})
        use_proxy = config.get("use_proxy", True)
        
        logger.info(f"Processing task {task_id}: engine={engine_name}, queries={len(queries)}")
        
        # Get engine adapter
        engine = EngineFactory.get(engine_name)
        if not engine:
            logger.error(f"Unknown engine: {engine_name}")
            await self._mark_task_failed(task_id, f"Unknown engine: {engine_name}")
            return
        
        # Update task status
        await self.redis_client.set(f"crawler:status:{task_id}", "running")
        
        successful = 0
        failed = 0
        
        # Get or create browser context for this task
        proxy = None
        if use_proxy and self.proxy_pool and self.proxy_pool.has_proxies:
            proxy = await self.proxy_pool.get_proxy()
            logger.info(f"Using proxy: {proxy['server'] if proxy else 'none'}")
        
        # Try to load existing session
        session_state = await self.session_store.load_session(engine_name)
        
        # Create context with proxy and session
        locale = config.get("language", "zh-CN")[:2] + "-" + config.get("region", "CN").upper()
        context = await self.browser_manager.new_context(
            proxy=proxy,
            locale=locale,
            storage_state=session_state,
        )
        
        try:
            # Process each query
            for query in queries:
                query_id = query.get("query_id")
                query_text = query.get("query_text", "")
                
                logger.info(f"Processing query: {query_text[:50]}...")
                
                try:
                    # Create page for this query
                    page = await context.new_page()
                    
                    try:
                        # Check login status if needed
                        if self.login_handler.requires_login(engine_name):
                            is_logged_in = await self.login_handler.ensure_logged_in(
                                engine_name,
                                context,
                                page,
                                config.get("credentials"),
                            )
                            if not is_logged_in:
                                logger.warning(f"Login required for {engine_name}")
                                raise Exception("Login required but could not authenticate")
                        
                        # Navigate to engine base URL and check for challenges
                        await page.goto(engine.base_url, wait_until="networkidle")
                        await asyncio.sleep(2)  # Brief wait for page to stabilize
                        
                        # Detect and handle challenges (Cloudflare, CAPTCHA, etc.)
                        if self.challenge_handler:
                            challenge_type = await self.challenge_handler.detect(page)
                            if challenge_type != ChallengeType.NONE:
                                self.stats["challenges_detected"] += 1
                                logger.info(f"Challenge detected: {challenge_type.value}")
                                
                                challenge_resolved = await self.challenge_handler.handle(
                                    page, context, engine_name
                                )
                                
                                if challenge_resolved:
                                    self.stats["challenges_resolved"] += 1
                                    # Save session after successful challenge resolution
                                    if self.session_store:
                                        try:
                                            await self.session_store.save_session(
                                                context, engine_name,
                                                metadata={"challenge_resolved": True}
                                            )
                                            logger.info(f"Session saved after challenge resolution for {engine_name}")
                                        except Exception as e:
                                            logger.warning(f"Failed to save session: {e}")
                                else:
                                    raise Exception(f"Challenge not resolved: {challenge_type.value}")
                        
                        # Execute crawl
                        result = await engine.crawl(
                            query=query_text,
                            browser_manager=self.browser_manager,
                            config=config,
                        )
                        
                        result["query_id"] = query_id
                        result["task_id"] = task_id
                        
                        # Save result to Redis
                        await self.redis_client.rpush(
                            f"crawler:results:{task_id}",
                            json.dumps(result),
                        )
                        
                        successful += 1
                        self.stats["queries_processed"] += 1
                        
                        # Mark proxy as successful
                        if proxy:
                            await self.proxy_pool.mark_success(proxy)
                        
                    finally:
                        await page.close()
                    
                    # Rate limiting between queries
                    rate_limit = getattr(settings, 'crawler_rate_limit', 0.2)
                    delay = 1 / rate_limit if rate_limit > 0 else 5
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Error crawling query '{query_text[:30]}': {e}")
                    
                    # Save error result
                    await self.redis_client.rpush(
                        f"crawler:results:{task_id}",
                        json.dumps({
                            "error": str(e),
                            "query_id": query_id,
                            "query": query_text,
                            "engine": engine_name,
                        }),
                    )
                    
                    failed += 1
                    self.stats["queries_failed"] += 1
                    
                    # Mark proxy as failed if proxy error
                    if proxy and "proxy" in str(e).lower():
                        await self.proxy_pool.mark_failed(proxy, str(e))
                        # Get new proxy for next query
                        proxy = await self.proxy_pool.get_proxy()
            
            # Save session after task (if login was successful)
            if session_state is None and successful > 0:
                try:
                    temp_page = await context.new_page()
                    await self.session_store.save_session(
                        context,
                        engine_name,
                        metadata={"task_id": task_id},
                    )
                    await temp_page.close()
                except Exception as e:
                    logger.warning(f"Failed to save session: {e}")
                    
        finally:
            await context.close()
        
        # Mark task as completed
        await self.redis_client.set(f"crawler:status:{task_id}", "completed")
        await self.redis_client.hset(
            f"crawler:task_stats:{task_id}",
            mapping={
                "successful": successful,
                "failed": failed,
                "total": len(queries),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        
        self.stats["tasks_processed"] += 1
        logger.info(f"Task {task_id} completed: {successful} success, {failed} failed")
    
    async def _mark_task_failed(self, task_id: str, error: str):
        """Mark a task as failed in Redis."""
        await self.redis_client.set(f"crawler:status:{task_id}", "failed")
        await self.redis_client.set(f"crawler:error:{task_id}", error)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            **self.stats,
            "proxy_stats": self.proxy_pool.get_stats() if self.proxy_pool else None,
            "active_tasks": len(self.active_tasks),
        }
