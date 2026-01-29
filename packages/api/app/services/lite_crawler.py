"""
Lite mode crawler service - executes crawler tasks directly without Redis/Celery.

This allows local development and testing without the full infrastructure.
Uses sync playwright in a thread to avoid Windows asyncio subprocess issues.
"""
import asyncio
import concurrent.futures
import logging
import os
import random
import sys
from datetime import datetime, timezone
from functools import partial
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import async_session_maker
from app.models.crawler import CrawlResult, CrawlTask

# Try to import playwright (sync version for Windows compatibility)
try:
    from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    BrowserContext = None
    Page = None
    sync_playwright = None

logger = logging.getLogger(__name__)


# User agents for rotation (expanded pool)
USER_AGENTS = [
    # Chrome Windows (most common)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Realistic viewport configurations
VIEWPORT_CONFIGS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 2560, "height": 1440},
]

# Full anti-detection stealth script (comprehensive protection)
STEALTH_SCRIPT = """
(function() {
    'use strict';
    
    // ===== Navigator.webdriver =====
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });
    delete Navigator.prototype.webdriver;
    
    // ===== Chrome Runtime =====
    if (!window.chrome) {
        window.chrome = {};
    }
    window.chrome.runtime = {
        id: undefined,
        connect: function() {},
        sendMessage: function() {},
        onMessage: { addListener: function() {} }
    };
    window.chrome.loadTimes = function() {
        return {
            requestTime: Date.now() / 1000 - Math.random() * 100,
            startLoadTime: Date.now() / 1000 - Math.random() * 10,
            commitLoadTime: Date.now() / 1000 - Math.random() * 5,
            finishDocumentLoadTime: Date.now() / 1000 - Math.random() * 2,
            finishLoadTime: Date.now() / 1000 - Math.random(),
            firstPaintTime: Date.now() / 1000 - Math.random() * 3,
            firstPaintAfterLoadTime: 0,
            navigationType: 'Other',
            wasFetchedViaSpdy: false,
            wasNpnNegotiated: true,
            npnNegotiatedProtocol: 'h2',
            wasAlternateProtocolAvailable: false,
            connectionInfo: 'h2'
        };
    };
    window.chrome.csi = function() {
        return {
            onloadT: Date.now(),
            startE: Date.now() - Math.random() * 1000,
            pageT: Math.random() * 10000,
            tran: 15
        };
    };
    
    // ===== Permissions API =====
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => {
        if (parameters.name === 'notifications') {
            return Promise.resolve({ state: Notification.permission });
        }
        return originalQuery.call(window.navigator.permissions, parameters);
    };
    
    // ===== Canvas Fingerprint Protection =====
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    
    function addNoise(imageData) {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            data[i] = Math.max(0, Math.min(255, data[i] + (Math.random() - 0.5) * 4));
            data[i+1] = Math.max(0, Math.min(255, data[i+1] + (Math.random() - 0.5) * 4));
            data[i+2] = Math.max(0, Math.min(255, data[i+2] + (Math.random() - 0.5) * 4));
        }
        return imageData;
    }
    
    HTMLCanvasElement.prototype.toDataURL = function(...args) {
        const ctx = this.getContext('2d');
        if (ctx) {
            try {
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                addNoise(imageData);
                ctx.putImageData(imageData, 0, 0);
            } catch(e) {}
        }
        return originalToDataURL.apply(this, args);
    };
    
    CanvasRenderingContext2D.prototype.getImageData = function(...args) {
        const imageData = originalGetImageData.apply(this, args);
        return addNoise(imageData);
    };
    
    // ===== WebGL Fingerprint Protection =====
    const getParameterProxyHandler = {
        apply: function(target, thisArg, args) {
            const param = args[0];
            if (param === 37445) return 'Intel Inc.';
            if (param === 37446) return 'Intel Iris OpenGL Engine';
            return Reflect.apply(target, thisArg, args);
        }
    };
    
    if (WebGLRenderingContext.prototype.getParameter) {
        WebGLRenderingContext.prototype.getParameter = new Proxy(
            WebGLRenderingContext.prototype.getParameter,
            getParameterProxyHandler
        );
    }
    if (typeof WebGL2RenderingContext !== 'undefined' && WebGL2RenderingContext.prototype.getParameter) {
        WebGL2RenderingContext.prototype.getParameter = new Proxy(
            WebGL2RenderingContext.prototype.getParameter,
            getParameterProxyHandler
        );
    }
    
    // ===== Navigator Properties =====
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const plugins = [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
            ];
            plugins.length = 3;
            plugins.item = (i) => plugins[i];
            plugins.namedItem = (name) => plugins.find(p => p.name === name);
            plugins.refresh = () => {};
            return plugins;
        }
    });
    
    Object.defineProperty(navigator, 'mimeTypes', {
        get: () => {
            const mimeTypes = [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
                { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' }
            ];
            mimeTypes.length = 2;
            mimeTypes.item = (i) => mimeTypes[i];
            mimeTypes.namedItem = (type) => mimeTypes.find(m => m.type === type);
            return mimeTypes;
        }
    });
    
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en-US', 'en']
    });
    
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32'
    });
    
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8
    });
    
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8
    });
    
    // ===== Screen Properties =====
    Object.defineProperty(screen, 'availWidth', { get: () => screen.width });
    Object.defineProperty(screen, 'availHeight', { get: () => screen.height - 40 });
    Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
    Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
    
    // ===== History Length =====
    Object.defineProperty(history, 'length', {
        get: () => Math.floor(Math.random() * 10) + 5
    });
    
    // ===== Performance API Protection =====
    const originalPerformanceNow = performance.now;
    performance.now = function() {
        return originalPerformanceNow.call(performance) + Math.random() * 0.5;
    };
    
    // ===== WebRTC Protection =====
    if (window.RTCPeerConnection) {
        const originalRTCPeerConnection = window.RTCPeerConnection;
        window.RTCPeerConnection = function(config) {
            if (config && config.iceServers) {
                config.iceServers = [];
            }
            return new originalRTCPeerConnection(config);
        };
        window.RTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
    }
    
    // ===== Headless Detection =====
    Object.defineProperty(document, 'hidden', { get: () => false });
    Object.defineProperty(document, 'visibilityState', { get: () => 'visible' });
    
    // ===== Outerwidth/Outerheight Protection =====
    if (window.outerWidth === 0) {
        Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth + 16 });
    }
    if (window.outerHeight === 0) {
        Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight + 88 });
    }
    
    // ===== CDP Markers Removal =====
    const cdpMarkers = [
        '__webdriver_evaluate', '__selenium_evaluate', '__webdriver_script_function',
        '__webdriver_script_func', '__webdriver_script_fn', '__fxdriver_evaluate',
        '__driver_unwrapped', '__webdriver_unwrapped', '__driver_evaluate',
        '__selenium_unwrapped', '__fxdriver_unwrapped',
        'cdc_adoQpoasnfa76pfcZLmcfl_Array', 'cdc_adoQpoasnfa76pfcZLmcfl_Promise',
        'cdc_adoQpoasnfa76pfcZLmcfl_Symbol'
    ];
    cdpMarkers.forEach(marker => {
        try { delete window[marker]; } catch(e) {}
        try { delete document[marker]; } catch(e) {}
    });
    
    // ===== Error Stack Protection =====
    const originalError = Error;
    Error = function(...args) {
        const error = new originalError(...args);
        const stack = error.stack;
        if (stack && stack.includes('playwright')) {
            error.stack = stack.replace(/playwright[^\\n]*/g, '');
        }
        return error;
    };
    Error.prototype = originalError.prototype;
    if (originalError.captureStackTrace) {
        Error.captureStackTrace = originalError.captureStackTrace;
    }
    
})();
"""

# Browser launch arguments for stealth mode
STEALTH_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-infobars",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-component-extensions-with-background-pages",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=TranslateUI",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-renderer-backgrounding",
    "--disable-sync",
    "--enable-features=NetworkService,NetworkServiceInProcess",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--no-first-run",
    "--password-store=basic",
    "--use-mock-keychain",
    "--disable-features=IsolateOrigins,site-per-process",
]


class HumanSimulator:
    """Simulate human-like behavior to avoid detection."""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def type_text(self, selector: str, text: str):
        """Type text with human-like delays and occasional typos."""
        element = await self.page.query_selector(selector)
        if not element:
            return
        
        await element.click()
        await self.random_delay(100, 300)
        
        for char in text:
            # Occasional typo (3% chance)
            if random.random() < 0.03:
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                await self.page.keyboard.type(wrong_char)
                await self.random_delay(50, 150)
                await self.page.keyboard.press("Backspace")
                await self.random_delay(50, 150)
            
            await self.page.keyboard.type(char)
            
            # Variable typing speed (30-150ms per char)
            delay = random.randint(30, 150)
            await asyncio.sleep(delay / 1000)
    
    async def random_delay(self, min_ms: int, max_ms: int):
        """Wait for a random duration."""
        delay = random.randint(min_ms, max_ms)
        await asyncio.sleep(delay / 1000)
    
    async def natural_scroll(self, direction: str = "down"):
        """Scroll naturally with random pauses."""
        scroll_amount = random.randint(100, 500)
        
        if direction == "down":
            await self.page.mouse.wheel(0, scroll_amount)
        else:
            await self.page.mouse.wheel(0, -scroll_amount)
        
        await self.random_delay(500, 1500)
    
    async def random_mouse_movement(self):
        """Make random mouse movements."""
        viewport = self.page.viewport_size or {"width": 1920, "height": 1080}
        target_x = random.randint(0, viewport["width"])
        target_y = random.randint(0, viewport["height"])
        
        await self.page.mouse.move(target_x, target_y)
        await self.random_delay(100, 300)


class LitePlaywrightManager:
    """
    Lightweight Playwright manager for lite mode.
    Uses sync playwright in a thread pool to avoid Windows asyncio subprocess issues.
    Supports session persistence for Cloudflare/CAPTCHA bypass.
    """
    
    SESSION_DIR = "data/sessions"
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._headless = True
        self._current_context: Optional[BrowserContext] = None
        self._current_engine: Optional[str] = None
        
        # Ensure session directory exists
        os.makedirs(self.SESSION_DIR, exist_ok=True)
    
    def _get_session_path(self, engine: str, account: str = "default") -> str:
        """Get the session file path for an engine/account."""
        return os.path.join(self.SESSION_DIR, f"{engine}_{account}.json")
    
    def _session_exists(self, engine: str, account: str = "default") -> bool:
        """Check if a session file exists."""
        path = self._get_session_path(engine, account)
        return os.path.exists(path)
    
    def _is_session_valid(self, engine: str, account: str = "default", ttl_hours: int = 24) -> bool:
        """Check if session exists and is not expired."""
        path = self._get_session_path(engine, account)
        if not os.path.exists(path):
            return False
        
        # Check file age
        file_age_hours = (datetime.now().timestamp() - os.path.getmtime(path)) / 3600
        return file_age_hours < ttl_hours
    
    def _start_sync(self, headless: bool = True):
        """Start the browser (sync version - runs in thread)."""
        self.playwright = sync_playwright().start()
        
        # Launch browser with comprehensive anti-detection settings
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=STEALTH_LAUNCH_ARGS,
        )
        
        logger.info("LitePlaywrightManager: Browser started (stealth mode)")
    
    async def start(self, headless: bool = True):
        """Start the browser (async wrapper)."""
        self._headless = headless
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, partial(self._start_sync, headless))
    
    def _close_sync(self):
        """Close the browser (sync version)."""
        if self._current_context:
            try:
                self._current_context.close()
            except:
                pass
            self._current_context = None
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("LitePlaywrightManager: Browser closed")
    
    async def close(self):
        """Close the browser (async wrapper)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self._close_sync)
        self._executor.shutdown(wait=False)
    
    def _new_context_with_session_sync(
        self,
        engine: str,
        account: str = "default",
        locale: str = "zh-CN",
        user_agent: Optional[str] = None,
    ) -> BrowserContext:
        """Create a new browser context with session persistence (sync version)."""
        # Random user agent and viewport for fingerprint diversity
        ua = user_agent or random.choice(USER_AGENTS)
        viewport = random.choice(VIEWPORT_CONFIGS)
        session_path = self._get_session_path(engine, account)
        
        context_options = {
            "viewport": viewport,
            "user_agent": ua,
            "locale": locale,
            "timezone_id": "Asia/Shanghai" if locale.startswith("zh") else "America/New_York",
            "color_scheme": "light",
            "device_scale_factor": 1,
        }
        
        # Load existing session if valid
        if self._is_session_valid(engine, account):
            logger.info(f"[Session] Loading existing session for {engine}/{account}")
            context_options["storage_state"] = session_path
        else:
            logger.info(f"[Session] No valid session for {engine}/{account}, creating new")
        
        logger.info(f"[Context] UA: {ua[:50]}..., Viewport: {viewport}")
        context = self.browser.new_context(**context_options)
        
        # Add comprehensive stealth scripts
        context.add_init_script(STEALTH_SCRIPT)
        
        self._current_context = context
        self._current_engine = engine
        
        return context
    
    def _new_context_sync(
        self,
        locale: str = "zh-CN",
        user_agent: Optional[str] = None,
    ) -> BrowserContext:
        """Create a new browser context without session (sync version)."""
        # Random user agent and viewport for fingerprint diversity
        ua = user_agent or random.choice(USER_AGENTS)
        viewport = random.choice(VIEWPORT_CONFIGS)
        
        context = self.browser.new_context(
            viewport=viewport,
            user_agent=ua,
            locale=locale,
            timezone_id="Asia/Shanghai" if locale.startswith("zh") else "America/New_York",
            color_scheme="light",
            device_scale_factor=1,
        )
        
        # Add comprehensive stealth scripts
        context.add_init_script(STEALTH_SCRIPT)
        
        self._current_context = context
        
        return context
    
    def save_session_sync(self, context: BrowserContext, engine: str, account: str = "default"):
        """Save browser session to file (sync version)."""
        try:
            session_path = self._get_session_path(engine, account)
            context.storage_state(path=session_path)
            logger.info(f"[Session] Saved session for {engine}/{account} to {session_path}")
        except Exception as e:
            logger.warning(f"[Session] Failed to save session: {e}")
    
    async def save_session(self, context: BrowserContext, engine: str, account: str = "default"):
        """Save browser session to file (async wrapper)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            partial(self.save_session_sync, context, engine, account)
        )
    
    def clear_session_sync(self, engine: str, account: str = "default"):
        """Clear a session file (sync version)."""
        session_path = self._get_session_path(engine, account)
        if os.path.exists(session_path):
            os.remove(session_path)
            logger.info(f"[Session] Cleared session for {engine}/{account}")
    
    async def new_context(
        self,
        locale: str = "zh-CN",
        user_agent: Optional[str] = None,
    ) -> BrowserContext:
        """Create a new browser context (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, 
            partial(self._new_context_sync, locale, user_agent)
        )
    
    async def new_context_with_session(
        self,
        engine: str,
        account: str = "default",
        locale: str = "zh-CN",
        user_agent: Optional[str] = None,
    ) -> BrowserContext:
        """Create a new browser context with session persistence (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            partial(self._new_context_with_session_sync, engine, account, locale, user_agent)
        )
    
    def _new_page_sync(self, context: BrowserContext) -> Page:
        """Create a new page (sync version)."""
        page = context.new_page()
        page.set_default_timeout(30000)
        return page
    
    async def new_page(self, context: Optional[BrowserContext] = None) -> Page:
        """Create a new page (async wrapper)."""
        if context is None:
            context = await self.new_context()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, partial(self._new_page_sync, context))


