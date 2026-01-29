"""Playwright browser manager."""
import asyncio
import random
from typing import Any, Dict, List, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.config import settings
from app.browser.stealth import (
    get_init_script_for_context,
    get_stealth_launch_args,
    get_viewport_configs,
    STEALTH_SCRIPTS_CN,
    STEALTH_SCRIPTS_EN,
)
from app.browser.user_agents import get_random_user_agent


class PlaywrightManager:
    """Manage Playwright browser instances with anti-detection."""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.default_context: Optional[BrowserContext] = None
        self._context_count = 0
    
    async def start(self):
        """Start the browser with stealth configuration."""
        self.playwright = await async_playwright().start()
        
        # Launch browser with comprehensive anti-detection args
        launch_args = get_stealth_launch_args()
        
        self.browser = await self.playwright.chromium.launch(
            headless=settings.headless,
            args=launch_args,
        )
        
        # Create default context with stealth settings
        viewport = random.choice(get_viewport_configs())
        user_agent = get_random_user_agent()
        
        self.default_context = await self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        
        # Add comprehensive anti-detection scripts
        await self.default_context.add_init_script(STEALTH_SCRIPTS_CN)
    
    async def close(self):
        """Close the browser."""
        if self.default_context:
            await self.default_context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def new_page(self, context: Optional[BrowserContext] = None) -> Page:
        """Create a new page."""
        ctx = context or self.default_context
        page = await ctx.new_page()
        page.set_default_timeout(settings.browser_timeout)
        return page
    
    async def new_context(
        self,
        proxy: Optional[Dict[str, str]] = None,
        locale: str = "zh-CN",
        storage_state: Optional[Dict] = None,
    ) -> BrowserContext:
        """Create a new browser context with stealth settings."""
        self._context_count += 1
        
        # Randomize viewport for fingerprint diversity
        viewport = random.choice(get_viewport_configs())
        timezone = "Asia/Shanghai" if locale.startswith("zh") else "America/New_York"
        
        context_options = {
            "viewport": viewport,
            "user_agent": get_random_user_agent(),
            "locale": locale,
            "timezone_id": timezone,
        }
        
        if proxy:
            context_options["proxy"] = proxy
        
        if storage_state:
            context_options["storage_state"] = storage_state
        
        context = await self.browser.new_context(**context_options)
        
        # Add stealth scripts to new context
        stealth_script = STEALTH_SCRIPTS_CN if locale.startswith("zh") else STEALTH_SCRIPTS_EN
        await context.add_init_script(stealth_script)
        
        return context
