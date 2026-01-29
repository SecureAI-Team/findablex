"""ChatGPT (OpenAI) engine adapter."""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.browser.playwright_manager import PlaywrightManager
from app.browser.human_simulator import HumanSimulator
from app.config import settings
from app.engines.base import BaseEngine


class ChatGPTEngine(BaseEngine):
    """ChatGPT (OpenAI) crawler adapter - Most complex anti-detection."""
    
    name = "chatgpt"
    base_url = "https://chat.openai.com"
    
    async def crawl(
        self,
        query: str,
        browser_manager: PlaywrightManager,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl ChatGPT for a query."""
        config = config or {}
        page = await browser_manager.new_page()
        simulator = HumanSimulator(page)
        
        try:
            # Session warmup for ChatGPT (helps avoid detection)
            if config.get("warmup", True):
                await simulator.session_warmup()
            
            # Navigate to ChatGPT
            await page.goto(self.base_url)
            await simulator.random_delay(3000, 5000)
            
            # Check for Cloudflare or other challenges
            challenge_detected = await self._check_challenge(page)
            if challenge_detected:
                # Wait for manual solving or timeout
                await simulator.wait_for_human_verification(timeout=60000)
                await simulator.random_delay(2000, 3000)
            
            # Check for login requirement
            login_required = await self._check_login_required(page)
            if login_required:
                return {
                    "query": query,
                    "response_text": "",
                    "citations": [],
                    "error": "Login required. Please configure cookies.",
                    "engine": self.name,
                    "login_required": True,
                }
            
            # Find input area - ChatGPT uses a specific prompt textarea
            input_selectors = [
                '#prompt-textarea',
                'textarea[placeholder*="Message"]',
                'textarea[placeholder*="Send"]',
                'textarea[data-id="root"]',
                '[contenteditable="true"]',
                'textarea',
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = await page.wait_for_selector(
                        selector, timeout=10000
                    )
                    if input_element:
                        break
                except Exception:
                    pass
            
            if not input_element:
                return {
                    "query": query,
                    "response_text": "",
                    "citations": [],
                    "error": "Could not find input element",
                    "engine": self.name,
                }
            
            # Type query with very human-like behavior (ChatGPT has sophisticated detection)
            await input_element.click()
            await simulator.random_delay(500, 1000)
            
            # Random mouse movement before typing
            await simulator.random_mouse_movement()
            await simulator.random_delay(300, 600)
            
            # Type with variable speed
            await simulator.type_text('#prompt-textarea, textarea', query)
            await simulator.random_delay(500, 1500)
            
            # Find and click send button
            send_selectors = [
                'button[data-testid="send-button"]',
                'button[data-testid="fruitjuice-send-button"]',
                '[class*="send"]',
                'button[type="submit"]',
                'button:has(svg)',  # Button with icon
            ]
            
            sent = False
            for selector in send_selectors:
                try:
                    send_btn = await page.query_selector(selector)
                    if send_btn:
                        # Check if button is enabled
                        is_disabled = await send_btn.get_attribute("disabled")
                        if not is_disabled:
                            await send_btn.click()
                            sent = True
                            break
                except Exception:
                    pass
            
            if not sent:
                # Try Enter key
                await page.keyboard.press("Enter")
            
            # Wait for response to start generating
            await simulator.random_delay(2000, 4000)
            
            # Wait for response completion (ChatGPT shows streaming text)
            try:
                # Wait for the "stop generating" button to appear then disappear
                await page.wait_for_function(
                    """() => {
                        const stopBtn = document.querySelector('[data-testid="stop-button"], button[aria-label*="Stop"]');
                        const thinking = document.querySelector('[class*="thinking"], [class*="result-streaming"]');
                        return (!stopBtn || stopBtn.offsetParent === null) && (!thinking || thinking.offsetParent === null);
                    }""",
                    timeout=120000
                )
            except Exception:
                pass
            
            await simulator.random_delay(2000, 3000)
            
            # Get page content
            html_content = await page.content()
            
            # Parse response
            parsed = await self.parse_response(html_content)
            
            # Take screenshot
            screenshot_path = ""
            if config.get("take_screenshot", True):
                screenshot_path = await self.take_screenshot(
                    page, query, settings.screenshot_dir
                )
            
            return {
                "query": query,
                "response_text": parsed.get("response_text", ""),
                "citations": parsed.get("citations", []),
                "raw_html": html_content,
                "screenshot_path": screenshot_path,
                "crawled_at": datetime.utcnow().isoformat(),
                "engine": self.name,
            }
        finally:
            await page.close()
    
    async def _check_challenge(self, page) -> bool:
        """Check for Cloudflare or other challenges."""
        challenge_indicators = [
            'iframe[src*="challenges"]',
            '[class*="cloudflare"]',
            '#challenge-running',
            '[class*="captcha"]',
        ]
        
        for selector in challenge_indicators:
            try:
                element = await page.query_selector(selector)
                if element:
                    return True
            except Exception:
                pass
        
        return False
    
    async def _check_login_required(self, page) -> bool:
        """Check if login is required."""
        login_indicators = [
            'button:has-text("Log in")',
            'button:has-text("Sign up")',
            '[class*="login"]',
            '[data-testid="login-button"]',
            'a[href*="auth"]',
        ]
        
        for selector in login_indicators:
            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    return True
            except Exception:
                pass
        
        return False
    
    async def parse_response(self, page_content: str) -> Dict[str, Any]:
        """Parse ChatGPT response page."""
        soup = BeautifulSoup(page_content, "lxml")
        
        # Extract response text
        response_text = ""
        
        # ChatGPT response selectors
        response_selectors = [
            '[data-message-author-role="assistant"]',
            '[class*="agent-turn"]',
            '[class*="markdown"]',
            '[class*="prose"]',
            '[class*="message"][class*="assistant"]',
        ]
        
        for selector in response_selectors:
            elements = soup.select(selector)
            if elements:
                # Get the last response (most recent)
                response_text = elements[-1].get_text(strip=True, separator="\n")
                if response_text:
                    break
        
        # Extract citations - ChatGPT with browsing shows sources
        citations = []
        
        citation_selectors = [
            '[class*="citation"] a',
            '[class*="source"] a',
            '[class*="reference"] a',
            'a[href*="http"][target="_blank"]',
        ]
        
        seen_urls = set()
        for selector in citation_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get("href", "")
                if href and href.startswith("http") and href not in seen_urls:
                    # Skip OpenAI internal links
                    if "openai.com" not in href and "chat.openai" not in href:
                        seen_urls.add(href)
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": link.get_text(strip=True) or href,
                            "source": "chatgpt",
                        })
        
        # Also look for browsing results panel
        browsing_results = soup.select('[class*="browsing"], [class*="web-result"]')
        for result in browsing_results:
            link = result.select_one('a[href]')
            if link:
                href = link.get("href", "")
                if href and href.startswith("http") and href not in seen_urls:
                    seen_urls.add(href)
                    title_el = result.select_one('[class*="title"]')
                    citations.append({
                        "position": len(citations) + 1,
                        "url": href,
                        "title": title_el.get_text(strip=True) if title_el else href,
                        "source": "chatgpt",
                    })
        
        return {
            "response_text": response_text,
            "citations": citations,
        }