class LiteEngineBase:
    """Base class for lite mode engine adapters. Uses sync playwright methods."""
    
    name: str = "base"
    base_url: str = ""
    
    def __init__(self):
        # Import challenge handler (lazy import to avoid circular imports)
        try:
            from app.services.challenge_handler import ChallengeHandler, ChallengeType
            self._challenge_handler = ChallengeHandler(
                strategy=getattr(settings, 'captcha_strategy', 'smart')
            )
            self._ChallengeType = ChallengeType
            logger.info(f"[{self.__class__.__name__}] ChallengeHandler initialized with strategy: {getattr(settings, 'captcha_strategy', 'smart')}")
        except ImportError as e:
            logger.error(f"[{self.__class__.__name__}] Failed to import ChallengeHandler: {e}")
            self._challenge_handler = None
            self._ChallengeType = None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Error initializing ChallengeHandler: {e}")
            self._challenge_handler = None
            self._ChallengeType = None
    
    def crawl_sync(
        self,
        query: str,
        page: Page,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl a query (sync version) - to be implemented by subclasses."""
        raise NotImplementedError
    
    def detect_and_handle_challenge(self, page, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Detect and handle any challenge on the page.
        
        Args:
            page: Playwright page object
            config: Optional configuration
            
        Returns:
            True if no challenge or challenge resolved, False if failed
        """
        if not self._challenge_handler:
            logger.warning(f"[{self.name}] No challenge handler available, skipping detection")
            return True
        
        config = config or {}
        
        try:
            logger.info(f"[{self.name}] Detecting challenges on page...")
            challenge_type = self._challenge_handler.detect(page)
            logger.info(f"[{self.name}] Detection result: {challenge_type.value if challenge_type else 'None'}")
            
            if challenge_type == self._ChallengeType.NONE:
                logger.info(f"[{self.name}] No challenge detected, continuing")
                return True
            
            logger.info(f"[{self.name}] Challenge detected: {challenge_type.value}")
            
            # Handle the challenge
            result = self._challenge_handler.handle(page, config)
            
            if result.success:
                logger.info(f"[{self.name}] Challenge resolved: {result.message}")
                return True
            else:
                logger.warning(f"[{self.name}] Challenge failed: {result.message}")
                return False
                
        except Exception as e:
            logger.error(f"[{self.name}] Challenge handling error: {e}", exc_info=True)
            return True  # Continue anyway on error
    
    # Common generating state indicators used across AI chatbots
    COMMON_GENERATING_SELECTORS = [
        'button:has-text("停止")',
        'button:has-text("Stop")',
        'button:has-text("停止生成")',
        '[aria-label*="停止"]',
        '[aria-label*="Stop"]',
        '[class*="loading"]',
        '[class*="typing"]',
        '[class*="generating"]',
        '[class*="streaming"]',
        '[class*="thinking"]',
        '.animate-pulse',
        '[class*="cursor-blink"]',
        '[class*="cursor"]',
    ]
    
    def _is_generating(self, page: Page, extra_selectors: List[str] = None) -> bool:
        """Check if AI is still generating response."""
        selectors = self.COMMON_GENERATING_SELECTORS + (extra_selectors or [])
        for selector in selectors:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    logger.debug(f"[{self.name}] Still generating (found: {selector})")
                    return True
            except:
                pass
        return False
    
    def wait_for_response_complete(
        self,
        page: Page,
        response_extractor: callable,
        max_wait_seconds: int = 120,
        extra_generating_selectors: List[str] = None,
    ) -> str:
        """
        Wait for AI response to fully complete.
        
        Args:
            page: Playwright page
            response_extractor: Function that extracts response text from page
            max_wait_seconds: Maximum time to wait
            extra_generating_selectors: Additional selectors to check for generating state
        
        Returns:
            The complete response text
        """
        import time
        start_time = time.time()
        last_response_text = ""
        last_response_length = 0
        stable_count = 0
        
        logger.info(f"[{self.name}] Waiting for response to complete...")
        
        while time.time() - start_time < max_wait_seconds:
            # Check if still generating
            if self._is_generating(page, extra_generating_selectors):
                logger.debug(f"[{self.name}] Still generating...")
                time.sleep(2)
                stable_count = 0
                continue
            
            # Get current response text
            try:
                current_text = response_extractor(page)
            except:
                current_text = ""
            
            current_length = len(current_text) if current_text else 0
            
            # Check if response is growing
            if current_length > last_response_length + 20:
                logger.debug(f"[{self.name}] Response growing: {last_response_length} -> {current_length}")
                last_response_length = current_length
                last_response_text = current_text
                stable_count = 0
                time.sleep(2)
                continue
            
            # Check if response has stabilized
            if current_text and current_text == last_response_text and len(current_text) > 30:
                stable_count += 1
                logger.debug(f"[{self.name}] Response stable count: {stable_count}")
                
                if stable_count >= 4:  # 8 seconds of stability
                    logger.info(f"[{self.name}] Response complete after {int(time.time() - start_time)}s")
                    return current_text
            else:
                stable_count = 0
                last_response_text = current_text
                last_response_length = current_length
            
            time.sleep(2)
        
        logger.warning(f"[{self.name}] Response wait timeout, returning partial response")
        return last_response_text
    
    def extract_citation_title(self, link, page: Page = None) -> str:
        """
        Extract proper title for a citation link.
        
        Handles the common case where link text is just a reference marker like "[2]".
        """
        import re
        
        title = ""
        
        # 1. Try link text
        try:
            link_text = link.inner_text().strip()
            # Skip if text is just a citation marker
            if link_text and not re.match(r'^[\[\]\(\)\-\s\d]+$', link_text):
                if len(link_text) > 3:
                    title = link_text
        except:
            pass
        
        # 2. Try title attribute
        if not title:
            try:
                title = link.get_attribute("title") or ""
            except:
                pass
        
        # 3. Try aria-label
        if not title:
            try:
                title = link.get_attribute("aria-label") or ""
            except:
                pass
        
        # 4. Try parent element
        if not title:
            try:
                parent = link.query_selector("xpath=..")
                if parent:
                    parent_text = parent.inner_text().strip()
                    if parent_text and not re.match(r'^[\[\]\(\)\-\s\d]+$', parent_text):
                        lines = parent_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and len(line) > 5 and not re.match(r'^[\[\]\(\)\-\s\d]+$', line):
                                title = line[:200]
                                break
            except:
                pass
        
        # 5. Fall back to domain
        if not title:
            try:
                href = link.get_attribute("href")
                if href:
                    from urllib.parse import urlparse
                    title = urlparse(href).netloc
            except:
                pass
        
        return title[:200] if title else ""

    def navigate_with_challenge_handling(
        self,
        page,
        url: str,
        config: Optional[Dict[str, Any]] = None,
        wait_until: str = "domcontentloaded",
    ) -> bool:
        """
        Navigate to URL and handle any challenges.
        
        Args:
            page: Playwright page
            url: URL to navigate to
            config: Optional configuration
            wait_until: Playwright wait condition (default: domcontentloaded for challenge compatibility)
            
        Returns:
            True if navigation successful and challenges resolved
        """
        try:
            page.goto(url, wait_until=wait_until, timeout=60000)
            self.random_delay(2000, 4000)
            
            # Check for and handle challenges
            if not self.detect_and_handle_challenge(page, config):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[{self.name}] Navigation error: {e}")
            return False
    
    def take_screenshot_sync(self, page: Page, query: str) -> Optional[str]:
        """Take a screenshot of the page (sync version)."""
        try:
            screenshot_dir = getattr(settings, 'screenshot_dir', 'data/screenshots')
            os.makedirs(screenshot_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = "".join(c for c in query[:30] if c.isalnum() or c in " -_")
            filename = f"{self.name}_{safe_query}_{timestamp}.png"
            filepath = os.path.join(screenshot_dir, filename)
            
            page.screenshot(path=filepath, full_page=True)
            return filepath
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
            return None
    
    def random_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """Add random delay to simulate human behavior."""
        import time
        delay = random.uniform(min_ms / 1000, max_ms / 1000)
        time.sleep(delay)
    
    def type_slowly(self, page: Page, selector: str, text: str):
        """Type text slowly like a human."""
        import time
        element = page.locator(selector)
        element.click()
        for char in text:
            element.type(char, delay=random.uniform(50, 150))
            if random.random() < 0.1:  # 10% chance of pause
                time.sleep(random.uniform(0.1, 0.3))


class PerplexityLiteEngine(LiteEngineBase):
    """Perplexity AI crawler for lite mode (sync version)."""
    
    name = "perplexity"
    base_url = "https://www.perplexity.ai"
    
    # Multiple selector options for Perplexity's search input
    SEARCH_SELECTORS = [
        'textarea[placeholder*="Ask"]',
        'textarea[placeholder*="ask"]',
        'textarea[placeholder*="Search"]',
        'textarea[placeholder*="搜索"]',
        'textarea[placeholder*="anything"]',
        'textarea[autofocus]',
        '[data-testid="search-input"]',
        'textarea.grow',
        'div[contenteditable="true"]',
        'textarea',
    ]
    
    def crawl_sync(
        self,
        query: str,
        page: Page,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl Perplexity for a query (sync version)."""
        config = config or {}
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"[Perplexity] Navigating to {self.base_url}")
            # Use domcontentloaded instead of networkidle - Cloudflare pages keep network activity
            page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
            self.random_delay(3000, 5000)
            
            # Take diagnostic screenshot
            self.take_screenshot_sync(page, f"{query}_initial")
            
            # Check for Cloudflare or other challenges
            if not self.detect_and_handle_challenge(page, config):
                screenshot_path = self.take_screenshot_sync(page, f"{query}_challenge_failed")
                return {
                    "success": False,
                    "query": query,
                    "error": "无法通过验证挑战，请检查浏览器或使用有效会话",
                    "engine": self.name,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "screenshot_path": screenshot_path,
                }
            
            # Try multiple selectors to find search input
            logger.info("[Perplexity] Looking for search input...")
            input_element = None
            used_selector = None
            
            for selector in self.SEARCH_SELECTORS:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        input_element = element
                        used_selector = selector
                        logger.info(f"[Perplexity] Found input with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not input_element:
                # Take screenshot for debugging
                screenshot_path = self.take_screenshot_sync(page, f"{query}_no_input")
                page_text = page.inner_text("body")[:500]
                logger.error(f"[Perplexity] No input found. Page text: {page_text}")
                return {
                    "success": False,
                    "query": query,
                    "error": f"找不到搜索输入框。页面可能已更改或被阻止。",
                    "engine": self.name,
                    "screenshot_path": screenshot_path,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
            
            # Type query
            logger.info(f"[Perplexity] Typing query: {query[:30]}...")
            input_element.click()
            self.random_delay(500, 1000)
            input_element.fill(query)
            self.random_delay(500, 1000)
            
            # Take screenshot before submit
            self.take_screenshot_sync(page, f"{query}_before_submit")
            
            # Submit query
            logger.info("[Perplexity] Submitting query...")
            page.keyboard.press("Enter")
            
            # Wait for response with multiple selectors
            logger.info("[Perplexity] Waiting for response...")
            response_selectors = [
                '[class*="prose"]',
                '[class*="markdown"]',
                '[class*="response"]',
                '[class*="answer"]',
                '[class*="result"]',
                'article',
                'main [class*="text"]',
            ]
            
            # Poll for response
            response_found = False
            for _ in range(24):  # 120 seconds total
                self.random_delay(4000, 6000)
                
                for selector in response_selectors:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            # Check if any element has substantial content
                            for el in elements:
                                text = el.inner_text()
                                if text and len(text) > 100:
                                    response_found = True
                                    logger.info(f"[Perplexity] Response found with selector: {selector}")
                                    break
                    except Exception:
                        continue
                    if response_found:
                        break
                if response_found:
                    break
            
            if not response_found:
                screenshot_path = self.take_screenshot_sync(page, f"{query}_timeout")
                logger.error("[Perplexity] Timeout waiting for response")
                return {
                    "success": False,
                    "query": query,
                    "error": "等待响应超时",
                    "engine": self.name,
                    "screenshot_path": screenshot_path,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
            
            # Wait a bit more for response to fully render
            self.random_delay(2000, 3000)
            
            # Get page content
            html_content = page.content()
            
            # Parse response
            response_text = self._extract_response_sync(page)
            citations = self._extract_citations_sync(page)
            
            # Take final screenshot
            screenshot_path = self.take_screenshot_sync(page, query) if config.get("take_screenshot", True) else None
            
            elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            logger.info(f"[Perplexity] Success! Response length: {len(response_text)}")
            
            return {
                "success": True,
                "query": query,
                "response_text": response_text,
                "citations": citations,
                "raw_html": html_content[:50000] if html_content else "",
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "engine": self.name,
                "response_time_ms": elapsed_ms,
            }
        except Exception as e:
            logger.error(f"Perplexity crawl error: {e}")
            # Try to take error screenshot
            try:
                screenshot_path = self.take_screenshot_sync(page, f"{query}_error")
            except:
                screenshot_path = None
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "engine": self.name,
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def _extract_response_sync(self, page: Page) -> str:
        """Extract response text from page (sync)."""
        try:
            selectors = ['[class*="prose"]', '[class*="response"]', '[class*="answer"]', 'main']
            for selector in selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    texts = []
                    for el in elements[-2:]:
                        text = el.inner_text()
                        if text and len(text) > 50:
                            texts.append(text)
                    if texts:
                        return "\n\n".join(texts)
            return ""
        except Exception:
            return ""
    
    def _extract_citations_sync(self, page: Page) -> List[Dict]:
        """Extract citations from Perplexity page (sync)."""
        citations = []
        seen_urls = set()
        
        try:
            from urllib.parse import urlparse
            
            # Perplexity citation selectors
            citation_selectors = [
                '[class*="citation"] a',
                '[class*="source"] a',
                '[class*="reference"] a',
                '[class*="prose"] a[href^="http"]',
                '[data-testid*="source"] a',
            ]
            
            for selector in citation_selectors:
                try:
                    links = page.query_selector_all(selector)
                    for link in links[:30]:
                        href = link.get_attribute("href")
                        
                        if not href or not href.startswith("http"):
                            continue
                        if "perplexity.ai" in href:
                            continue
                        if href in seen_urls:
                            continue
                        
                        seen_urls.add(href)
                        title = self.extract_citation_title(link, page)
                        
                        try:
                            domain = urlparse(href).netloc
                        except:
                            domain = href
                        
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": title or domain,
                            "domain": domain,
                            "source": "perplexity",
                        })
                except:
                    continue
            
            if citations:
                logger.info(f"[Perplexity] Extracted {len(citations)} citations")
                
        except Exception as e:
            logger.warning(f"[Perplexity] Citation extraction error: {e}")
        
        return citations


class QwenLiteEngine(LiteEngineBase):
    """Qwen (通义千问) crawler for lite mode (sync version)."""
    
    name = "qwen"
    base_url = "https://tongyi.aliyun.com/qianwen"
    
    def _enable_web_search(self, page: Page) -> bool:
        """
        Enable web search mode in Qwen (通义千问).
        
        Qwen has a "联网搜索" toggle that enables real-time web search
        and provides citation sources in responses.
        """
        try:
            # Qwen-specific selectors for web search toggle
            search_toggle_selectors = [
                # Common toggle patterns
                'button[aria-label*="联网"]',
                'button[aria-label*="搜索"]',
                '[class*="search-toggle"]',
                '[class*="web-search"]',
                'button:has-text("联网搜索")',
                'button:has-text("联网")',
                # Qwen specific
                '[data-testid*="search"]',
                '[class*="internet"]',
                '[class*="online"]',
                # Toggle switch patterns
                '[role="switch"]',
                'input[type="checkbox"]',
                # Toolbar icons
                '[class*="toolbar"] button',
            ]
            
            for selector in search_toggle_selectors:
                try:
                    toggle = page.query_selector(selector)
                    if toggle and toggle.is_visible():
                        # Check if already enabled
                        is_enabled = (
                            toggle.get_attribute("aria-checked") == "true" or
                            toggle.get_attribute("data-state") == "checked" or
                            "active" in (toggle.get_attribute("class") or "") or
                            "selected" in (toggle.get_attribute("class") or "")
                        )
                        
                        if not is_enabled:
                            logger.info(f"[Qwen] Clicking web search toggle: {selector}")
                            toggle.click()
                            self.random_delay(500, 1000)
                            return True
                        else:
                            logger.info("[Qwen] Web search already enabled")
                            return True
                except Exception as e:
                    logger.debug(f"[Qwen] Toggle selector {selector} failed: {e}")
                    continue
            
            # Try clicking by text
            try:
                page.click('text=联网搜索', timeout=2000)
                self.random_delay(500, 1000)
                logger.info("[Qwen] Enabled web search via text click")
                return True
            except:
                pass
            
            logger.warning("[Qwen] Web search toggle not found")
            return False
            
        except Exception as e:
            logger.warning(f"[Qwen] Failed to enable web search: {e}")
            return False
    
    def _extract_citations_sync(self, page: Page) -> List[Dict]:
        """
        Extract citations from Qwen web search results.
        
        When web search is enabled, Qwen shows citation sources
        typically as numbered references or source cards.
        """
        citations = []
        seen_urls = set()
        
        try:
            from urllib.parse import urlparse
            
            # Qwen citation selectors
            citation_selectors = [
                # Source/reference sections
                '[class*="source"] a',
                '[class*="reference"] a',
                '[class*="citation"] a',
                '[class*="sources"] a',
                # Search result cards
                '[class*="search-result"] a',
                '[class*="result"] a[href^="http"]',
                # Link previews
                '[class*="link-preview"] a',
                '[class*="url"] a',
                # Footnotes
                '[class*="footnote"] a',
                # Generic external links in response
                '[class*="message"] a[href^="http"]',
                '[class*="answer"] a[href^="http"]',
                '[class*="content"] a[href^="http"]',
            ]
            
            for selector in citation_selectors:
                try:
                    links = page.query_selector_all(selector)
                    for link in links[:30]:
                        href = link.get_attribute("href")
                        
                        if not href or not href.startswith("http"):
                            continue
                        if "aliyun.com" in href or "tongyi" in href:
                            continue
                        if href in seen_urls:
                            continue
                        
                        seen_urls.add(href)
                        
                        # Use base class method for proper title extraction
                        title = self.extract_citation_title(link, page)
                        
                        try:
                            domain = urlparse(href).netloc
                        except:
                            domain = href
                        
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": title or domain,
                            "domain": domain,
                            "source": "qwen",
                        })
                except Exception as e:
                    logger.debug(f"[Qwen] Citation selector {selector} error: {e}")
                    continue
            
            if citations:
                logger.info(f"[Qwen] Extracted {len(citations)} citations")
            else:
                logger.debug("[Qwen] No citations found")
                
        except Exception as e:
            logger.warning(f"[Qwen] Citation extraction error: {e}")
        
        return citations
    
    def crawl_sync(
        self,
        query: str,
        page: Page,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl Qwen for a query (sync version)."""
        config = config or {}
        start_time = datetime.now(timezone.utc)
        
        try:
            page.goto(self.base_url)
            self.random_delay(2000, 4000)
            
            # Check for Cloudflare or other challenges
            if not self.detect_and_handle_challenge(page, config):
                screenshot_path = self.take_screenshot_sync(page, f"{query}_challenge_failed")
                return {
                    "success": False,
                    "query": query,
                    "error": "无法通过验证挑战",
                    "engine": self.name,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "screenshot_path": screenshot_path,
                }
            
            # Check for login requirement
            login_el = page.query_selector('[class*="login"], button:has-text("登录")')
            if login_el:
                return {
                    "success": False,
                    "query": query,
                    "error": "需要登录，请配置会话 cookie",
                    "engine": self.name,
                    "requires_login": True,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
            
            # Find search input
            search_selector = 'textarea, [contenteditable="true"], input[type="text"]'
            page.wait_for_selector(search_selector, timeout=15000)
            
            # Enable web search mode for citations
            web_search_enabled = self._enable_web_search(page)
            if web_search_enabled:
                logger.info("[Qwen] Web search mode enabled - citations will be available")
            
            # Type query
            self.type_slowly(page, search_selector, query)
            self.random_delay(500, 1000)
            
            # Submit
            btn = page.query_selector('button[type="submit"], button:has-text("发送"), [class*="send"]')
            if btn:
                btn.click()
            else:
                page.keyboard.press("Enter")
            
            # Wait for response
            self.random_delay(5000, 8000)
            
            html_content = page.content()
            response_text = self._extract_response_sync(page)
            
            # Extract citations if web search was enabled
            citations = self._extract_citations_sync(page)
            
            screenshot_path = self.take_screenshot_sync(page, query) if config.get("take_screenshot", True) else None
            
            elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            logger.info(f"[Qwen] Success! Response length: {len(response_text)}, citations: {len(citations)}")
            
            return {
                "success": True,
                "query": query,
                "response_text": response_text,
                "citations": citations,
                "raw_html": html_content[:50000] if html_content else "",
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "engine": self.name,
                "response_time_ms": elapsed_ms,
                "web_search_enabled": web_search_enabled,
            }
        except Exception as e:
            logger.error(f"Qwen crawl error: {e}")
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "engine": self.name,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def _extract_response_sync(self, page: Page) -> str:
        try:
            selectors = ['[class*="message"]', '[class*="response"]', '[class*="answer"]', '[class*="content"]']
            for selector in selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    for el in reversed(elements):
                        text = el.inner_text()
                        if text and len(text) > 50:
                            return text
            return ""
        except Exception:
            return ""


class DeepSeekLiteEngine(LiteEngineBase):
    """DeepSeek AI crawler for lite mode (sync version)."""
    
    name = "deepseek"
    base_url = "https://chat.deepseek.com"
    
    # Patterns that indicate AI is asking for clarification instead of answering
    CLARIFICATION_PATTERNS = [
        "请告诉我", "请问", "您可以告诉", "能告诉我", "想了解",
        "您的需求", "您的预算", "核心需求", "具体需求",
        "可以提供", "更多信息", "详细说明",
        "what would you like", "could you tell me", "what are your",
    ]
    
    # Follow-up response when AI asks clarifying questions
    FOLLOWUP_RESPONSE = "不需要更多信息，请直接给出完整的推荐和建议。"
    
    # Selectors for detecting if AI is still generating
    GENERATING_SELECTORS = [
        # Stop buttons (most reliable indicator)
        'button:has-text("停止")',
        'button:has-text("Stop")',
        'button:has-text("停止生成")',
        '[aria-label*="停止"]',
        '[aria-label*="Stop"]',
        # Loading/generating indicators (less reliable - might stay visible)
        '[class*="generating"]:not([class*="done"])',
        '[class*="streaming"]:not([class*="done"])',
        # Animation indicators
        '.animate-pulse',
        '[class*="cursor-blink"]',
        # DeepSeek specific thinking indicator
        '[class*="thinking"]:not([class*="done"])',
    ]
    
    def _is_still_generating(self, page: Page) -> bool:
        """Check if AI is still generating response."""
        # First check for explicit stop button - most reliable
        stop_selectors = [
            'button:has-text("停止")',
            'button:has-text("Stop")',
            '[aria-label*="停止"]',
        ]
        
        for selector in stop_selectors:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    logger.debug(f"[DeepSeek] Still generating (stop button visible: {selector})")
                    return True
            except:
                pass
        
        # Check other generating indicators (less reliable)
        for selector in self.GENERATING_SELECTORS:
            if selector in stop_selectors:
                continue  # Already checked
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    logger.debug(f"[DeepSeek] Still generating (found: {selector})")
                    return True
            except:
                pass
            
        return False
    
    def _wait_for_response_complete(self, page: Page, max_wait_seconds: int = 180) -> bool:
        """
        Wait for AI response to fully complete.
        
        Returns True if response completed, False if timeout.
        """
        import time
        start_time = time.time()
        last_response_text = ""
        last_response_length = 0
        stable_count = 0
        page_stable_count = 0
        
        logger.info("[DeepSeek] Waiting for response to complete...")
        
        while time.time() - start_time < max_wait_seconds:
            elapsed = int(time.time() - start_time)
            
            # Check if still generating (stop button visible)
            if self._is_still_generating(page):
                logger.debug(f"[DeepSeek] [{elapsed}s] Still generating...")
                time.sleep(3)
                stable_count = 0
                page_stable_count = 0
                continue
            
            # No generating indicator - page might be done
            page_stable_count += 1
            
            # Quick check: if citations exist and no generating, likely done
            if page_stable_count >= 3:  # After 6 seconds of no generating indicator
                citations = self._extract_citations_sync(page)
                if len(citations) > 0:
                    logger.info(f"[DeepSeek] [{elapsed}s] Found {len(citations)} citations, response appears complete")
                    return True
            
            # Try to extract text
            current_text = self._extract_response_sync(page)
            current_length = len(current_text)
            
            logger.debug(f"[DeepSeek] [{elapsed}s] Text length: {current_length}, stable: {page_stable_count}")
            
            # If we have text, check if it's stabilized
            if current_length > 50:
                if current_length > last_response_length + 10:
                    # Still growing
                    logger.debug(f"[DeepSeek] [{elapsed}s] Response growing: {last_response_length} -> {current_length}")
                    last_response_length = current_length
                    last_response_text = current_text
                    stable_count = 0
                elif current_text == last_response_text:
                    stable_count += 1
                    if stable_count >= 3:  # 6 seconds stable
                        logger.info(f"[DeepSeek] [{elapsed}s] Response stabilized with {current_length} chars")
                        return True
                else:
                    last_response_text = current_text
                    last_response_length = current_length
                    stable_count = 0
            
            # Fallback: after extended period with no generating indicator, assume done
            if page_stable_count >= 15:  # 30 seconds without generating indicator
                logger.info(f"[DeepSeek] [{elapsed}s] Page stable for {page_stable_count*2}s, assuming complete")
                return True
            
            time.sleep(2)
        
        logger.warning("[DeepSeek] Response wait timeout")
        return False
    
    def _needs_clarification(self, response_text: str) -> bool:
        """Check if AI is asking for clarification instead of answering."""
        response_lower = response_text.lower()
        for pattern in self.CLARIFICATION_PATTERNS:
            if pattern.lower() in response_lower:
                # Additional check: response should be relatively short (clarification questions are usually brief)
                if len(response_text) < 1000:
                    return True
        return False
    
    def _send_followup(self, page: Page, message: str) -> bool:
        """Send a follow-up message to continue the conversation."""
        try:
            # Find input field
            input_element = page.query_selector('textarea, [contenteditable="true"]')
            if not input_element:
                logger.warning("[DeepSeek] Cannot find input for follow-up")
                return False
            
            logger.info(f"[DeepSeek] Sending follow-up: {message[:30]}...")
            input_element.click()
            self.random_delay(300, 500)
            input_element.fill(message)
            self.random_delay(300, 500)
            
            # Submit
            btn = page.query_selector('button[type="submit"], button:has-text("发送")')
            if btn:
                btn.click()
            else:
                page.keyboard.press("Enter")
            
            return True
        except Exception as e:
            logger.error(f"[DeepSeek] Follow-up send error: {e}")
            return False
    
    def _enable_web_search(self, page: Page, enable: bool = True) -> bool:
        """
        Enable or disable web search mode in DeepSeek.
        
        DeepSeek has a "联网搜索" (Web Search) toggle that enables real-time
        web search and provides citation sources in responses.
        
        Note: When web search is enabled, responses take significantly longer
        as DeepSeek performs actual web searches before answering.
        
        Args:
            page: Playwright page instance
            enable: True to enable, False to ensure disabled
            
        Returns:
            True if web search is in desired state, False if toggle not found
        """
        try:
            # DeepSeek 2024/2025 UI uses these selectors for web search toggle
            # The toggle is typically in the input toolbar area
            search_toggle_selectors = [
                # DeepSeek specific selectors (most likely to work)
                '[class*="ds-icon-"] svg[class*="search"]',  # Icon class pattern
                'div[class*="toolbar"] button:has(svg)',
                '[class*="chat-input"] button:has(svg)',
                # Search toggle with specific patterns
                'button[class*="search"]',
                '[class*="search-btn"]',
                '[class*="web-search-toggle"]',
                # Toggle switches
                '[role="switch"]',
                '[class*="toggle"]',
                # Icon buttons in toolbar
                'button[aria-label*="联网"]',
                'button[aria-label*="搜索"]',
                'button[aria-label*="Search"]',
                'button[aria-label*="web"]',
                # Text based
                'button:has-text("联网")',
                'button:has-text("搜索")',
                # Tooltip based
                '[data-tooltip*="联网"]',
                '[title*="联网"]',
                '[title*="搜索"]',
            ]
            
            toggle_found = False
            for selector in search_toggle_selectors:
                try:
                    toggle = page.query_selector(selector)
                    if toggle and toggle.is_visible():
                        # Check current state
                        is_currently_enabled = (
                            toggle.get_attribute("aria-checked") == "true" or
                            toggle.get_attribute("data-state") == "checked" or
                            toggle.get_attribute("aria-pressed") == "true" or
                            "active" in (toggle.get_attribute("class") or "").lower() or
                            "enabled" in (toggle.get_attribute("class") or "").lower() or
                            "selected" in (toggle.get_attribute("class") or "").lower() or
                            "on" in (toggle.get_attribute("class") or "").lower()
                        )
                        
                        # Click if state needs to change
                        if enable and not is_currently_enabled:
                            logger.info(f"[DeepSeek] Enabling web search via: {selector}")
                            toggle.click()
                            self.random_delay(800, 1500)
                            toggle_found = True
                            break
                        elif not enable and is_currently_enabled:
                            logger.info(f"[DeepSeek] Disabling web search via: {selector}")
                            toggle.click()
                            self.random_delay(800, 1500)
                            toggle_found = True
                            break
                        elif enable and is_currently_enabled:
                            logger.info("[DeepSeek] Web search already enabled")
                            return True
                        elif not enable and not is_currently_enabled:
                            logger.info("[DeepSeek] Web search already disabled")
                            return True
                except Exception as e:
                    logger.debug(f"[DeepSeek] Selector {selector} failed: {e}")
                    continue
            
            if toggle_found:
                return True
                
            # Try clicking by text content as fallback
            try:
                if enable:
                    page.click('text=联网搜索', timeout=2000)
                    self.random_delay(800, 1500)
                    logger.info("[DeepSeek] Enabled web search via text click")
                    return True
            except:
                pass
            
            # If we get here, toggle wasn't found
            if enable:
                logger.warning("[DeepSeek] Web search toggle not found - proceeding WITHOUT web search")
            else:
                logger.info("[DeepSeek] Web search toggle not found - assuming disabled (good)")
            return not enable  # Return True if we wanted disabled anyway
            
        except Exception as e:
            logger.warning(f"[DeepSeek] Web search toggle error: {e}")
            return not enable
    
    def _extract_citations_sync(self, page: Page) -> List[Dict]:
        """
        Extract citations from DeepSeek web search results.
        
        When web search is enabled, DeepSeek shows citation sources
        typically as numbered references or link cards.
        """
        citations = []
        seen_urls = set()
        
        try:
            from urllib.parse import urlparse
            
            # DeepSeek citation selectors - search results usually appear as:
            # 1. Inline numbered citations [1], [2], etc.
            # 2. Source cards at the bottom
            # 3. Reference links in response
            citation_selectors = [
                # Source/reference sections (these often have better titles)
                '[class*="source"] a',
                '[class*="reference"] a',
                '[class*="citation"] a',
                '[class*="sources"] a',
                '[class*="refs"] a',
                # Search result cards
                '[class*="search-result"] a',
                '[class*="result-item"] a',
                '[class*="web-result"] a',
                # Link cards
                '[class*="link-card"] a',
                '[class*="url-card"] a',
                # Footnotes
                '[class*="footnote"] a',
                # Generic external links in response area (but not nav links)
                '[class*="markdown"] a[href^="http"]',
                '[class*="message"] a[href^="http"]',
                '[class*="prose"] a[href^="http"]',
            ]
            
            for selector in citation_selectors:
                try:
                    links = page.query_selector_all(selector)
                    for link in links[:30]:  # Limit to prevent too many
                        href = link.get_attribute("href")
                        
                        # Skip internal/invalid links
                        if not href or not href.startswith("http"):
                            continue
                        if "deepseek.com" in href:  # Skip internal links
                            continue
                        if href in seen_urls:
                            continue
                        
                        seen_urls.add(href)
                        
                        # Get title - try multiple approaches
                        title = ""
                        
                        # 1. Try to get title from link text
                        link_text = link.inner_text().strip()
                        
                        # Skip if link text is just a number or bracket reference like "[2]", "2", "- 2"
                        if link_text and not self._is_citation_marker(link_text):
                            title = link_text
                        
                        # 2. Try to get title from title attribute
                        if not title:
                            title = link.get_attribute("title") or ""
                        
                        # 3. Try to get title from aria-label
                        if not title:
                            title = link.get_attribute("aria-label") or ""
                        
                        # 4. Try to get title from parent or nearby element
                        if not title:
                            try:
                                parent = link.query_selector("xpath=..")
                                if parent:
                                    parent_text = parent.inner_text().strip()
                                    # Take first line or reasonable portion
                                    if parent_text and not self._is_citation_marker(parent_text):
                                        lines = parent_text.split('\n')
                                        for line in lines:
                                            line = line.strip()
                                            if line and len(line) > 5 and not self._is_citation_marker(line):
                                                title = line
                                                break
                            except:
                                pass
                        
                        # 5. Extract domain as fallback title
                        try:
                            domain = urlparse(href).netloc
                        except:
                            domain = href
                        
                        if not title:
                            title = domain
                        
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": title[:200] if title else domain,
                            "domain": domain,
                            "source": "deepseek",
                        })
                except Exception as e:
                    logger.debug(f"[DeepSeek] Citation selector {selector} error: {e}")
                    continue
            
            if citations:
                logger.info(f"[DeepSeek] Extracted {len(citations)} citations")
            else:
                logger.debug("[DeepSeek] No citations found")
                
        except Exception as e:
            logger.warning(f"[DeepSeek] Citation extraction error: {e}")
        
        return citations
    
    def _is_citation_marker(self, text: str) -> bool:
        """Check if text is just a citation marker like '[2]', '2', '- 2', etc."""
        import re
        text = text.strip()
        # Empty or very short
        if not text or len(text) <= 3:
            return True
        # Just numbers, brackets, dashes
        if re.match(r'^[\[\]\(\)\-\s\d]+$', text):
            return True
        # Looks like "[1]" or "(2)" etc
        if re.match(r'^\[?\(?\d+\)?\]?$', text):
            return True
        return False
    
    def _extract_response_sync(self, page: Page) -> str:
        """Extract response text from DeepSeek page."""
        try:
            # DeepSeek-specific selectors for response content
            selectors = [
                '[class*="ds-markdown"]',  # DeepSeek uses ds-markdown
                '[class*="markdown-body"]',
                '[class*="message-content"]',
                '[class*="prose"]',
                '[class*="response"]',
                '[class*="answer-content"]',
            ]
            
            for selector in selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        # Get the last message elements (AI responses)
                        texts = []
                        for el in elements[-3:]:  # Check last 3 elements
                            try:
                                text = el.inner_text()
                                if text and len(text) > 30:
                                    # Skip if it's the user's query
                                    if not text.strip().startswith("直接回答"):
                                        texts.append(text)
                            except:
                                continue
                        
                        if texts:
                            # Return the longest response (usually the main AI answer)
                            return max(texts, key=len)
                except:
                    continue
            
            # Fallback: try to find any markdown content
            try:
                main_content = page.query_selector('main, [role="main"], #app')
                if main_content:
                    text = main_content.inner_text()
                    if text and len(text) > 50:
                        return text
            except:
                pass
            
            return ""
        except Exception as e:
            logger.error(f"[DeepSeek] Response extraction error: {e}")
            return ""
    
    def crawl_sync(
        self,
        query: str,
        page: Page,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl DeepSeek for a query (sync version).
        
        Config options:
            - max_turns: Maximum conversation turns (default: 2)
            - enable_web_search: Whether to enable web search mode (default: False for stability)
            - max_wait_seconds: Max wait time for response (default: 120, 180 if web search enabled)
            - take_screenshot: Whether to take screenshots (default: True)
        """
        config = config or {}
        start_time = datetime.now(timezone.utc)
        max_turns = config.get("max_turns", 2)
        # Default to True to get citation sources (core feature)
        enable_web_search = config.get("enable_web_search", True)
        
        try:
            logger.info(f"[DeepSeek] Navigating to {self.base_url}")
            page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
            self.random_delay(3000, 5000)
            
            # Check for Cloudflare or other challenges
            if not self.detect_and_handle_challenge(page, config):
                screenshot_path = self.take_screenshot_sync(page, f"{query}_challenge_failed")
                return {
                    "success": False,
                    "query": query,
                    "error": "无法通过验证挑战",
                    "engine": self.name,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "screenshot_path": screenshot_path,
                }
            
            # Take screenshot of initial page
            self.take_screenshot_sync(page, f"{query}_initial")
            
            # Check for login requirement
            page_text = page.inner_text("body")
            login_indicators = ["登录", "Sign in", "Login", "注册", "Sign up"]
            needs_login = any(ind in page_text for ind in login_indicators)
            
            login_el = page.query_selector('button:has-text("登录"), a:has-text("登录"), button:has-text("Sign in")')
            if login_el or needs_login:
                input_el = page.query_selector('textarea, [contenteditable="true"]')
                if not input_el:
                    screenshot_path = self.take_screenshot_sync(page, f"{query}_login_required")
                    logger.warning("[DeepSeek] Login required - no input field found")
                    return {
                        "success": False,
                        "query": query,
                        "error": "登录要求: DeepSeek 需要登录才能使用",
                        "engine": self.name,
                        "requires_login": True,
                        "screenshot_path": screenshot_path,
                        "crawled_at": datetime.now(timezone.utc).isoformat(),
                    }
            
            # Find input field
            logger.info("[DeepSeek] Looking for input field")
            input_element = page.query_selector('textarea, [contenteditable="true"]')
            
            if not input_element:
                screenshot_path = self.take_screenshot_sync(page, f"{query}_no_input")
                logger.error("[DeepSeek] No input field found")
                return {
                    "success": False,
                    "query": query,
                    "error": "找不到输入框。页面可能需要登录或结构已变化。",
                    "engine": self.name,
                    "screenshot_path": screenshot_path,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
            
            # Handle web search mode based on config
            web_search_enabled = False
            if enable_web_search:
                logger.info("[DeepSeek] Attempting to enable web search mode...")
                web_search_enabled = self._enable_web_search(page, enable=True)
                if web_search_enabled:
                    logger.info("[DeepSeek] Web search mode ENABLED - citations will be available")
                else:
                    logger.warning("[DeepSeek] Could not find web search toggle - proceeding without it")
            else:
                logger.info("[DeepSeek] Skipping web search toggle (disabled in config)")
            
            # Format query to discourage clarifying questions
            formatted_query = f"直接回答以下问题，不要询问更多信息，给出完整建议：{query}"
            
            # Type query
            logger.info(f"[DeepSeek] Typing query: {query[:30]}...")
            input_element.click()
            self.random_delay(500, 1000)
            input_element.fill(formatted_query)
            self.random_delay(500, 1000)
            
            self.take_screenshot_sync(page, f"{query}_before_submit")
            
            # Submit
            logger.info("[DeepSeek] Submitting query")
            btn = page.query_selector('button[type="submit"], button:has-text("发送")')
            if btn:
                btn.click()
            else:
                page.keyboard.press("Enter")
            
            # Wait for initial response
            self.random_delay(5000, 8000)
            
            # Multi-turn conversation loop
            turn = 0
            final_response = ""
            
            # Determine max wait time based on web search mode
            max_wait = config.get("max_wait_seconds", 180 if web_search_enabled else 120)
            
            while turn < max_turns:
                turn += 1
                logger.info(f"[DeepSeek] Turn {turn}/{max_turns} (web_search={web_search_enabled})")
                
                # Wait for response to complete - longer timeout if web search is enabled
                if not self._wait_for_response_complete(page, max_wait_seconds=max_wait):
                    logger.warning(f"[DeepSeek] Turn {turn} response timeout (waited {max_wait}s)")
                    break
                
                # Extract response
                response_text = self._extract_response_sync(page)
                
                if not response_text or len(response_text) < 20:
                    logger.warning(f"[DeepSeek] Turn {turn} no valid response")
                    break
                
                # Check if AI is asking for clarification
                if self._needs_clarification(response_text):
                    logger.info(f"[DeepSeek] Turn {turn} AI asking for clarification, sending follow-up...")
                    self.take_screenshot_sync(page, f"{query}_clarification_t{turn}")
                    
                    if turn >= max_turns:
                        logger.warning("[DeepSeek] Max turns reached, accepting partial response")
                        final_response = response_text
                        break
                    
                    # Send follow-up
                    if not self._send_followup(page, self.FOLLOWUP_RESPONSE):
                        final_response = response_text
                        break
                    
                    self.random_delay(3000, 5000)
                    continue
                else:
                    # Got a real answer
                    final_response = response_text
                    logger.info(f"[DeepSeek] Turn {turn} got complete response ({len(response_text)} chars)")
                    break
            
            # Final screenshot and result
            html_content = page.content()
            screenshot_path = self.take_screenshot_sync(page, query) if config.get("take_screenshot", True) else None
            
            # Extract citations
            citations = self._extract_citations_sync(page)
            
            # If text extraction failed but we have citations, try one more time with the full page
            if len(final_response) < 50 and len(citations) > 0:
                logger.info("[DeepSeek] Text extraction failed but citations found, trying full page extraction...")
                try:
                    # Try getting text from body directly
                    body_text = page.evaluate("() => document.body.innerText")
                    if body_text and len(body_text) > 200:
                        # Clean up the text
                        lines = body_text.split('\n')
                        # Find content area (skip sidebar, header)
                        content_lines = []
                        in_content = False
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            # Start capturing after seeing substantial Chinese text
                            if len(line) > 30 and any('\u4e00' <= c <= '\u9fff' for c in line):
                                in_content = True
                            if in_content:
                                # Stop at input area
                                if '给 DeepSeek 发送消息' in line or '深度思考' in line:
                                    break
                                content_lines.append(line)
                        
                        if content_lines:
                            final_response = '\n'.join(content_lines[:50])  # Limit to reasonable size
                            logger.info(f"[DeepSeek] Recovered {len(final_response)} chars from page body")
                except Exception as e:
                    logger.warning(f"[DeepSeek] Page body extraction failed: {e}")
            
            elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Success if we have substantial text OR citations (citations are more important for GEO)
            success = len(final_response) > 50 or len(citations) > 0
            logger.info(f"[DeepSeek] {'SUCCESS' if success else 'FAILED'}! Response: {len(final_response)} chars, Citations: {len(citations)}")
            
            return {
                "success": success,
                "query": query,
                "response_text": final_response,
                "citations": citations,
                "raw_html": html_content[:50000] if html_content else "",
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "engine": self.name,
                "response_time_ms": elapsed_ms,
                "turns": turn,
                "web_search_enabled": web_search_enabled,
            }
        except Exception as e:
            logger.error(f"DeepSeek crawl error: {e}")
            try:
                screenshot_path = self.take_screenshot_sync(page, f"{query}_error")
            except:
                screenshot_path = None
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "engine": self.name,
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def _extract_response_sync(self, page: Page) -> str:
        """Extract response text from DeepSeek page using JavaScript."""
        try:
            # Use JavaScript to extract text - more reliable for CSS module hashed classes
            # DeepSeek's response area can be identified by its position and content structure
            js_extract = """
            () => {
                // Strategy 1: Find the main content area (right side of the chat)
                // DeepSeek typically has a sidebar on left and main content on right
                const mainContent = document.querySelector('[role="main"]') || 
                                   document.querySelector('main') ||
                                   document.querySelector('[class*="main"]');
                
                if (mainContent) {
                    // Look for the last substantial text block (AI response)
                    const allText = mainContent.innerText;
                    if (allText && allText.length > 100) {
                        // Clean up: remove common UI elements
                        let cleaned = allText;
                        // Remove the input area text at the bottom
                        const inputIdx = cleaned.indexOf('给 DeepSeek 发送消息');
                        if (inputIdx > 0) {
                            cleaned = cleaned.substring(0, inputIdx);
                        }
                        // Remove sidebar content
                        const sidebarIdx = cleaned.indexOf('开启新对话');
                        if (sidebarIdx === 0) {
                            // Find where sidebar ends (look for actual content)
                            const contentStart = cleaned.search(/[一-龥]{10,}/);
                            if (contentStart > 0) {
                                cleaned = cleaned.substring(contentStart);
                            }
                        }
                        return cleaned.trim();
                    }
                }
                
                // Strategy 2: Find response by looking for elements with substantial Chinese text
                const allDivs = document.querySelectorAll('div');
                let bestMatch = '';
                let bestLength = 0;
                
                for (const div of allDivs) {
                    const text = div.innerText;
                    // Look for divs with substantial content (likely response)
                    if (text && text.length > 200 && text.length < 50000) {
                        // Prefer content with Chinese characters and bullet points
                        const chineseCount = (text.match(/[一-龥]/g) || []).length;
                        const hasBullets = text.includes('•') || text.includes('·');
                        const score = chineseCount + (hasBullets ? 500 : 0);
                        
                        if (score > bestLength) {
                            bestLength = score;
                            bestMatch = text;
                        }
                    }
                }
                
                if (bestMatch) {
                    // Clean up UI elements
                    let cleaned = bestMatch;
                    const inputIdx = cleaned.indexOf('给 DeepSeek 发送消息');
                    if (inputIdx > 0) {
                        cleaned = cleaned.substring(0, inputIdx);
                    }
                    return cleaned.trim();
                }
                
                return '';
            }
            """
            
            result = page.evaluate(js_extract)
            if result and len(result) > 50:
                logger.debug(f"[DeepSeek] Extracted response via JS, length: {len(result)}")
                return result
            
            # Fallback: Try CSS selectors (in case DeepSeek changes back to normal classes)
            selectors = [
                '[class*="markdown"]',
                '[class*="prose"]',
                '[class*="message"]',
                '[class*="content"]',
                'main',
            ]
            
            for selector in selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for el in reversed(elements or []):
                        try:
                            text = el.inner_text()
                            if text and len(text) > 100:
                                if '给 DeepSeek 发送消息' not in text[:50]:
                                    logger.debug(f"[DeepSeek] Found via selector: {selector}")
                                    return text.strip()
                        except:
                            continue
                except:
                    continue
            
            logger.warning("[DeepSeek] Could not extract response text")
            return ""
        except Exception as e:
            logger.error(f"[DeepSeek] Response extraction error: {e}")
            return ""


class KimiLiteEngine(LiteEngineBase):
    """Kimi AI crawler for lite mode (sync version)."""
    
    name = "kimi"
    base_url = "https://kimi.moonshot.cn"
    
    # Kimi-specific generating selectors
    KIMI_GENERATING_SELECTORS = [
        'button:has-text("停止")',
        '[class*="loading"]',
        '[class*="generating"]',
        '[class*="typing"]',
    ]
    
    def crawl_sync(
        self,
        query: str,
        page: Page,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl Kimi for a query (sync version)."""
        config = config or {}
        start_time = datetime.now(timezone.utc)
        
        try:
            page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
            self.random_delay(3000, 5000)
            
            # Check for Cloudflare or other challenges
            if not self.detect_and_handle_challenge(page, config):
                screenshot_path = self.take_screenshot_sync(page, f"{query}_challenge_failed")
                return {
                    "success": False,
                    "query": query,
                    "error": "无法通过验证挑战",
                    "engine": self.name,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "screenshot_path": screenshot_path,
                }
            
            self.take_screenshot_sync(page, f"{query}_initial")
            
            # Find input
            search_selector = 'textarea, [contenteditable="true"]'
            page.wait_for_selector(search_selector, timeout=15000)
            
            self.type_slowly(page, search_selector, query)
            self.random_delay(500, 1000)
            
            # Submit
            btn = page.query_selector('button[type="submit"], button:has-text("发送")')
            if btn:
                btn.click()
            else:
                page.keyboard.press("Enter")
            
            # Wait for initial response
            self.random_delay(3000, 5000)
            page.wait_for_selector('[class*="markdown"], [class*="message"]', timeout=60000)
            
            # Wait for response to fully complete
            response_text = self.wait_for_response_complete(
                page,
                self._extract_response_sync,
                max_wait_seconds=120,
                extra_generating_selectors=self.KIMI_GENERATING_SELECTORS,
            )
            
            html_content = page.content()
            citations = self._extract_citations_sync(page)
            screenshot_path = self.take_screenshot_sync(page, query) if config.get("take_screenshot", True) else None
            
            elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            success = len(response_text) > 50
            logger.info(f"[Kimi] {'Success' if success else 'Failed'}! Response: {len(response_text)} chars, citations: {len(citations)}")
            
            return {
                "success": success,
                "query": query,
                "response_text": response_text,
                "citations": citations,
                "raw_html": html_content[:50000] if html_content else "",
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "engine": self.name,
                "response_time_ms": elapsed_ms,
            }
        except Exception as e:
            logger.error(f"Kimi crawl error: {e}")
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "engine": self.name,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def _extract_response_sync(self, page: Page) -> str:
        try:
            selectors = ['[class*="markdown"]', '[class*="message-content"]', '[class*="response"]', '[class*="answer"]']
            for selector in selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    texts = []
                    for el in elements[-3:]:
                        try:
                            text = el.inner_text()
                            if text and len(text) > 30:
                                texts.append(text)
                        except:
                            continue
                    if texts:
                        return max(texts, key=len)
            return ""
        except Exception:
            return ""
    
    def _extract_citations_sync(self, page: Page) -> List[Dict]:
        citations = []
        seen_urls = set()
        
        try:
            from urllib.parse import urlparse
            
            # Kimi citation selectors
            citation_selectors = [
                '[class*="source"] a',
                '[class*="reference"] a',
                '[class*="citation"] a',
                '[class*="link-card"] a',
                '[class*="markdown"] a[href^="http"]',
            ]
            
            for selector in citation_selectors:
                try:
                    links = page.query_selector_all(selector)
                    for link in links[:30]:
                        href = link.get_attribute("href")
                        
                        if not href or not href.startswith("http"):
                            continue
                        if "kimi.moonshot" in href or "moonshot.cn" in href:
                            continue
                        if href in seen_urls:
                            continue
                        
                        seen_urls.add(href)
                        title = self.extract_citation_title(link, page)
                        
                        try:
                            domain = urlparse(href).netloc
                        except:
                            domain = href
                        
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": title or domain,
                            "domain": domain,
                            "source": "kimi",
                        })
                except:
                    continue
            
            if citations:
                logger.info(f"[Kimi] Extracted {len(citations)} citations")
                
        except Exception as e:
            logger.warning(f"[Kimi] Citation extraction error: {e}")
        
        return citations


class ChatGPTLiteEngine(LiteEngineBase):
    """ChatGPT crawler for lite mode (sync version)."""
    
    name = "chatgpt"
    base_url = "https://chatgpt.com"
    
    def crawl_sync(
        self,
        query: str,
        page: Page,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl ChatGPT for a query (sync version)."""
        config = config or {}
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"[ChatGPT] Navigating to {self.base_url}")
            page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
            self.random_delay(3000, 5000)
            
            # Check for Cloudflare or other challenges
            if not self.detect_and_handle_challenge(page, config):
                screenshot_path = self.take_screenshot_sync(page, f"{query}_challenge_failed")
                return {
                    "success": False,
                    "query": query,
                    "error": "无法通过验证挑战",
                    "engine": self.name,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "screenshot_path": screenshot_path,
                }
            
            self.take_screenshot_sync(page, f"{query}_initial")
            
            # Check for login requirement
            page_text = page.inner_text("body")
            login_indicators = ["Log in", "Sign up", "登录", "注册", "Welcome to ChatGPT"]
            
            # Look for the prompt input field
            input_selectors = [
                '#prompt-textarea',
                'textarea[data-id="root"]',
                'textarea[placeholder*="Message"]',
                'textarea[placeholder*="消息"]',
                'textarea',
                '[contenteditable="true"]',
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = page.query_selector(selector)
                    if input_element and input_element.is_visible():
                        break
                except:
                    continue
            
            if not input_element:
                # Check if login is required
                if any(ind in page_text for ind in login_indicators):
                    screenshot_path = self.take_screenshot_sync(page, f"{query}_login_required")
                    return {
                        "success": False,
                        "query": query,
                        "error": "登录要求: ChatGPT 需要登录才能使用",
                        "engine": self.name,
                        "requires_login": True,
                        "screenshot_path": screenshot_path,
                        "crawled_at": datetime.now(timezone.utc).isoformat(),
                    }
                
                screenshot_path = self.take_screenshot_sync(page, f"{query}_no_input")
                return {
                    "success": False,
                    "query": query,
                    "error": "找不到输入框",
                    "engine": self.name,
                    "screenshot_path": screenshot_path,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
            
            # Type query
            logger.info(f"[ChatGPT] Typing query: {query[:30]}...")
            input_element.click()
            self.random_delay(300, 500)
            input_element.fill(query)
            self.random_delay(500, 1000)
            
            # Submit
            logger.info("[ChatGPT] Submitting query")
            submit_btn = page.query_selector('button[data-testid="send-button"], button[aria-label*="Send"], button:has-text("发送")')
            if submit_btn:
                submit_btn.click()
            else:
                page.keyboard.press("Enter")
            
            # Wait for response
            self.random_delay(5000, 8000)
            
            # Wait for response to complete (check for stop button)
            max_wait = 120
            start_wait = datetime.now(timezone.utc)
            while (datetime.now(timezone.utc) - start_wait).seconds < max_wait:
                stop_btn = page.query_selector('button[aria-label*="Stop"], button:has-text("Stop")')
                if not stop_btn or not stop_btn.is_visible():
                    break
                self.random_delay(2000, 3000)
            
            html_content = page.content()
            response_text = self._extract_response_sync(page)
            citations = self._extract_citations_sync(page)
            screenshot_path = self.take_screenshot_sync(page, query) if config.get("take_screenshot", True) else None
            
            elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            success = len(response_text) > 50
            logger.info(f"[ChatGPT] {'Success' if success else 'Failed'}! Response length: {len(response_text)}")
            
            return {
                "success": success,
                "query": query,
                "response_text": response_text,
                "citations": citations,
                "raw_html": html_content[:50000] if html_content else "",
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "engine": self.name,
                "response_time_ms": elapsed_ms,
            }
        except Exception as e:
            logger.error(f"ChatGPT crawl error: {e}")
            try:
                screenshot_path = self.take_screenshot_sync(page, f"{query}_error")
            except:
                screenshot_path = None
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "engine": self.name,
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def _extract_response_sync(self, page: Page) -> str:
        try:
            selectors = [
                '[data-message-author-role="assistant"]',
                '[class*="markdown"]',
                '[class*="prose"]',
                '[class*="message-content"]',
                '[class*="response"]',
            ]
            for selector in selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    for el in reversed(elements):
                        text = el.inner_text()
                        if text and len(text) > 50:
                            return text
            return ""
        except Exception:
            return ""
    
    def _extract_citations_sync(self, page: Page) -> List[Dict]:
        """ChatGPT typically doesn't provide citations, but extract any links."""
        citations = []
        try:
            links = page.query_selector_all('[data-message-author-role="assistant"] a[href^="http"]')
            seen_urls = set()
            for link in links[:20]:
                href = link.get_attribute("href")
                title = link.inner_text()
                if href and href.startswith("http") and href not in seen_urls:
                    if "openai.com" not in href:
                        seen_urls.add(href)
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": title[:200] if title else "",
                            "source": "chatgpt",
                        })
        except Exception:
            pass
        return citations


