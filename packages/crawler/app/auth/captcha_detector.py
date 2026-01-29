"""
CAPTCHA detection and handling strategies.

Detects various CAPTCHA types and provides handling options:
- Automatic waiting/retry for rate-limit CAPTCHAs
- Third-party solver integration (2Captcha, Anti-Captcha)
- Manual solving queue with notifications
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Page

from app.config import settings

logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    """Types of CAPTCHAs that can be detected."""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE = "cloudflare"
    TURNSTILE = "turnstile"
    IMAGE_CAPTCHA = "image_captcha"
    SLIDER_CAPTCHA = "slider_captcha"
    TEXT_CAPTCHA = "text_captcha"
    UNKNOWN = "unknown"


class CaptchaSolverStrategy(ABC):
    """Base class for CAPTCHA solving strategies."""
    
    name: str = "base"
    
    @abstractmethod
    async def solve(
        self,
        page: Page,
        captcha_type: CaptchaType,
        captcha_info: Dict[str, Any],
    ) -> bool:
        """
        Attempt to solve the CAPTCHA.
        
        Args:
            page: Playwright page
            captcha_type: Type of CAPTCHA detected
            captcha_info: Additional info about the CAPTCHA
        
        Returns:
            True if solved successfully
        """
        pass


class WaitAndRetryStrategy(CaptchaSolverStrategy):
    """
    Simple wait and retry strategy for rate-limit CAPTCHAs.
    
    Useful for Cloudflare challenges that auto-resolve.
    """
    
    name = "wait_and_retry"
    
    def __init__(self, max_wait: int = 30, check_interval: int = 2):
        self.max_wait = max_wait
        self.check_interval = check_interval
    
    async def solve(
        self,
        page: Page,
        captcha_type: CaptchaType,
        captcha_info: Dict[str, Any],
    ) -> bool:
        """Wait for CAPTCHA to auto-resolve."""
        logger.info(f"Waiting for {captcha_type.value} to resolve (max {self.max_wait}s)")
        
        elapsed = 0
        while elapsed < self.max_wait:
            await asyncio.sleep(self.check_interval)
            elapsed += self.check_interval
            
            # Check if CAPTCHA is gone
            detector = CaptchaDetector()
            detected, _ = await detector.detect(page)
            
            if not detected:
                logger.info("CAPTCHA resolved!")
                return True
        
        logger.warning("CAPTCHA did not auto-resolve")
        return False


class ManualSolverStrategy(CaptchaSolverStrategy):
    """
    Manual solving strategy.
    
    Waits for user to solve CAPTCHA in the browser.
    Optionally sends notification.
    """
    
    name = "manual"
    
    def __init__(
        self,
        timeout: int = 300,
        notify_callback: Optional[callable] = None,
    ):
        self.timeout = timeout
        self.notify_callback = notify_callback
    
    async def solve(
        self,
        page: Page,
        captcha_type: CaptchaType,
        captcha_info: Dict[str, Any],
    ) -> bool:
        """Wait for manual CAPTCHA solving."""
        logger.info(f"Manual CAPTCHA solve required: {captcha_type.value}")
        
        # Send notification if callback provided
        if self.notify_callback:
            try:
                await self.notify_callback({
                    "type": "captcha_required",
                    "captcha_type": captcha_type.value,
                    "url": page.url,
                    "timeout": self.timeout,
                })
            except Exception as e:
                logger.warning(f"Notification callback failed: {e}")
        
        # Wait for CAPTCHA to be solved
        elapsed = 0
        check_interval = 2
        
        while elapsed < self.timeout:
            await asyncio.sleep(check_interval)
            elapsed += check_interval
            
            # Check if CAPTCHA is gone
            detector = CaptchaDetector()
            detected, _ = await detector.detect(page)
            
            if not detected:
                logger.info("CAPTCHA solved manually!")
                return True
        
        logger.warning("Manual CAPTCHA solve timed out")
        return False


class TwoCaptchaSolverStrategy(CaptchaSolverStrategy):
    """
    2Captcha API solver strategy.
    
    Uses 2captcha.com service to solve CAPTCHAs.
    """
    
    name = "2captcha"
    API_URL = "https://2captcha.com"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'captcha_api_key', '')
    
    async def solve(
        self,
        page: Page,
        captcha_type: CaptchaType,
        captcha_info: Dict[str, Any],
    ) -> bool:
        """Solve CAPTCHA using 2Captcha API."""
        if not self.api_key:
            logger.error("2Captcha API key not configured")
            return False
        
        try:
            import httpx
            
            # Submit CAPTCHA for solving
            if captcha_type in (CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3):
                site_key = captcha_info.get("site_key", "")
                page_url = page.url
                
                async with httpx.AsyncClient() as client:
                    # Submit task
                    submit_data = {
                        "key": self.api_key,
                        "method": "userrecaptcha",
                        "googlekey": site_key,
                        "pageurl": page_url,
                        "json": 1,
                    }
                    
                    if captcha_type == CaptchaType.RECAPTCHA_V3:
                        submit_data["version"] = "v3"
                        submit_data["action"] = captcha_info.get("action", "verify")
                    
                    response = await client.post(
                        f"{self.API_URL}/in.php",
                        data=submit_data,
                    )
                    result = response.json()
                    
                    if result.get("status") != 1:
                        logger.error(f"2Captcha submit failed: {result}")
                        return False
                    
                    task_id = result.get("request")
                    
                    # Poll for result
                    for _ in range(60):  # Max 2 minutes
                        await asyncio.sleep(2)
                        
                        response = await client.get(
                            f"{self.API_URL}/res.php",
                            params={
                                "key": self.api_key,
                                "action": "get",
                                "id": task_id,
                                "json": 1,
                            },
                        )
                        result = response.json()
                        
                        if result.get("status") == 1:
                            token = result.get("request")
                            # Inject token into page
                            await self._inject_recaptcha_token(page, token)
                            return True
                        elif "CAPCHA_NOT_READY" not in str(result.get("request", "")):
                            logger.error(f"2Captcha solve failed: {result}")
                            return False
            
            elif captcha_type == CaptchaType.HCAPTCHA:
                # Similar process for hCaptcha
                site_key = captcha_info.get("site_key", "")
                page_url = page.url
                
                async with httpx.AsyncClient() as client:
                    submit_data = {
                        "key": self.api_key,
                        "method": "hcaptcha",
                        "sitekey": site_key,
                        "pageurl": page_url,
                        "json": 1,
                    }
                    
                    response = await client.post(f"{self.API_URL}/in.php", data=submit_data)
                    result = response.json()
                    
                    if result.get("status") != 1:
                        return False
                    
                    task_id = result.get("request")
                    
                    for _ in range(60):
                        await asyncio.sleep(2)
                        response = await client.get(
                            f"{self.API_URL}/res.php",
                            params={"key": self.api_key, "action": "get", "id": task_id, "json": 1},
                        )
                        result = response.json()
                        
                        if result.get("status") == 1:
                            token = result.get("request")
                            await self._inject_hcaptcha_token(page, token)
                            return True
                        elif "CAPCHA_NOT_READY" not in str(result.get("request", "")):
                            return False
            
            return False
            
        except Exception as e:
            logger.error(f"2Captcha solver error: {e}")
            return False
    
    async def _inject_recaptcha_token(self, page: Page, token: str):
        """Inject reCAPTCHA token into page."""
        await page.evaluate(f"""
            const textarea = document.getElementById('g-recaptcha-response');
            if (textarea) {{
                textarea.innerHTML = '{token}';
                textarea.style.display = 'block';
            }}
            
            // Also try to find callback and invoke it
            if (typeof ___grecaptcha_cfg !== 'undefined') {{
                Object.keys(___grecaptcha_cfg.clients).forEach(key => {{
                    const client = ___grecaptcha_cfg.clients[key];
                    if (client && client.callback) {{
                        client.callback('{token}');
                    }}
                }});
            }}
        """)
    
    async def _inject_hcaptcha_token(self, page: Page, token: str):
        """Inject hCaptcha token into page."""
        await page.evaluate(f"""
            const textarea = document.querySelector('[name="h-captcha-response"]');
            if (textarea) {{
                textarea.value = '{token}';
            }}
            
            // Try to submit form
            const form = document.querySelector('form');
            if (form) {{
                form.submit();
            }}
        """)


class CaptchaDetector:
    """
    Detect CAPTCHAs on web pages.
    
    Identifies various CAPTCHA types and extracts relevant info.
    """
    
    # Detection selectors for each CAPTCHA type
    DETECTION_RULES: Dict[CaptchaType, List[Dict[str, Any]]] = {
        CaptchaType.RECAPTCHA_V2: [
            {"selector": 'iframe[src*="recaptcha/api2"]', "extract": "src"},
            {"selector": '.g-recaptcha', "extract": "data-sitekey"},
            {"selector": '[data-sitekey]', "extract": "data-sitekey"},
        ],
        CaptchaType.RECAPTCHA_V3: [
            {"selector": 'script[src*="recaptcha/api.js?render="]', "extract": "src"},
        ],
        CaptchaType.HCAPTCHA: [
            {"selector": 'iframe[src*="hcaptcha.com"]', "extract": "src"},
            {"selector": '.h-captcha', "extract": "data-sitekey"},
        ],
        CaptchaType.CLOUDFLARE: [
            {"selector": '#challenge-form', "extract": None},
            {"selector": '[data-ray]', "extract": None},
            {"selector": '#cf-challenge-running', "extract": None},
        ],
        CaptchaType.TURNSTILE: [
            {"selector": 'iframe[src*="challenges.cloudflare.com"]', "extract": "src"},
            {"selector": '.cf-turnstile', "extract": "data-sitekey"},
        ],
        CaptchaType.SLIDER_CAPTCHA: [
            {"selector": '[class*="slider"]', "extract": None},
            {"selector": '[class*="drag"]', "extract": None},
        ],
        CaptchaType.IMAGE_CAPTCHA: [
            {"selector": 'img[src*="captcha"]', "extract": "src"},
            {"selector": '[class*="captcha"] img', "extract": "src"},
        ],
    }
    
    async def detect(self, page: Page) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if page has a CAPTCHA.
        
        Args:
            page: Playwright page
        
        Returns:
            Tuple of (has_captcha, captcha_info)
        """
        for captcha_type, rules in self.DETECTION_RULES.items():
            for rule in rules:
                try:
                    element = await page.query_selector(rule["selector"])
                    if element:
                        info = {
                            "type": captcha_type,
                            "selector": rule["selector"],
                        }
                        
                        # Extract additional info
                        if rule["extract"]:
                            value = await element.get_attribute(rule["extract"])
                            info["site_key"] = self._extract_site_key(value, captcha_type)
                            info["raw_value"] = value
                        
                        logger.info(f"CAPTCHA detected: {captcha_type.value}")
                        return True, info
                        
                except Exception as e:
                    logger.debug(f"Detection error for {rule['selector']}: {e}")
                    continue
        
        # Check page content for CAPTCHA indicators
        try:
            content = await page.content()
            content_lower = content.lower()
            
            captcha_indicators = [
                ("recaptcha", CaptchaType.RECAPTCHA_V2),
                ("hcaptcha", CaptchaType.HCAPTCHA),
                ("cloudflare", CaptchaType.CLOUDFLARE),
                ("turnstile", CaptchaType.TURNSTILE),
            ]
            
            for indicator, captcha_type in captcha_indicators:
                if indicator in content_lower:
                    # Additional check - make sure it's actually a challenge
                    if any(x in content_lower for x in ["challenge", "verify", "robot"]):
                        return True, {"type": captcha_type, "detected_by": "content"}
                        
        except Exception as e:
            logger.debug(f"Content check error: {e}")
        
        return False, None
    
    def _extract_site_key(self, value: str, captcha_type: CaptchaType) -> Optional[str]:
        """Extract site key from attribute value."""
        if not value:
            return None
        
        if captcha_type in (CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3):
            # From src: ...?k=SITEKEY or render=SITEKEY
            import re
            match = re.search(r'[?&]k=([^&]+)', value)
            if match:
                return match.group(1)
            match = re.search(r'render=([^&]+)', value)
            if match:
                return match.group(1)
        
        # Direct site key
        if len(value) > 20 and value.isalnum():
            return value
        
        return value
    
    async def get_captcha_screenshot(
        self,
        page: Page,
        captcha_info: Dict[str, Any],
    ) -> Optional[bytes]:
        """Get screenshot of CAPTCHA element."""
        try:
            selector = captcha_info.get("selector")
            if selector:
                element = await page.query_selector(selector)
                if element:
                    return await element.screenshot()
            
            # Fallback to full page
            return await page.screenshot()
        except Exception as e:
            logger.error(f"CAPTCHA screenshot error: {e}")
            return None


