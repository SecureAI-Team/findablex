"""
Challenge Handler for Cloudflare, CAPTCHA, and other anti-bot protections.

Provides unified detection and handling of various challenge types with
multiple strategies: manual solving, auto-wait, and API-based solving.
"""
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class ChallengeType(Enum):
    """Types of challenges that can be detected."""
    NONE = "none"
    CLOUDFLARE_JS = "cloudflare_js"  # JavaScript challenge (auto-resolves)
    CLOUDFLARE_CAPTCHA = "cloudflare_captcha"  # Turnstile or CAPTCHA
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    LOGIN_REQUIRED = "login_required"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class ChallengeResult:
    """Result of challenge handling."""
    success: bool
    challenge_type: ChallengeType
    message: str
    screenshot_path: Optional[str] = None
    time_taken_ms: int = 0


class ChallengeDetector:
    """
    Detects various types of challenges on a page.
    
    Supports Cloudflare, reCAPTCHA, hCaptcha, and login detection.
    """
    
    # Cloudflare detection patterns (English + Chinese)
    CLOUDFLARE_INDICATORS = [
        # English
        "Checking your browser",
        "Please wait",
        "Just a moment",
        "DDoS protection by",
        "cf-browser-verification",
        "Verifying you are human",
        "checking if the site connection is secure",
        "Enable JavaScript and cookies",
        # Chinese
        "正在验证您是否是真人",
        "这可能需要几秒钟时间",
        "检查您的连接的安全性",
        "正在验证",
        "请稍候",
        "验证您是人类",
        "安全检查",
        "Cloudflare",
        "Ray ID",
    ]
    
    CLOUDFLARE_SELECTORS = [
        "#cf-spinner",
        ".cf-browser-verification",
        "#challenge-running",
        "#challenge-form",
        "#challenge-stage",
        'iframe[src*="challenges.cloudflare.com"]',
        "#turnstile-wrapper",
        ".cf-turnstile",
        '[data-ray]',
    ]
    
    # CAPTCHA detection patterns
    RECAPTCHA_SELECTORS = [
        ".g-recaptcha",
        "#g-recaptcha",
        'iframe[src*="recaptcha"]',
        'iframe[title*="reCAPTCHA"]',
    ]
    
    HCAPTCHA_SELECTORS = [
        ".h-captcha",
        "#h-captcha",
        'iframe[src*="hcaptcha"]',
    ]
    
    # Login detection patterns
    LOGIN_INDICATORS = [
        "登录", "Sign in", "Login", "Log in",
        "请登录", "Please sign in", "请先登录",
    ]
    
    LOGIN_SELECTORS = [
        'input[type="password"]',
        'form[action*="login"]',
        'form[action*="signin"]',
        'button:has-text("登录")',
        'button:has-text("Sign in")',
    ]
    
    # Rate limit / block patterns
    RATE_LIMIT_INDICATORS = [
        "rate limit",
        "too many requests",
        "请求过于频繁",
        "try again later",
        "稍后重试",
    ]
    
    BLOCKED_INDICATORS = [
        "access denied",
        "blocked",
        "forbidden",
        "您的访问被拒绝",
        "访问受限",
    ]
    
    def detect(self, page) -> ChallengeType:
        """
        Detect if the page has any challenge.
        
        Args:
            page: Playwright page object
            
        Returns:
            ChallengeType enum value
        """
        try:
            # Get page content for text-based detection
            page_text = page.inner_text("body").lower()
            page_url = page.url.lower()
            
            logger.debug(f"[ChallengeDetector] Page URL: {page_url}")
            logger.debug(f"[ChallengeDetector] Page text (first 200 chars): {page_text[:200]}")
            
            # Check for Cloudflare
            if self._is_cloudflare(page, page_text, page_url):
                logger.info("[ChallengeDetector] Cloudflare challenge detected")
                # Determine if it's JS challenge or CAPTCHA
                if self._has_cloudflare_captcha(page):
                    logger.info("[ChallengeDetector] Type: CLOUDFLARE_CAPTCHA (Turnstile)")
                    return ChallengeType.CLOUDFLARE_CAPTCHA
                logger.info("[ChallengeDetector] Type: CLOUDFLARE_JS")
                return ChallengeType.CLOUDFLARE_JS
            
            # Check for reCAPTCHA
            if self._has_recaptcha(page):
                return ChallengeType.RECAPTCHA_V2
            
            # Check for hCaptcha
            if self._has_hcaptcha(page):
                return ChallengeType.HCAPTCHA
            
            # Check for rate limiting
            if self._is_rate_limited(page_text):
                return ChallengeType.RATE_LIMITED
            
            # Check for blocked access
            if self._is_blocked(page_text):
                return ChallengeType.BLOCKED
            
            # Check for login requirement
            if self._requires_login(page, page_text):
                return ChallengeType.LOGIN_REQUIRED
            
            return ChallengeType.NONE
            
        except Exception as e:
            logger.warning(f"Challenge detection error: {e}")
            return ChallengeType.UNKNOWN
    
    def _is_cloudflare(self, page, page_text: str, page_url: str) -> bool:
        """Check if page shows Cloudflare challenge."""
        # Check text indicators
        for indicator in self.CLOUDFLARE_INDICATORS:
            indicator_lower = indicator.lower()
            if indicator_lower in page_text:
                logger.debug(f"[ChallengeDetector] Matched Cloudflare indicator: '{indicator}'")
                return True
        
        # Check selectors
        for selector in self.CLOUDFLARE_SELECTORS:
            try:
                if page.query_selector(selector):
                    logger.debug(f"[ChallengeDetector] Matched Cloudflare selector: '{selector}'")
                    return True
            except:
                pass
        
        # Check URL
        if "challenge" in page_url or "cdn-cgi" in page_url:
            logger.debug(f"[ChallengeDetector] Matched Cloudflare URL pattern")
            return True
        
        logger.debug("[ChallengeDetector] No Cloudflare indicators found")
        return False
    
    def _has_cloudflare_captcha(self, page) -> bool:
        """Check if Cloudflare challenge includes CAPTCHA (Turnstile)."""
        captcha_selectors = [
            'iframe[src*="challenges.cloudflare.com"]',
            "#turnstile-wrapper",
            ".cf-turnstile",
        ]
        for selector in captcha_selectors:
            try:
                if page.query_selector(selector):
                    return True
            except:
                pass
        return False
    
    def _has_recaptcha(self, page) -> bool:
        """Check for reCAPTCHA presence."""
        for selector in self.RECAPTCHA_SELECTORS:
            try:
                if page.query_selector(selector):
                    return True
            except:
                pass
        return False
    
    def _has_hcaptcha(self, page) -> bool:
        """Check for hCaptcha presence."""
        for selector in self.HCAPTCHA_SELECTORS:
            try:
                if page.query_selector(selector):
                    return True
            except:
                pass
        return False
    
    def _is_rate_limited(self, page_text: str) -> bool:
        """Check if page shows rate limiting."""
        for indicator in self.RATE_LIMIT_INDICATORS:
            if indicator.lower() in page_text:
                return True
        return False
    
    def _is_blocked(self, page_text: str) -> bool:
        """Check if access is blocked."""
        for indicator in self.BLOCKED_INDICATORS:
            if indicator.lower() in page_text:
                return True
        return False
    
    def _requires_login(self, page, page_text: str) -> bool:
        """Check if page requires login."""
        # Check text indicators
        for indicator in self.LOGIN_INDICATORS:
            if indicator.lower() in page_text:
                # Also verify there's a login form
                for selector in self.LOGIN_SELECTORS:
                    try:
                        if page.query_selector(selector):
                            return True
                    except:
                        pass
        return False
    
    def get_site_key(self, page, challenge_type: ChallengeType) -> Optional[str]:
        """Extract site key for CAPTCHA solving APIs."""
        try:
            if challenge_type == ChallengeType.RECAPTCHA_V2:
                el = page.query_selector(".g-recaptcha")
                if el:
                    return el.get_attribute("data-sitekey")
            elif challenge_type == ChallengeType.HCAPTCHA:
                el = page.query_selector(".h-captcha")
                if el:
                    return el.get_attribute("data-sitekey")
        except Exception as e:
            logger.warning(f"Failed to get site key: {e}")
        return None