class DoubaoLiteEngine(LiteEngineBase):
    """豆包 (Doubao) crawler for lite mode (sync version)."""
    
    name = "doubao"
    base_url = "https://www.doubao.com/chat"
    
    def crawl_sync(
        self,
        query: str,
        page: Page,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl Doubao for a query (sync version)."""
        config = config or {}
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"[Doubao] Navigating to {self.base_url}")
            page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
            self.random_delay(3000, 5000)
            
            # Check for challenges
            if not self.detect_and_handle_challenge(page, config):
                screenshot_path = self.take_screenshot_sync(page, f"{query}_challenge_failed")
                return {
                    "success": False,
                    "query": query,
                    "error": "无法通过验证挑战",
                    "engine": self.name,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "screenshot_path": screenshot_path,
                }
            
            self.take_screenshot_sync(page, f"{query}_initial")
            
            # Check for login requirement
            page_text = page.inner_text("body")
            login_indicators = ["登录", "注册", "Login", "Sign"]
            
            # Find input field
            input_selectors = [
                'textarea[placeholder*="输入"]',
                'textarea[placeholder*="问"]',
                'textarea',
                '[contenteditable="true"]',
                'input[type="text"]',
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = page.query_selector(selector)
                    if input_element and input_element.is_visible():
                        break
                except:
                    continue
            
            if not input_element:
                if any(ind in page_text for ind in login_indicators):
                    screenshot_path = self.take_screenshot_sync(page, f"{query}_login_required")
                    return {
                        "success": False,
                        "query": query,
                        "error": "登录要求: 豆包需要登录才能使用",
                        "engine": self.name,
                        "requires_login": True,
                        "screenshot_path": screenshot_path,
                        "crawled_at": datetime.now(timezone.utc).isoformat(),
                    }
                
                screenshot_path = self.take_screenshot_sync(page, f"{query}_no_input")
                return {
                    "success": False,
                    "query": query,
                    "error": "找不到输入框",
                    "engine": self.name,
                    "screenshot_path": screenshot_path,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
            
            # Type query
            logger.info(f"[Doubao] Typing query: {query[:30]}...")
            input_element.click()
            self.random_delay(300, 500)
            input_element.fill(query)
            self.random_delay(500, 1000)
            
            # Submit
            logger.info("[Doubao] Submitting query")
            submit_btn = page.query_selector('button[type="submit"], button:has-text("发送"), [class*="send"]')
            if submit_btn:
                submit_btn.click()
            else:
                page.keyboard.press("Enter")
            
            # Wait for response
            self.random_delay(5000, 10000)
            
            # Wait for completion
            max_wait = 90
            start_wait = datetime.now(timezone.utc)
            last_text = ""
            stable_count = 0
            
            while (datetime.now(timezone.utc) - start_wait).seconds < max_wait:
                current_text = self._extract_response_sync(page)
                if current_text == last_text and len(current_text) > 50:
                    stable_count += 1
                    if stable_count >= 3:
                        break
                else:
                    stable_count = 0
                    last_text = current_text
                self.random_delay(2000, 3000)
            
            html_content = page.content()
            response_text = self._extract_response_sync(page)
            citations = self._extract_citations_sync(page)
            screenshot_path = self.take_screenshot_sync(page, query) if config.get("take_screenshot", True) else None
            
            elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            success = len(response_text) > 50
            logger.info(f"[Doubao] {'Success' if success else 'Failed'}! Response length: {len(response_text)}")
            
            return {
                "success": success,
                "query": query,
                "response_text": response_text,
                "citations": citations,
                "raw_html": html_content[:50000] if html_content else "",
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "engine": self.name,
                "response_time_ms": elapsed_ms,
            }
        except Exception as e:
            logger.error(f"Doubao crawl error: {e}")
            try:
                screenshot_path = self.take_screenshot_sync(page, f"{query}_error")
            except:
                screenshot_path = None
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "engine": self.name,
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def _extract_response_sync(self, page: Page) -> str:
        try:
            selectors = [
                '[class*="message-content"]',
                '[class*="markdown"]',
                '[class*="response"]',
                '[class*="answer"]',
                '[class*="bot-message"]',
            ]
            for selector in selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    for el in reversed(elements):
                        text = el.inner_text()
                        if text and len(text) > 50:
                            return text
            return ""
        except Exception:
            return ""
    
    def _extract_citations_sync(self, page: Page) -> List[Dict]:
        """Doubao is conversational AI, typically no citations."""
        return []


class ChatGLMLiteEngine(LiteEngineBase):
    """ChatGLM (智谱清言) crawler for lite mode (sync version)."""
    
    name = "chatglm"
    base_url = "https://chatglm.cn"
    
    def crawl_sync(
        self,
        query: str,
        page: Page,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl ChatGLM for a query (sync version)."""
        config = config or {}
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"[ChatGLM] Navigating to {self.base_url}")
            page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
            self.random_delay(3000, 5000)
            
            # Check for challenges
            if not self.detect_and_handle_challenge(page, config):
                screenshot_path = self.take_screenshot_sync(page, f"{query}_challenge_failed")
                return {
                    "success": False,
                    "query": query,
                    "error": "无法通过验证挑战",
                    "engine": self.name,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "screenshot_path": screenshot_path,
                }
            
            self.take_screenshot_sync(page, f"{query}_initial")
            
            # Check for login
            page_text = page.inner_text("body")
            login_indicators = ["登录", "注册", "Login", "Sign in"]
            
            # Find input field
            input_selectors = [
                'textarea[placeholder*="输入"]',
                'textarea[placeholder*="问"]',
                'textarea',
                '[contenteditable="true"]',
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = page.query_selector(selector)
                    if input_element and input_element.is_visible():
                        break
                except:
                    continue
            
            if not input_element:
                if any(ind in page_text for ind in login_indicators):
                    screenshot_path = self.take_screenshot_sync(page, f"{query}_login_required")
                    return {
                        "success": False,
                        "query": query,
                        "error": "登录要求: 智谱清言需要登录才能使用",
                        "engine": self.name,
                        "requires_login": True,
                        "screenshot_path": screenshot_path,
                        "crawled_at": datetime.now(timezone.utc).isoformat(),
                    }
                
                screenshot_path = self.take_screenshot_sync(page, f"{query}_no_input")
                return {
                    "success": False,
                    "query": query,
                    "error": "找不到输入框",
                    "engine": self.name,
                    "screenshot_path": screenshot_path,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
            
            # Type query
            logger.info(f"[ChatGLM] Typing query: {query[:30]}...")
            input_element.click()
            self.random_delay(300, 500)
            input_element.fill(query)
            self.random_delay(500, 1000)
            
            # Submit
            logger.info("[ChatGLM] Submitting query")
            submit_btn = page.query_selector('button[type="submit"], button:has-text("发送"), [class*="send"]')
            if submit_btn:
                submit_btn.click()
            else:
                page.keyboard.press("Enter")
            
            # Wait for response
            self.random_delay(5000, 10000)
            
            # Wait for completion
            max_wait = 90
            start_wait = datetime.now(timezone.utc)
            last_text = ""
            stable_count = 0
            
            while (datetime.now(timezone.utc) - start_wait).seconds < max_wait:
                current_text = self._extract_response_sync(page)
                if current_text == last_text and len(current_text) > 50:
                    stable_count += 1
                    if stable_count >= 3:
                        break
                else:
                    stable_count = 0
                    last_text = current_text
                self.random_delay(2000, 3000)
            
            html_content = page.content()
            response_text = self._extract_response_sync(page)
            citations = self._extract_citations_sync(page)
            screenshot_path = self.take_screenshot_sync(page, query) if config.get("take_screenshot", True) else None
            
            elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            success = len(response_text) > 50
            logger.info(f"[ChatGLM] {'Success' if success else 'Failed'}! Response length: {len(response_text)}")
            
            return {
                "success": success,
                "query": query,
                "response_text": response_text,
                "citations": citations,
                "raw_html": html_content[:50000] if html_content else "",
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "engine": self.name,
                "response_time_ms": elapsed_ms,
            }
        except Exception as e:
            logger.error(f"ChatGLM crawl error: {e}")
            try:
                screenshot_path = self.take_screenshot_sync(page, f"{query}_error")
            except:
                screenshot_path = None
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "engine": self.name,
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def _extract_response_sync(self, page: Page) -> str:
        try:
            selectors = [
                '[class*="message-content"]',
                '[class*="markdown"]',
                '[class*="prose"]',
                '[class*="response"]',
                '[class*="answer"]',
            ]
            for selector in selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    for el in reversed(elements):
                        text = el.inner_text()
                        if text and len(text) > 50:
                            return text
            return ""
        except Exception:
            return ""
    
    def _extract_citations_sync(self, page: Page) -> List[Dict]:
        """ChatGLM is conversational AI, typically no citations."""
        citations = []
        try:
            links = page.query_selector_all('[class*="message"] a[href^="http"], [class*="markdown"] a[href^="http"]')
            seen_urls = set()
            for link in links[:20]:
                href = link.get_attribute("href")
                title = link.inner_text()
                if href and href.startswith("http") and href not in seen_urls:
                    if "chatglm" not in href and "zhipu" not in href:
                        seen_urls.add(href)
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": title[:200] if title else "",
                            "source": "chatglm",
                        })
        except Exception:
            pass
        return citations


