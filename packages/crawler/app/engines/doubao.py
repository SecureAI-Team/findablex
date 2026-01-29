"""Doubao (豆包) AI engine adapter."""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.browser.playwright_manager import PlaywrightManager
from app.browser.human_simulator import HumanSimulator
from app.config import settings
from app.engines.base import BaseEngine


class DoubaoEngine(BaseEngine):
    """Doubao (豆包) AI crawler adapter - ByteDance product."""
    
    name = "doubao"
    base_url = "https://www.doubao.com/chat"
    
    async def crawl(
        self,
        query: str,
        browser_manager: PlaywrightManager,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl Doubao for a query."""
        config = config or {}
        page = await browser_manager.new_page()
        simulator = HumanSimulator(page)
        
        try:
            # Navigate to Doubao
            await page.goto(self.base_url)
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
            
            # Find input area - Doubao uses textarea or contenteditable
            input_selectors = [
                'textarea[placeholder*="输入"]',
                'textarea[placeholder*="问"]',
                'textarea[placeholder*="聊"]',
                '[contenteditable="true"]',
                'textarea',
                '#chat-input',
                '[class*="input"] textarea',
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = await page.wait_for_selector(
                        selector, timeout=5000
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
            
            # Type query with human-like behavior
            await input_element.click()
            await simulator.random_delay(300, 600)
            
            # Clear any existing text
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Backspace")
            await simulator.random_delay(200, 400)
            
            # Type the query
            await page.keyboard.type(query)
            await simulator.random_delay(500, 1000)
            
            # Find and click send button
            send_selectors = [
                'button[type="submit"]',
                '[class*="send"]',
                '[class*="submit"]',
                '[aria-label*="发送"]',
                'button[class*="btn"]',
                '[data-testid*="send"]',
            ]
            
            sent = False
            for selector in send_selectors:
                try:
                    send_btn = await page.query_selector(selector)
                    if send_btn and await send_btn.is_visible():
                        await send_btn.click()
                        sent = True
                        break
                except Exception:
                    pass
            
            if not sent:
                await page.keyboard.press("Enter")
            
            # Wait for response to generate
            await simulator.random_delay(3000, 5000)
            
            # Wait for response completion
            try:
                await page.wait_for_function(
                    """() => {
                        const loading = document.querySelector('[class*="loading"], [class*="typing"]');
                        return !loading || loading.offsetParent === null;
                    }""",
                    timeout=60000
                )
            except Exception:
                pass
            
            await simulator.random_delay(1000, 2000)
            
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
    
    async def _check_login_required(self, page) -> bool:
        """Check if login is required."""
        login_indicators = [
            '[class*="login"]',
            '[class*="sign-in"]',
            'button:has-text("登录")',
            'button:has-text("登陆")',
            '[class*="qrcode"]',  # QR code login
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
        """Parse Doubao response page."""
        soup = BeautifulSoup(page_content, "lxml")
        
        # Extract response text
        response_text = ""
        
        # ByteDance products typically use these patterns
        response_selectors = [
            '[class*="message"][class*="assistant"]',
            '[class*="message"][class*="bot"]',
            '[class*="chat-message"][class*="receive"]',
            '[class*="response"]',
            '[class*="answer"]',
            '[class*="markdown"]',
            '[class*="content"][class*="bot"]',
        ]
        
        for selector in response_selectors:
            elements = soup.select(selector)
            if elements:
                # Get the last response (most recent)
                response_text = elements[-1].get_text(strip=True, separator="\n")
                if response_text:
                    break
        
        # Extract citations
        citations = []
        
        # Look for reference links
        citation_selectors = [
            '[class*="reference"] a',
            '[class*="source"] a',
            '[class*="link"] a[href*="http"]',
            '[class*="cite"] a',
        ]
        
        seen_urls = set()
        for selector in citation_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get("href", "")
                if href and href.startswith("http") and href not in seen_urls:
                    # Skip Doubao internal links
                    if "doubao.com" not in href and "bytedance" not in href:
                        seen_urls.add(href)
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": link.get_text(strip=True) or href,
                            "source": "doubao",
                        })
        
        return {
            "response_text": response_text,
            "citations": citations,
        }