class ChallengeStrategy(ABC):
    """Base class for challenge handling strategies."""
    
    @abstractmethod
    def handle(self, page, challenge_type: ChallengeType, config: Dict[str, Any]) -> ChallengeResult:
        """Handle the challenge."""
        pass
    
    def take_screenshot(self, page, prefix: str = "challenge") -> Optional[str]:
        """Take a screenshot for debugging."""
        try:
            screenshot_dir = getattr(settings, 'screenshot_dir', 'data/screenshots')
            os.makedirs(screenshot_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.png"
            filepath = os.path.join(screenshot_dir, filename)
            
            page.screenshot(path=filepath, full_page=True)
            return filepath
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
            return None


class ManualChallengeStrategy(ChallengeStrategy):
    """
    Manual challenge solving strategy.
    
    Pauses execution and waits for user to manually solve the challenge.
    Best for development/testing or when API solving is not available.
    """
    
    def __init__(self, timeout_seconds: int = 300):
        self.timeout_seconds = timeout_seconds
    
    def handle(self, page, challenge_type: ChallengeType, config: Dict[str, Any]) -> ChallengeResult:
        """Wait for manual challenge solving."""
        start_time = time.time()
        screenshot_path = self.take_screenshot(page, f"manual_{challenge_type.value}")
        
        logger.warning(
            f"\n{'='*60}\n"
            f"[MANUAL SOLVING REQUIRED]\n"
            f"Challenge Type: {challenge_type.value}\n"
            f"Please solve the challenge in the browser window.\n"
            f"Timeout: {self.timeout_seconds} seconds\n"
            f"Screenshot: {screenshot_path}\n"
            f"{'='*60}"
        )
        
        detector = ChallengeDetector()
        check_interval = 2  # seconds
        
        while time.time() - start_time < self.timeout_seconds:
            time.sleep(check_interval)
            
            # Check if challenge is resolved
            current_challenge = detector.detect(page)
            if current_challenge == ChallengeType.NONE:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.info(f"[MANUAL] Challenge solved in {elapsed_ms}ms")
                
                # Wait for page to fully load after challenge resolution
                # Cloudflare redirects to the actual site after passing
                logger.info("[MANUAL] Waiting for page redirect and load...")
                time.sleep(3)  # Initial wait for redirect
                
                try:
                    # Wait for page to be ready
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                    time.sleep(2)  # Additional stabilization time
                    logger.info("[MANUAL] Page loaded after challenge")
                except Exception as e:
                    logger.warning(f"[MANUAL] Page load wait error: {e}")
                
                return ChallengeResult(
                    success=True,
                    challenge_type=challenge_type,
                    message="Challenge solved manually",
                    screenshot_path=screenshot_path,
                    time_taken_ms=elapsed_ms,
                )
        
        # Timeout
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[MANUAL] Challenge solving timeout after {elapsed_ms}ms")
        return ChallengeResult(
            success=False,
            challenge_type=challenge_type,
            message=f"Manual solving timeout after {self.timeout_seconds}s",
            screenshot_path=self.take_screenshot(page, "manual_timeout"),
            time_taken_ms=elapsed_ms,
        )


class AutoWaitStrategy(ChallengeStrategy):
    """
    Auto-wait strategy for JavaScript challenges.
    
    Cloudflare JS challenges typically resolve automatically in 5-10 seconds.
    This strategy waits for the challenge to complete.
    """
    
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds
    
    def handle(self, page, challenge_type: ChallengeType, config: Dict[str, Any]) -> ChallengeResult:
        """Wait for auto-resolving challenge."""
        start_time = time.time()
        screenshot_path = self.take_screenshot(page, f"autowait_{challenge_type.value}")
        
        logger.info(f"[AUTOWAIT] Waiting for {challenge_type.value} to resolve...")
        
        detector = ChallengeDetector()
        check_interval = 1  # second
        
        while time.time() - start_time < self.timeout_seconds:
            time.sleep(check_interval)
            
            # Check if challenge is resolved
            current_challenge = detector.detect(page)
            if current_challenge == ChallengeType.NONE:
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.info(f"[AUTOWAIT] Challenge auto-resolved in {elapsed_ms}ms")
                return ChallengeResult(
                    success=True,
                    challenge_type=challenge_type,
                    message="Challenge auto-resolved",
                    screenshot_path=screenshot_path,
                    time_taken_ms=elapsed_ms,
                )
            
            # Check for cf_clearance cookie (Cloudflare success indicator)
            if challenge_type in (ChallengeType.CLOUDFLARE_JS, ChallengeType.CLOUDFLARE_CAPTCHA):
                cookies = page.context.cookies()
                if any(c["name"] == "cf_clearance" for c in cookies):
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    logger.info(f"[AUTOWAIT] Cloudflare clearance obtained in {elapsed_ms}ms")
                    return ChallengeResult(
                        success=True,
                        challenge_type=challenge_type,
                        message="Cloudflare clearance cookie obtained",
                        time_taken_ms=elapsed_ms,
                    )
        
        # Timeout - challenge didn't auto-resolve
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.warning(f"[AUTOWAIT] Challenge didn't auto-resolve in {elapsed_ms}ms")
        return ChallengeResult(
            success=False,
            challenge_type=challenge_type,
            message=f"Auto-wait timeout after {self.timeout_seconds}s",
            screenshot_path=self.take_screenshot(page, "autowait_timeout"),
            time_taken_ms=elapsed_ms,
        )


class TwoCaptchaStrategy(ChallengeStrategy):
    """
    2Captcha API strategy for solving CAPTCHAs.
    
    Sends CAPTCHA to 2Captcha service for solving.
    Requires API key configuration.
    """
    
    API_URL = "http://2captcha.com"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'twocaptcha_api_key', '')
    
    def handle(self, page, challenge_type: ChallengeType, config: Dict[str, Any]) -> ChallengeResult:
        """Solve CAPTCHA using 2Captcha API."""
        start_time = time.time()
        
        if not self.api_key:
            return ChallengeResult(
                success=False,
                challenge_type=challenge_type,
                message="2Captcha API key not configured",
                time_taken_ms=0,
            )
        
        try:
            import requests
        except ImportError:
            return ChallengeResult(
                success=False,
                challenge_type=challenge_type,
                message="requests library required for 2Captcha",
                time_taken_ms=0,
            )
        
        detector = ChallengeDetector()
        site_key = detector.get_site_key(page, challenge_type)
        
        if not site_key:
            return ChallengeResult(
                success=False,
                challenge_type=challenge_type,
                message="Could not extract site key for CAPTCHA",
                screenshot_path=self.take_screenshot(page, "2captcha_no_sitekey"),
                time_taken_ms=int((time.time() - start_time) * 1000),
            )
        
        page_url = page.url
        
        logger.info(f"[2CAPTCHA] Submitting {challenge_type.value} to 2Captcha...")
        
        try:
            # Submit CAPTCHA
            if challenge_type == ChallengeType.RECAPTCHA_V2:
                submit_data = {
                    "key": self.api_key,
                    "method": "userrecaptcha",
                    "googlekey": site_key,
                    "pageurl": page_url,
                    "json": 1,
                }
            elif challenge_type == ChallengeType.HCAPTCHA:
                submit_data = {
                    "key": self.api_key,
                    "method": "hcaptcha",
                    "sitekey": site_key,
                    "pageurl": page_url,
                    "json": 1,
                }
            else:
                return ChallengeResult(
                    success=False,
                    challenge_type=challenge_type,
                    message=f"2Captcha doesn't support {challenge_type.value}",
                    time_taken_ms=int((time.time() - start_time) * 1000),
                )
            
            # Submit to 2Captcha
            response = requests.post(f"{self.API_URL}/in.php", data=submit_data, timeout=30)
            result = response.json()
            
            if result.get("status") != 1:
                return ChallengeResult(
                    success=False,
                    challenge_type=challenge_type,
                    message=f"2Captcha submit error: {result.get('request')}",
                    time_taken_ms=int((time.time() - start_time) * 1000),
                )
            
            captcha_id = result["request"]
            logger.info(f"[2CAPTCHA] Submitted, ID: {captcha_id}")
            
            # Poll for result
            for _ in range(60):  # Max 2 minutes
                time.sleep(5)
                
                poll_response = requests.get(
                    f"{self.API_URL}/res.php",
                    params={"key": self.api_key, "action": "get", "id": captcha_id, "json": 1},
                    timeout=30,
                )
                poll_result = poll_response.json()
                
                if poll_result.get("status") == 1:
                    token = poll_result["request"]
                    logger.info(f"[2CAPTCHA] Solved, token length: {len(token)}")
                    
                    # Inject token
                    if self._inject_token(page, challenge_type, token):
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        return ChallengeResult(
                            success=True,
                            challenge_type=challenge_type,
                            message="CAPTCHA solved via 2Captcha",
                            time_taken_ms=elapsed_ms,
                        )
                    else:
                        return ChallengeResult(
                            success=False,
                            challenge_type=challenge_type,
                            message="Failed to inject CAPTCHA token",
                            time_taken_ms=int((time.time() - start_time) * 1000),
                        )
                
                elif poll_result.get("request") != "CAPCHA_NOT_READY":
                    return ChallengeResult(
                        success=False,
                        challenge_type=challenge_type,
                        message=f"2Captcha error: {poll_result.get('request')}",
                        time_taken_ms=int((time.time() - start_time) * 1000),
                    )
            
            return ChallengeResult(
                success=False,
                challenge_type=challenge_type,
                message="2Captcha solving timeout",
                time_taken_ms=int((time.time() - start_time) * 1000),
            )
            
        except Exception as e:
            logger.error(f"[2CAPTCHA] Error: {e}")
            return ChallengeResult(
                success=False,
                challenge_type=challenge_type,
                message=f"2Captcha error: {str(e)}",
                time_taken_ms=int((time.time() - start_time) * 1000),
            )
    
    def _inject_token(self, page, challenge_type: ChallengeType, token: str) -> bool:
        """Inject solved token into the page."""
        try:
            if challenge_type == ChallengeType.RECAPTCHA_V2:
                # Inject into g-recaptcha-response textarea
                page.evaluate(f'''
                    document.getElementById("g-recaptcha-response").innerHTML = "{token}";
                    if (typeof ___grecaptcha_cfg !== "undefined") {{
                        Object.keys(___grecaptcha_cfg.clients).forEach(key => {{
                            const client = ___grecaptcha_cfg.clients[key];
                            if (client && client.G && client.G.callback) {{
                                client.G.callback("{token}");
                            }}
                        }});
                    }}
                ''')
                return True
            elif challenge_type == ChallengeType.HCAPTCHA:
                # Inject into h-captcha-response
                page.evaluate(f'''
                    document.querySelector('[name="h-captcha-response"]').value = "{token}";
                    document.querySelector('[name="g-recaptcha-response"]').value = "{token}";
                ''')
                return True
        except Exception as e:
            logger.error(f"Token injection failed: {e}")
        return False