class CaptchaHandler:
    """
    Handle CAPTCHAs with configurable strategies.
    
    Usage:
        handler = CaptchaHandler()
        
        # Check for CAPTCHA
        if await handler.check_and_handle(page):
            # CAPTCHA was detected and handled
            pass
    """
    
    # Default strategies for each CAPTCHA type
    DEFAULT_STRATEGIES: Dict[CaptchaType, str] = {
        CaptchaType.CLOUDFLARE: "wait_and_retry",
        CaptchaType.TURNSTILE: "wait_and_retry",
        CaptchaType.RECAPTCHA_V2: "manual",
        CaptchaType.RECAPTCHA_V3: "wait_and_retry",
        CaptchaType.HCAPTCHA: "manual",
        CaptchaType.SLIDER_CAPTCHA: "manual",
        CaptchaType.IMAGE_CAPTCHA: "manual",
        CaptchaType.UNKNOWN: "manual",
    }
    
    def __init__(
        self,
        preferred_strategy: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize CAPTCHA handler.
        
        Args:
            preferred_strategy: Preferred strategy (manual, wait_and_retry, 2captcha)
            api_key: API key for third-party solvers
        """
        self.preferred_strategy = preferred_strategy or getattr(settings, 'captcha_solver', 'manual')
        self.api_key = api_key or getattr(settings, 'captcha_api_key', '')
        self.detector = CaptchaDetector()
        
        # Initialize strategies
        self.strategies: Dict[str, CaptchaSolverStrategy] = {
            "wait_and_retry": WaitAndRetryStrategy(),
            "manual": ManualSolverStrategy(),
        }
        
        if self.api_key:
            self.strategies["2captcha"] = TwoCaptchaSolverStrategy(self.api_key)
    
    async def check_and_handle(
        self,
        page: Page,
        max_attempts: int = 3,
    ) -> bool:
        """
        Check for CAPTCHA and attempt to handle it.
        
        Args:
            page: Playwright page
            max_attempts: Maximum solve attempts
        
        Returns:
            True if CAPTCHA was detected and handled (or no CAPTCHA)
        """
        # Check for CAPTCHA
        detected, captcha_info = await self.detector.detect(page)
        
        if not detected:
            return True  # No CAPTCHA, proceed
        
        captcha_type = captcha_info.get("type", CaptchaType.UNKNOWN)
        logger.info(f"CAPTCHA detected: {captcha_type.value}")
        
        # Get strategy
        strategy_name = self.preferred_strategy
        if strategy_name not in self.strategies:
            strategy_name = self.DEFAULT_STRATEGIES.get(captcha_type, "manual")
        
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            logger.error(f"No strategy available: {strategy_name}")
            return False
        
        # Attempt to solve
        for attempt in range(max_attempts):
            logger.info(f"Attempting to solve CAPTCHA (attempt {attempt + 1}/{max_attempts})")
            
            solved = await strategy.solve(page, captcha_type, captcha_info)
            
            if solved:
                # Verify CAPTCHA is gone
                detected, _ = await self.detector.detect(page)
                if not detected:
                    logger.info("CAPTCHA solved successfully!")
                    return True
            
            # Wait before retry
            await asyncio.sleep(2)
        
        logger.warning("Failed to solve CAPTCHA after all attempts")
        return False
    
    def set_notification_callback(self, callback: callable):
        """Set callback for manual solve notifications."""
        if "manual" in self.strategies:
            self.strategies["manual"].notify_callback = callback
