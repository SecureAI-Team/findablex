"""Human behavior simulation for anti-detection."""
import asyncio
import random
from typing import Tuple

from playwright.async_api import Page

from app.config import settings


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
            # Occasional typo
            if random.random() < 0.03:
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                await self.page.keyboard.type(wrong_char)
                await self.random_delay(50, 150)
                await self.page.keyboard.press("Backspace")
                await self.random_delay(50, 150)
            
            await self.page.keyboard.type(char)
            
            # Variable typing speed
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
    
    async def bezier_mouse_move(self, target: Tuple[int, int]):
        """Move mouse along a bezier curve to target."""
        current_x, current_y = await self._get_mouse_position()
        target_x, target_y = target
        
        # Generate bezier curve points
        steps = random.randint(10, 20)
        control_x = (current_x + target_x) / 2 + random.randint(-100, 100)
        control_y = (current_y + target_y) / 2 + random.randint(-100, 100)
        
        for i in range(steps + 1):
            t = i / steps
            # Quadratic bezier
            x = (1-t)**2 * current_x + 2*(1-t)*t * control_x + t**2 * target_x
            y = (1-t)**2 * current_y + 2*(1-t)*t * control_y + t**2 * target_y
            
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.01, 0.03))
    
    async def _get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position (estimated)."""
        # Default to center of viewport
        viewport = self.page.viewport_size
        return (viewport["width"] // 2, viewport["height"] // 2)
    
    async def random_mouse_movement(self):
        """Make random mouse movements."""
        viewport = self.page.viewport_size
        target_x = random.randint(0, viewport["width"])
        target_y = random.randint(0, viewport["height"])
        
        await self.bezier_mouse_move((target_x, target_y))
    
    async def session_warmup(self, urls: list = None):
        """Warm up session by visiting some pages."""
        warmup_urls = urls or [
            "https://www.baidu.com",
            "https://www.bing.com",
        ]
        
        for url in random.sample(warmup_urls, min(2, len(warmup_urls))):
            try:
                await self.page.goto(url)
                await self.random_delay(2000, 5000)
                await self.natural_scroll()
                await self.random_mouse_movement()
            except Exception:
                pass
    
    async def wait_for_human_verification(self, timeout: int = 30000):
        """Wait for potential CAPTCHA or verification."""
        # Check for common CAPTCHA indicators
        captcha_selectors = [
            "iframe[src*='captcha']",
            "iframe[src*='recaptcha']",
            "[class*='captcha']",
            "[id*='captcha']",
        ]
        
        for selector in captcha_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    print(f"CAPTCHA detected: {selector}")
                    # Wait for user to solve (or timeout)
                    await asyncio.sleep(timeout / 1000)
                    return True
            except Exception:
                pass
        
        return False