class ChallengeHandler:
    """
    Main handler for detecting and resolving challenges.
    
    Uses a smart strategy selection based on challenge type and configuration.
    """
    
    def __init__(self, strategy: str = "smart"):
        """
        Initialize handler with strategy.
        
        Args:
            strategy: "manual", "auto_wait", "api", or "smart"
        """
        self.strategy = strategy
        self.detector = ChallengeDetector()
        
        # Initialize strategies
        manual_timeout = getattr(settings, 'captcha_manual_timeout', 300)
        api_key = getattr(settings, 'twocaptcha_api_key', '')
        
        self.strategies = {
            "manual": ManualChallengeStrategy(timeout_seconds=manual_timeout),
            "auto_wait": AutoWaitStrategy(timeout_seconds=30),
            "api": TwoCaptchaStrategy(api_key=api_key),
        }
    
    def detect(self, page) -> ChallengeType:
        """Detect challenge on page."""
        return self.detector.detect(page)
    
    def handle(self, page, config: Optional[Dict[str, Any]] = None) -> ChallengeResult:
        """
        Detect and handle any challenge on the page.
        
        Args:
            page: Playwright page object
            config: Optional configuration overrides
            
        Returns:
            ChallengeResult with success status and details
        """
        config = config or {}
        
        # Detect challenge
        challenge_type = self.detect(page)
        
        if challenge_type == ChallengeType.NONE:
            return ChallengeResult(
                success=True,
                challenge_type=ChallengeType.NONE,
                message="No challenge detected",
            )
        
        logger.info(f"[ChallengeHandler] Detected: {challenge_type.value}")
        
        # For Cloudflare challenges - use manual mode directly (Turnstile needs user click)
        if challenge_type in (ChallengeType.CLOUDFLARE_JS, ChallengeType.CLOUDFLARE_CAPTCHA):
            logger.info("[ChallengeHandler] Cloudflare detected - using manual solving mode")
            logger.info("[ChallengeHandler] Please click the Turnstile checkbox in the browser window...")
            return self.strategies["manual"].handle(page, challenge_type, config)
        
        # For other challenges, use selected strategy
        strategy = self._select_strategy(challenge_type, config)
        logger.info(f"[ChallengeHandler] Using strategy: {strategy.__class__.__name__}")
        
        return strategy.handle(page, challenge_type, config)
    
    def _select_strategy(self, challenge_type: ChallengeType, config: Dict[str, Any]) -> ChallengeStrategy:
        """Select appropriate strategy based on challenge type and configuration."""
        strategy_override = config.get("captcha_strategy", self.strategy)
        
        if strategy_override == "smart":
            # Smart selection based on challenge type
            if challenge_type == ChallengeType.CLOUDFLARE_JS:
                # JS challenges auto-resolve
                return self.strategies["auto_wait"]
            elif challenge_type in (ChallengeType.RECAPTCHA_V2, ChallengeType.HCAPTCHA):
                # Use API if available, else manual
                if self.strategies["api"].api_key:
                    return self.strategies["api"]
                return self.strategies["manual"]
            elif challenge_type == ChallengeType.CLOUDFLARE_CAPTCHA:
                # Cloudflare CAPTCHA - try auto-wait first (sometimes passes), then manual
                return self.strategies["auto_wait"]
            else:
                # Default to manual for unknown/login/rate-limit
                return self.strategies["manual"]
        else:
            return self.strategies.get(strategy_override, self.strategies["manual"])
    
    def wait_for_challenge_resolution(
        self,
        page,
        timeout_seconds: int = 60,
        check_interval: float = 2.0,
    ) -> bool:
        """
        Wait for any challenge to be resolved.
        
        Useful after manual solving to verify challenge is complete.
        
        Returns:
            True if no challenge detected, False on timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            if self.detect(page) == ChallengeType.NONE:
                return True
            time.sleep(check_interval)
        
        return False