class GoogleSGELiteEngine(LiteEngineBase):
    """Google SGE (AI Overview) crawler for lite mode (sync version)."""
    
    name = "google_sge"
    base_url = "https://www.google.com"
    
    def crawl_sync(
        self,
        query: str,
        page: Page,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl Google Search for AI Overview (sync version)."""
        config = config or {}
        start_time = datetime.now(timezone.utc)
        
        try:
            # Go to Google search with the query
            search_url = f"{self.base_url}/search?q={query}"
            logger.info(f"[GoogleSGE] Navigating to {search_url}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            self.random_delay(2000, 4000)
            
            # Check for challenges
            if not self.detect_and_handle_challenge(page, config):
                screenshot_path = self.take_screenshot_sync(page, f"{query}_challenge_failed")
                return {
                    "success": False,
                    "query": query,
                    "error": "无法通过验证挑战",
                    "engine": self.name,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "screenshot_path": screenshot_path,
                }
            
            self.take_screenshot_sync(page, f"{query}_initial")
            
            # Wait for AI Overview to load (if available)
            self.random_delay(3000, 5000)
            
            # Look for AI Overview section
            ai_overview_selectors = [
                '[data-attrid*="ai"]',
                '[class*="ai-overview"]',
                '[class*="AIOverview"]',
                '[data-md*="ai"]',
                '[class*="featured-snippet"]',
                '[class*="kp-wholepage"]',
                '#rso [class*="g"] [data-attrid]',
            ]
            
            ai_content = ""
            for selector in ai_overview_selectors:
                try:
                    el = page.query_selector(selector)
                    if el:
                        text = el.inner_text()
                        if text and len(text) > 50:
                            ai_content = text
                            break
                except:
                    continue
            
            html_content = page.content()
            response_text = ai_content if ai_content else self._extract_response_sync(page)
            citations = self._extract_citations_sync(page)
            screenshot_path = self.take_screenshot_sync(page, query) if config.get("take_screenshot", True) else None
            
            elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            success = len(response_text) > 50
            logger.info(f"[GoogleSGE] {'Success' if success else 'No AI Overview'}! Response length: {len(response_text)}")
            
            return {
                "success": success,
                "query": query,
                "response_text": response_text,
                "citations": citations,
                "raw_html": html_content[:50000] if html_content else "",
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "engine": self.name,
                "response_time_ms": elapsed_ms,
                "has_ai_overview": bool(ai_content),
            }
        except Exception as e:
            logger.error(f"GoogleSGE crawl error: {e}")
            try:
                screenshot_path = self.take_screenshot_sync(page, f"{query}_error")
            except:
                screenshot_path = None
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "engine": self.name,
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def _extract_response_sync(self, page: Page) -> str:
        """Extract featured snippet or main search result."""
        try:
            selectors = [
                '[class*="featured-snippet"]',
                '[data-attrid*="description"]',
                '[class*="kp-wholepage"]',
                '#rso [class*="g"]:first-child',
            ]
            for selector in selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    for el in elements:
                        text = el.inner_text()
                        if text and len(text) > 50:
                            return text
            return ""
        except Exception:
            return ""
    
    def _extract_citations_sync(self, page: Page) -> List[Dict]:
        """Extract search result links as citations."""
        citations = []
        try:
            # Get search result links
            links = page.query_selector_all('#rso a[href^="http"], [data-attrid] a[href^="http"]')
            seen_urls = set()
            for link in links[:15]:
                href = link.get_attribute("href")
                title = link.inner_text()
                if href and href.startswith("http") and href not in seen_urls:
                    if "google.com" not in href:
                        seen_urls.add(href)
                        try:
                            from urllib.parse import urlparse
                            domain = urlparse(href).netloc
                        except:
                            domain = href
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": title[:200] if title else "",
                            "domain": domain,
                            "source": "google_sge",
                        })
        except Exception:
            pass
        return citations


class BingCopilotLiteEngine(LiteEngineBase):
    """Bing Copilot crawler for lite mode (sync version)."""
    
    name = "bing_copilot"
    base_url = "https://www.bing.com/chat"
    
    def crawl_sync(
        self,
        query: str,
        page: Page,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl Bing Copilot for a query (sync version)."""
        config = config or {}
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"[BingCopilot] Navigating to {self.base_url}")
            page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
            self.random_delay(3000, 5000)
            
            # Check for challenges
            if not self.detect_and_handle_challenge(page, config):
                screenshot_path = self.take_screenshot_sync(page, f"{query}_challenge_failed")
                return {
                    "success": False,
                    "query": query,
                    "error": "无法通过验证挑战",
                    "engine": self.name,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "screenshot_path": screenshot_path,
                }
            
            self.take_screenshot_sync(page, f"{query}_initial")
            
            # Find input field - Bing Copilot has specific selectors
            input_selectors = [
                '#searchbox',
                'textarea[placeholder*="Ask"]',
                'textarea[placeholder*="问"]',
                'textarea[name="q"]',
                '[class*="chat-input"] textarea',
                'textarea',
                '[contenteditable="true"]',
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = page.query_selector(selector)
                    if input_element and input_element.is_visible():
                        break
                except:
                    continue
            
            if not input_element:
                # Check for login requirement
                page_text = page.inner_text("body")
                if "Sign in" in page_text or "登录" in page_text:
                    screenshot_path = self.take_screenshot_sync(page, f"{query}_login_required")
                    return {
                        "success": False,
                        "query": query,
                        "error": "登录要求: Bing Copilot 需要登录才能使用",
                        "engine": self.name,
                        "requires_login": True,
                        "screenshot_path": screenshot_path,
                        "crawled_at": datetime.now(timezone.utc).isoformat(),
                    }
                
                screenshot_path = self.take_screenshot_sync(page, f"{query}_no_input")
                return {
                    "success": False,
                    "query": query,
                    "error": "找不到输入框",
                    "engine": self.name,
                    "screenshot_path": screenshot_path,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
            
            # Type query
            logger.info(f"[BingCopilot] Typing query: {query[:30]}...")
            input_element.click()
            self.random_delay(300, 500)
            input_element.fill(query)
            self.random_delay(500, 1000)
            
            # Submit
            logger.info("[BingCopilot] Submitting query")
            submit_btn = page.query_selector('button[type="submit"], button[aria-label*="Submit"], [class*="submit"]')
            if submit_btn:
                submit_btn.click()
            else:
                page.keyboard.press("Enter")
            
            # Wait for response
            self.random_delay(5000, 10000)
            
            # Wait for completion
            max_wait = 120
            start_wait = datetime.now(timezone.utc)
            last_text = ""
            stable_count = 0
            
            while (datetime.now(timezone.utc) - start_wait).seconds < max_wait:
                # Check if still typing
                typing_indicator = page.query_selector('[class*="typing"], [class*="loading"]')
                if typing_indicator and typing_indicator.is_visible():
                    self.random_delay(2000, 3000)
                    continue
                
                current_text = self._extract_response_sync(page)
                if current_text == last_text and len(current_text) > 50:
                    stable_count += 1
                    if stable_count >= 3:
                        break
                else:
                    stable_count = 0
                    last_text = current_text
                self.random_delay(2000, 3000)
            
            html_content = page.content()
            response_text = self._extract_response_sync(page)
            citations = self._extract_citations_sync(page)
            screenshot_path = self.take_screenshot_sync(page, query) if config.get("take_screenshot", True) else None
            
            elapsed_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            success = len(response_text) > 50
            logger.info(f"[BingCopilot] {'Success' if success else 'Failed'}! Response length: {len(response_text)}")
            
            return {
                "success": success,
                "query": query,
                "response_text": response_text,
                "citations": citations,
                "raw_html": html_content[:50000] if html_content else "",
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "engine": self.name,
                "response_time_ms": elapsed_ms,
            }
        except Exception as e:
            logger.error(f"BingCopilot crawl error: {e}")
            try:
                screenshot_path = self.take_screenshot_sync(page, f"{query}_error")
            except:
                screenshot_path = None
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "engine": self.name,
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def _extract_response_sync(self, page: Page) -> str:
        try:
            selectors = [
                '[class*="response-content"]',
                '[class*="message-content"]',
                '[class*="bot-response"]',
                '[class*="cib-message"]',
                '[class*="markdown"]',
                '[class*="prose"]',
            ]
            for selector in selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    for el in reversed(elements):
                        text = el.inner_text()
                        if text and len(text) > 50:
                            return text
            return ""
        except Exception:
            return ""
    
    def _extract_citations_sync(self, page: Page) -> List[Dict]:
        """Extract citations from Bing Copilot responses."""
        citations = []
        try:
            # Bing Copilot shows "Learn more" links
            links = page.query_selector_all('[class*="citation"] a, [class*="source"] a, [class*="reference"] a, [class*="learn-more"] a')
            seen_urls = set()
            for link in links[:20]:
                href = link.get_attribute("href")
                title = link.inner_text()
                if href and href.startswith("http") and href not in seen_urls:
                    if "bing.com" not in href and "microsoft.com" not in href:
                        seen_urls.add(href)
                        try:
                            from urllib.parse import urlparse
                            domain = urlparse(href).netloc
                        except:
                            domain = href
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": title[:200] if title else "",
                            "domain": domain,
                            "source": "bing_copilot",
                        })
        except Exception:
            pass
        return citations


