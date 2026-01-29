"""
Login flow handler for engines requiring authentication.

Supports multiple login strategies:
- Manual: User logs in interactively, session is saved
- Cookie injection: Import cookies from external source
- API tokens: Use API keys where available
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type

from playwright.async_api import BrowserContext, Page

from app.auth.session_store import SessionStore, get_session_store
from app.browser.human_simulator import HumanSimulator

logger = logging.getLogger(__name__)


class LoginStrategy(ABC):
    """Base class for login strategies."""
    
    name: str = "base"
    
    @abstractmethod
    async def login(
        self,
        page: Page,
        credentials: Dict[str, Any],
        simulator: HumanSimulator,
    ) -> bool:
        """
        Perform login.
        
        Args:
            page: Playwright page
            credentials: Login credentials
            simulator: Human behavior simulator
        
        Returns:
            True if login successful
        """
        pass
    
    @abstractmethod
    async def check_logged_in(self, page: Page) -> bool:
        """
        Check if currently logged in.
        
        Args:
            page: Playwright page
        
        Returns:
            True if logged in
        """
        pass


class ManualLoginStrategy(LoginStrategy):
    """
    Manual login strategy.
    
    Opens browser in visible mode and waits for user to login.
    """
    
    name = "manual"
    
    def __init__(self, timeout_seconds: int = 300):
        self.timeout_seconds = timeout_seconds
    
    async def login(
        self,
        page: Page,
        credentials: Dict[str, Any],
        simulator: HumanSimulator,
    ) -> bool:
        """Wait for user to login manually."""
        login_url = credentials.get("login_url", "")
        
        if login_url:
            await page.goto(login_url)
        
        logger.info(f"Please login manually in the browser window. Timeout: {self.timeout_seconds}s")
        
        # Wait for login indicators to disappear
        start_time = datetime.now(timezone.utc)
        check_interval = 2  # seconds
        
        while True:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed > self.timeout_seconds:
                logger.warning("Manual login timeout")
                return False
            
            if await self.check_logged_in(page):
                logger.info("Login detected!")
                return True
            
            await asyncio.sleep(check_interval)
    
    async def check_logged_in(self, page: Page) -> bool:
        """Check for login indicators."""
        # Common login page indicators
        login_indicators = [
            'input[type="password"]',
            '[class*="login"]',
            '[class*="signin"]',
            'button:has-text("登录")',
            'button:has-text("Sign in")',
            'button:has-text("Log in")',
        ]
        
        for selector in login_indicators:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    return False
            except Exception:
                continue
        
        # Check for logged-in indicators
        logged_in_indicators = [
            '[class*="avatar"]',
            '[class*="profile"]',
            '[class*="user-menu"]',
            '[aria-label*="account"]',
        ]
        
        for selector in logged_in_indicators:
            try:
                element = await page.query_selector(selector)
                if element:
                    return True
            except Exception:
                continue
        
        # If no login form visible, assume logged in
        return True


class EmailPasswordLoginStrategy(LoginStrategy):
    """
    Automated email/password login.
    
    Fills in login form automatically with human-like behavior.
    """
    
    name = "email_password"
    
    async def login(
        self,
        page: Page,
        credentials: Dict[str, Any],
        simulator: HumanSimulator,
    ) -> bool:
        """Perform automated email/password login."""
        email = credentials.get("email", "")
        password = credentials.get("password", "")
        login_url = credentials.get("login_url", "")
        
        if not email or not password:
            logger.error("Email and password required")
            return False
        
        try:
            if login_url:
                await page.goto(login_url)
                await simulator.random_delay(1000, 2000)
            
            # Find email input
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[name="username"]',
                'input[placeholder*="email" i]',
                'input[placeholder*="邮箱"]',
            ]
            
            email_input = None
            for selector in email_selectors:
                email_input = await page.query_selector(selector)
                if email_input:
                    break
            
            if not email_input:
                logger.error("Could not find email input")
                return False
            
            # Type email
            await simulator.type_text(email_selectors[0], email)
            await simulator.random_delay(500, 1000)
            
            # Find password input
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="password" i]',
                'input[placeholder*="密码"]',
            ]
            
            password_input = None
            for selector in password_selectors:
                password_input = await page.query_selector(selector)
                if password_input:
                    break
            
            if not password_input:
                logger.error("Could not find password input")
                return False
            
            # Type password
            await simulator.type_text(password_selectors[0], password)
            await simulator.random_delay(500, 1000)
            
            # Find and click submit button
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("登录")',
                'button:has-text("Sign in")',
                'button:has-text("Log in")',
                'input[type="submit"]',
            ]
            
            for selector in submit_selectors:
                submit = await page.query_selector(selector)
                if submit and await submit.is_visible():
                    await submit.click()
                    break
            else:
                # Try pressing Enter
                await page.keyboard.press("Enter")
            
            # Wait for navigation
            await simulator.random_delay(3000, 5000)
            
            # Check if logged in
            return await self.check_logged_in(page)
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    async def check_logged_in(self, page: Page) -> bool:
        """Check if logged in by looking for user indicators."""
        # Check URL changed from login page
        url = page.url.lower()
        if "login" in url or "signin" in url:
            # Still on login page, check for error
            error_selectors = [
                '[class*="error"]',
                '[class*="alert"]',
                '[role="alert"]',
            ]
            for selector in error_selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text:
                        logger.warning(f"Login error detected: {text[:100]}")
                        return False
        
        # Check for user avatar/menu
        success_indicators = [
            '[class*="avatar"]',
            '[class*="user"]',
            '[class*="profile"]',
        ]
        
        for selector in success_indicators:
            element = await page.query_selector(selector)
            if element:
                return True
        
        return False


class CookieInjectionStrategy(LoginStrategy):
    """
    Cookie injection strategy.
    
    Imports cookies from external source (browser extension, etc.)
    """
    
    name = "cookie_injection"
    
    async def login(
        self,
        page: Page,
        credentials: Dict[str, Any],
        simulator: HumanSimulator,
    ) -> bool:
        """Inject cookies to establish session."""
        cookies = credentials.get("cookies", [])
        
        if not cookies:
            logger.error("No cookies provided")
            return False
        
        try:
            context = page.context
            
            # Add cookies to context
            await context.add_cookies(cookies)
            
            # Reload page to apply cookies
            await page.reload()
            await simulator.random_delay(2000, 3000)
            
            return await self.check_logged_in(page)
            
        except Exception as e:
            logger.error(f"Cookie injection error: {e}")
            return False
    
    async def check_logged_in(self, page: Page) -> bool:
        """Check if cookies established a valid session."""
        # Simply check for user indicators
        success_indicators = [
            '[class*="avatar"]',
            '[class*="user"]',
            '[class*="profile"]',
            '[class*="logged-in"]',
        ]
        
        for selector in success_indicators:
            element = await page.query_selector(selector)
            if element:
                return True
        
        return False


# Engine-specific login handlers
ENGINE_LOGIN_CONFIGS: Dict[str, Dict[str, Any]] = {
    "perplexity": {
        "login_url": "https://www.perplexity.ai/",
        "requires_login": False,  # Can use without login
        "strategies": ["manual", "cookie_injection"],
    },
    "chatgpt": {
        "login_url": "https://chat.openai.com/auth/login",
        "requires_login": True,
        "strategies": ["manual", "cookie_injection"],
    },
    "qwen": {
        "login_url": "https://tongyi.aliyun.com/qianwen",
        "requires_login": True,
        "strategies": ["manual", "cookie_injection"],
    },
    "deepseek": {
        "login_url": "https://chat.deepseek.com/",
        "requires_login": True,
        "strategies": ["manual", "cookie_injection"],
    },
    "kimi": {
        "login_url": "https://kimi.moonshot.cn/",
        "requires_login": True,
        "strategies": ["manual", "cookie_injection"],
    },
    "doubao": {
        "login_url": "https://www.doubao.com/",
        "requires_login": True,
        "strategies": ["manual", "cookie_injection"],
    },
    "chatglm": {
        "login_url": "https://chatglm.cn/",
        "requires_login": True,
        "strategies": ["manual", "cookie_injection"],
    },
}


class LoginHandler:
    """
    Handle login flows for different engines.
    
    Manages login strategies and session persistence.
    """
    
    # Available strategies
    STRATEGIES: Dict[str, Type[LoginStrategy]] = {
        "manual": ManualLoginStrategy,
        "email_password": EmailPasswordLoginStrategy,
        "cookie_injection": CookieInjectionStrategy,
    }
    
    def __init__(self, session_store: Optional[SessionStore] = None):
        """
        Initialize login handler.
        
        Args:
            session_store: Session store for persistence
        """
        self.session_store = session_store or get_session_store()
    
    async def login(
        self,
        engine: str,
        page: Page,
        credentials: Dict[str, Any],
        strategy: str = "manual",
        save_session: bool = True,
    ) -> bool:
        """
        Perform login for an engine.
        
        Args:
            engine: Engine name
            page: Playwright page
            credentials: Login credentials
            strategy: Login strategy name
            save_session: Whether to save session after login
        
        Returns:
            True if login successful
        """
        # Get engine config
        config = ENGINE_LOGIN_CONFIGS.get(engine, {})
        
        # Add login URL to credentials if not provided
        if "login_url" not in credentials:
            credentials["login_url"] = config.get("login_url", "")
        
        # Get strategy
        strategy_class = self.STRATEGIES.get(strategy)
        if not strategy_class:
            logger.error(f"Unknown login strategy: {strategy}")
            return False
        
        # Create strategy instance
        strategy_instance = strategy_class()
        
        # Create simulator
        simulator = HumanSimulator(page)
        
        # Perform login
        success = await strategy_instance.login(page, credentials, simulator)
        
        if success and save_session:
            # Save session
            account_id = credentials.get("account_id", "default")
            await self.session_store.save_session(
                page.context,
                engine,
                account_id,
                metadata={
                    "login_strategy": strategy,
                    "login_time": datetime.now(timezone.utc).isoformat(),
                }
            )
        
        return success
    
    async def ensure_logged_in(
        self,
        engine: str,
        context: BrowserContext,
        page: Page,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Ensure user is logged in, attempting login if needed.
        
        Args:
            engine: Engine name
            context: Browser context
            page: Playwright page
            credentials: Optional credentials for auto-login
        
        Returns:
            True if logged in (or login not required)
        """
        config = ENGINE_LOGIN_CONFIGS.get(engine, {})
        
        # Check if login is required
        if not config.get("requires_login", True):
            return True
        
        # Check if already logged in
        if await self.check_logged_in(engine, page):
            return True
        
        # Try to restore session
        account_id = (credentials or {}).get("account_id", "default")
        session = await self.session_store.load_session(engine, account_id)
        
        if session:
            # Apply session
            await context.add_cookies(session.get("cookies", []))
            await page.reload()
            await asyncio.sleep(2)
            
            if await self.check_logged_in(engine, page):
                logger.info(f"Session restored for {engine}")
                return True
        
        # Need to login
        if credentials:
            strategy = credentials.get("strategy", "manual")
            return await self.login(engine, page, credentials, strategy)
        
        logger.warning(f"Login required for {engine} but no credentials provided")
        return False
    
    async def check_logged_in(self, engine: str, page: Page) -> bool:
        """
        Check if currently logged in to an engine.
        
        Args:
            engine: Engine name
            page: Playwright page
        
        Returns:
            True if logged in
        """
        # Engine-specific login checks
        checks = {
            "chatgpt": ['[data-testid*="user"]', '[class*="avatar"]'],
            "qwen": ['[class*="user"]', '[class*="avatar"]'],
            "deepseek": ['[class*="user"]', '[class*="avatar"]'],
            "kimi": ['[class*="user"]', '[class*="avatar"]'],
            "doubao": ['[class*="user"]', '[class*="avatar"]'],
            "chatglm": ['[class*="user"]', '[class*="avatar"]'],
        }
        
        selectors = checks.get(engine, ['[class*="avatar"]', '[class*="user"]'])
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    return True
            except Exception:
                continue
        
        # Check for login button as negative indicator
        login_indicators = [
            'button:has-text("登录")',
            'button:has-text("Sign in")',
            'a:has-text("登录")',
        ]
        
        for selector in login_indicators:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    return False
            except Exception:
                continue
        
        return False
    
    async def detect_login_required(self, page: Page) -> bool:
        """
        Detect if current page requires login.
        
        Args:
            page: Playwright page
        
        Returns:
            True if login appears to be required
        """
        # Check URL
        url = page.url.lower()
        if any(x in url for x in ["login", "signin", "auth"]):
            return True
        
        # Check for login form
        login_selectors = [
            'input[type="password"]',
            'form[action*="login"]',
            'form[action*="signin"]',
            '[class*="login-form"]',
        ]
        
        for selector in login_selectors:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    return True
            except Exception:
                continue
        
        return False
    
    def get_supported_strategies(self, engine: str) -> List[str]:
        """Get supported login strategies for an engine."""
        config = ENGINE_LOGIN_CONFIGS.get(engine, {})
        return config.get("strategies", ["manual"])
    
    def requires_login(self, engine: str) -> bool:
        """Check if an engine requires login."""
        config = ENGINE_LOGIN_CONFIGS.get(engine, {})
        return config.get("requires_login", True)