# Engine registry
LITE_ENGINES = {
    "perplexity": PerplexityLiteEngine,
    "qwen": QwenLiteEngine,
    "deepseek": DeepSeekLiteEngine,
    "kimi": KimiLiteEngine,
    "chatgpt": ChatGPTLiteEngine,
    "doubao": DoubaoLiteEngine,
    "chatglm": ChatGLMLiteEngine,
    "google_sge": GoogleSGELiteEngine,
    "bing_copilot": BingCopilotLiteEngine,
}


class LiteCrawlerService:
    """Execute crawler tasks directly in lite mode without Redis/Celery."""
    
    def __init__(self):
        self.browser_manager: Optional[LitePlaywrightManager] = None
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    async def _ensure_browser(self):
        """Ensure browser is running."""
        if self.browser_manager is None:
            logger.info(f"[LiteCrawler] Playwright available: {PLAYWRIGHT_AVAILABLE}")
            if not PLAYWRIGHT_AVAILABLE:
                logger.error("[LiteCrawler] Playwright is NOT installed! Run: pip install playwright && playwright install chromium")
                raise RuntimeError("Playwright not available")
            
            self.browser_manager = LitePlaywrightManager()
            headless = getattr(settings, 'headless', True)
            logger.info(f"[LiteCrawler] Starting browser (headless={headless})...")
            await self.browser_manager.start(headless=headless)
            logger.info("[LiteCrawler] Browser started successfully")
    
    async def close(self):
        """Close the browser."""
        if self.browser_manager:
            await self.browser_manager.close()
            self.browser_manager = None
    
    def _crawl_query_sync(
        self,
        engine: LiteEngineBase,
        query_text: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run a single query crawl in sync mode (called from thread)."""
        # Use session-aware context for better Cloudflare/CAPTCHA handling
        context = self.browser_manager._new_context_with_session_sync(
            engine=engine.name,
            account="default",
        )
        page = self.browser_manager._new_page_sync(context)
        
        try:
            result = engine.crawl_sync(query_text, page, config)
            
            # Save session after successful crawl for future reuse
            if result.get("success"):
                self.browser_manager.save_session_sync(context, engine.name, "default")
            
            return result
        finally:
            page.close()
            context.close()
    
    async def execute_task(
        self,
        task_id: UUID,
        engine_name: str,
        queries: List[Dict[str, str]],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a crawler task directly.
        
        Args:
            task_id: The CrawlTask ID
            engine_name: Engine name (perplexity, qwen, etc.)
            queries: List of {"query_id": str, "query_text": str}
            config: Optional configuration
        
        Returns:
            Summary of execution results
        """
        config = config or {}
        results = []
        successful = 0
        failed = 0
        
        logger.info(f"[LiteCrawler] Starting task {task_id} with {len(queries)} queries on {engine_name}")
        
        # Get engine
        engine_class = LITE_ENGINES.get(engine_name)
        if not engine_class:
            logger.warning(f"[LiteCrawler] Unknown engine {engine_name}, using mock response")
            # Return mock results for unsupported engines
            return await self._mock_execute(task_id, engine_name, queries)
        
        engine = engine_class()
        
        try:
            await self._ensure_browser()
            
            # Update task status to running
            await self._update_task_status(task_id, "running")
            
            loop = asyncio.get_event_loop()
            
            for query_data in queries:
                query_id = query_data.get("query_id")
                query_text = query_data.get("query_text", "")
                
                logger.info(f"[LiteCrawler] Processing query: {query_text[:50]}...")
                
                try:
                    # Run sync crawl in thread pool
                    result = await loop.run_in_executor(
                        self.browser_manager._executor,
                        partial(self._crawl_query_sync, engine, query_text, config)
                    )
                    result["query_id"] = query_id
                    
                    if result.get("success"):
                        successful += 1
                        logger.info(f"[LiteCrawler] Query SUCCESS: {query_text[:50]}...")
                    else:
                        failed += 1
                        error_msg = result.get("error", "Unknown error")
                        logger.error(f"[LiteCrawler] Query FAILED: {query_text[:50]}... Error: {error_msg}")
                    
                    # Always save result to database (both success and failure)
                    await self._save_result(task_id, query_id, result)
                    
                    results.append(result)
                    
                    # Rate limiting between queries
                    rate_limit = getattr(settings, 'crawler_rate_limit', 0.2)
                    await asyncio.sleep(1 / rate_limit if rate_limit > 0 else 5)
                    
                except Exception as e:
                    logger.error(f"[LiteCrawler] Query EXCEPTION: {query_text[:50]}... Error: {e}", exc_info=True)
                    failed += 1
                    error_result = {
                        "success": False,
                        "query_id": query_id,
                        "query": query_text,
                        "error": str(e),
                        "engine": engine_name,
                        "crawled_at": datetime.now(timezone.utc).isoformat(),
                    }
                    results.append(error_result)
                    # Save error result to database too
                    await self._save_result(task_id, query_id, error_result)
            
            # Update task as completed
            await self._update_task_status(
                task_id,
                "completed",
                successful=successful,
                failed=failed,
            )
            
            logger.info(f"[LiteCrawler] Task {task_id} completed: {successful} success, {failed} failed")
            
            return {
                "task_id": str(task_id),
                "status": "completed",
                "total": len(queries),
                "successful": successful,
                "failed": failed,
                "results": results,
            }
            
        except Exception as e:
            logger.error(f"[LiteCrawler] Task execution error: {e}")
            await self._update_task_status(task_id, "failed")
            return {
                "task_id": str(task_id),
                "status": "failed",
                "error": str(e),
            }
    
    async def _mock_execute(
        self,
        task_id: UUID,
        engine_name: str,
        queries: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Mock execution for unsupported engines."""
        results = []
        
        await self._update_task_status(task_id, "running")
        
        for query_data in queries:
            query_id = query_data.get("query_id")
            query_text = query_data.get("query_text", "")
            
            # Simulate processing delay
            await asyncio.sleep(1)
            
            result = {
                "success": True,
                "query_id": query_id,
                "query": query_text,
                "response_text": f"[Mock Response] This is a simulated response for '{query_text}' from {engine_name}.",
                "citations": [],
                "engine": engine_name,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "is_mock": True,
            }
            results.append(result)
            
            # Save mock result
            await self._save_result(task_id, query_id, result)
        
        await self._update_task_status(
            task_id,
            "completed",
            successful=len(queries),
            failed=0,
        )
        
        return {
            "task_id": str(task_id),
            "status": "completed",
            "total": len(queries),
            "successful": len(queries),
            "failed": 0,
            "results": results,
            "is_mock": True,
        }
    
    async def _update_task_status(
        self,
        task_id: UUID,
        status: str,
        successful: int = 0,
        failed: int = 0,
    ):
        """Update task status in database."""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(CrawlTask).where(CrawlTask.id == task_id)
                )
                task = result.scalar_one_or_none()
                
                if task:
                    task.status = status
                    task.successful_queries = successful
                    task.failed_queries = failed
                    
                    if status == "running":
                        task.started_at = datetime.now(timezone.utc)
                    elif status in ("completed", "failed"):
                        task.completed_at = datetime.now(timezone.utc)
                    
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
    
    async def _save_result(
        self,
        task_id: UUID,
        query_id: str,
        result: Dict[str, Any],
    ):
        """Save crawl result to database."""
        try:
            async with async_session_maker() as session:
                crawl_result = CrawlResult(
                    task_id=task_id,
                    query_item_id=UUID(query_id),
                    engine=result.get("engine", "unknown"),
                    raw_html=result.get("raw_html", "")[:100000] if result.get("raw_html") else "",
                    parsed_response={
                        "query_text": result.get("query", ""),
                        "response_text": result.get("response_text", ""),
                        "error": result.get("error"),
                    },
                    citations=result.get("citations", []),
                    response_time_ms=result.get("response_time_ms"),
                    screenshot_path=result.get("screenshot_path"),
                    is_complete=result.get("success", False),
                    has_citations=len(result.get("citations", [])) > 0,
                )
                session.add(crawl_result)
                await session.commit()
                logger.info(f"[LiteCrawler] Saved result for query_id {query_id}")
        except Exception as e:
            logger.error(f"Failed to save crawl result: {e}")


# Background task runner for lite mode
async def run_lite_crawler_task(
    task_id: UUID,
    engine: str,
    queries: List[Dict[str, str]],
    config: Optional[Dict[str, Any]] = None,
):
    """
    Run a crawler task in the background.
    
    Priority:
    1. API mode (if enabled and API key available) - no browser needed
    2. Browser mode (if Playwright available)
    3. Mock mode (fallback)
    """
    # Check if API mode should be used
    try:
        from app.config import dynamic
        from app.services.api_crawler import APICrawlerService, WEB_TO_API_ENGINE_MAP
        
        api_mode_enabled = await dynamic.get("crawler.api_mode_enabled", True)
        api_engines = await dynamic.get("crawler.api_mode_engines", 
                                        ["deepseek", "qwen", "kimi", "perplexity", "chatgpt"])
        
        # Check if this engine supports API mode
        if api_mode_enabled and engine in api_engines:
            api_service = APICrawlerService()
            try:
                # Check if API key is configured
                if await api_service.is_api_available(engine):
                    logger.info(f"[Crawler] Using API mode for engine {engine}")
                    await run_api_crawler_task(task_id, engine, queries, config)
                    return
                else:
                    logger.info(f"[Crawler] API key not configured for {engine}, falling back to browser mode")
            finally:
                await api_service.close()
    except Exception as e:
        logger.warning(f"[Crawler] Failed to check API mode: {e}, falling back to browser mode")
    
    # Fall back to browser mode
    if not PLAYWRIGHT_AVAILABLE:
        # Fallback to mock mode when playwright is not installed
        logger.warning(f"[LiteCrawler] Playwright not installed, running in mock mode for task {task_id}")
        await run_mock_crawler_task(task_id, engine, queries, config)
        return
    
    service = LiteCrawlerService()
    try:
        await service.execute_task(task_id, engine, queries, config)
    finally:
        await service.close()


async def run_api_crawler_task(
    task_id: UUID,
    engine: str,
    queries: List[Dict[str, str]],
    config: Optional[Dict[str, Any]] = None,
):
    """Run a crawler task using API mode (no browser needed)."""
    from app.services.api_crawler import APICrawlerService
    
    config = config or {}
    enable_web_search = config.get("enable_web_search", True)
    
    logger.info(f"[APICrawler] Starting API task {task_id} with {len(queries)} queries on {engine}")
    
    async with async_session_maker() as db:
        # Update task to running
        result = await db.execute(
            select(CrawlTask).where(CrawlTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "running"
            task.started_at = datetime.now(timezone.utc)
            await db.commit()
        
        successful = 0
        failed = 0
        
        # Create API crawler service
        api_service = APICrawlerService(db)
        
        try:
            for idx, query_info in enumerate(queries):
                query_text = query_info.get("query_text", "")
                query_id = query_info.get("query_id")
                
                logger.info(f"[APICrawler] Processing query {idx + 1}/{len(queries)}: {query_text[:50]}...")
                
                try:
                    # Execute query via API
                    api_result = await api_service.execute_query(
                        engine_name=engine,
                        question=query_text,
                        workspace_id=None,  # TODO: Get from task/project
                        enable_web_search=enable_web_search,
                    )
                    
                    if api_result["success"]:
                        # Save successful result
                        crawl_result = CrawlResult(
                            task_id=task_id,
                            query_item_id=UUID(query_id) if query_id else None,
                            engine=f"{engine}_api",  # Mark as API mode
                            raw_html="",  # No HTML in API mode
                            parsed_response={
                                "query_text": query_text,
                                "response_text": api_result["response_text"],
                                "model": api_result["model"],
                                "tokens_used": api_result["tokens_used"],
                                "error": None,
                            },
                            citations=api_result["citations"],
                            response_time_ms=api_result["response_time_ms"],
                            is_complete=True,
                            has_citations=len(api_result["citations"]) > 0,
                        )
                        db.add(crawl_result)
                        successful += 1
                        logger.info(f"[APICrawler] Query successful, got {len(api_result['citations'])} citations")
                    else:
                        # Save failed result
                        crawl_result = CrawlResult(
                            task_id=task_id,
                            query_item_id=UUID(query_id) if query_id else None,
                            engine=f"{engine}_api",
                            raw_html="",
                            parsed_response={
                                "query_text": query_text,
                                "response_text": "",
                                "error": api_result["error"],
                            },
                            citations=[],
                            is_complete=False,
                            has_citations=False,
                        )
                        db.add(crawl_result)
                        failed += 1
                        logger.warning(f"[APICrawler] Query failed: {api_result['error']}")
                    
                    # Small delay between requests to respect rate limits
                    if idx < len(queries) - 1:
                        await asyncio.sleep(1.0)
                        
                except Exception as e:
                    logger.error(f"[APICrawler] Exception processing query: {e}")
                    failed += 1
                
                # Update task progress
                if task:
                    task.successful_queries = successful
                    task.failed_queries = failed
                    await db.commit()
            
            # Update final task status
            if task:
                task.status = "completed"
                task.completed_at = datetime.now(timezone.utc)
                task.successful_queries = successful
                task.failed_queries = failed
                await db.commit()
            
            logger.info(f"[APICrawler] Task {task_id} completed: {successful} successful, {failed} failed")
            
        finally:
            await api_service.close()


async def run_mock_crawler_task(
    task_id: UUID,
    engine: str,
    queries: List[Dict[str, str]],
    config: Optional[Dict[str, Any]] = None,
):
    """Run a mock crawler task when playwright is not available."""
    logger.info(f"[MockCrawler] Starting mock task {task_id} with {len(queries)} queries on {engine}")
    
    async with async_session_maker() as db:
        # Update task to running
        result = await db.execute(
            select(CrawlTask).where(CrawlTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "running"
            task.started_at = datetime.now(timezone.utc)
            await db.commit()
        
        successful = 0
        failed = 0
        
        for query_info in queries:
            query_text = query_info.get("query_text", "")
            query_id = query_info.get("query_id")
            
            # Simulate processing delay
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Create mock result
            mock_response = f"""这是来自 {engine} 引擎的模拟响应。

**查询**: {query_text}

由于 Playwright 浏览器未安装，系统以模拟模式运行。要启用真实爬虫功能，请运行：

```
pip install playwright
playwright install chromium
```

模拟引用来源：
1. https://example.com/article-1 - 示例文章标题
2. https://example.com/article-2 - 另一篇相关文章
"""
            
            mock_citations = [
                {"position": 1, "url": "https://example.com/article-1", "title": "示例文章标题", "domain": "example.com"},
                {"position": 2, "url": "https://example.com/article-2", "title": "另一篇相关文章", "domain": "example.com"},
            ]
            
            # Save result using correct CrawlResult model fields
            crawl_result = CrawlResult(
                task_id=task_id,
                query_item_id=UUID(query_id) if query_id else None,
                engine=engine,
                raw_html="<mock>Mock mode - no real HTML</mock>",
                parsed_response={
                    "query_text": query_text,
                    "response_text": mock_response,
                    "error": None,
                },
                citations=mock_citations,
                is_complete=True,
                has_citations=True,
            )
            db.add(crawl_result)
            successful += 1
            
            logger.info(f"[MockCrawler] Processed query: {query_text[:50]}...")
        
        # Update task status
        if task:
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.successful_queries = successful
            task.failed_queries = failed
            await db.commit()
        
        logger.info(f"[MockCrawler] Task {task_id} completed: {successful} successful, {failed} failed")


def schedule_lite_crawler_task(
    task_id: UUID,
    engine: str,
    queries: List[Dict[str, str]],
    config: Optional[Dict[str, Any]] = None,
):
    """Schedule a crawler task to run in the background (non-blocking)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(run_lite_crawler_task(task_id, engine, queries, config))
        logger.info(f"[LiteCrawler] Scheduled task {task_id} in background")
    except RuntimeError:
        # No running loop, run synchronously
        asyncio.run(run_lite_crawler_task(task_id, engine, queries, config))
