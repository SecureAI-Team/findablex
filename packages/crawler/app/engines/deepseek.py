"""DeepSeek AI engine adapter."""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.browser.playwright_manager import PlaywrightManager
from app.browser.human_simulator import HumanSimulator
from app.config import settings
from app.engines.base import BaseEngine


class DeepSeekEngine(BaseEngine):
    """DeepSeek AI crawler adapter."""
    
    name = "deepseek"
    base_url = "https://chat.deepseek.com"
    
    async def crawl(
        self,
        query: str,
        browser_manager: PlaywrightManager,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl DeepSeek for a query."""
        config = config or {}
        page = await browser_manager.new_page()
        simulator = HumanSimulator(page)
        
        try:
            # Navigate to DeepSeek
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
            
            # Find input area
            input_selectors = [
                'textarea[placeholder*="输入"]',
                'textarea[placeholder*="问"]',
                'textarea',
                '[contenteditable="true"]',
                '#chat-input',
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
            await simulator.type_text('textarea', query)
            await simulator.random_delay(500, 1000)
            
            # Find and click send button or press Enter
            send_selectors = [
                'button[type="submit"]',
                '[class*="send"]',
                '[aria-label*="发送"]',
                'button[class*="submit"]',
            ]
            
            sent = False
            for selector in send_selectors:
                try:
                    send_btn = await page.query_selector(selector)
                    if send_btn:
                        await send_btn.click()
                        sent = True
                        break
                except Exception:
                    pass
            
            if not sent:
                await page.keyboard.press("Enter")
            
            # Wait for response to generate
            await simulator.random_delay(3000, 5000)
            
            # Wait for response completion (look for stop generating button to disappear)
            try:
                await page.wait_for_function(
                    """() => {
                        const stopBtn = document.querySelector('[class*="stop"], [aria-label*="停止"]');
                        return !stopBtn || stopBtn.offsetParent === null;
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
            'button:has-text("Sign")',
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
        """Parse DeepSeek response page."""
        soup = BeautifulSoup(page_content, "lxml")
        
        # Extract response text
        response_text = ""
        
        # Possible response container selectors for DeepSeek
        response_selectors = [
            '[class*="message"][class*="assistant"]',
            '[class*="markdown-body"]',
            '[class*="response"]',
            '[class*="answer"]',
            '[class*="chat-message"]',
            '.prose',
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
        
        # Look for reference links in response
        citation_selectors = [
            '[class*="reference"] a',
            '[class*="source"] a',
            '[class*="citation"] a',
            '[class*="footnote"] a',
            'a[href*="http"]',
        ]
        
        seen_urls = set()
        for selector in citation_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get("href", "")
                if href and href.startswith("http") and href not in seen_urls:
                    # Skip DeepSeek internal links
                    if "deepseek.com" not in href:
                        seen_urls.add(href)
                        citations.append({
                            "position": len(citations) + 1,
                            "url": href,
                            "title": link.get_text(strip=True) or href,
                            "source": "deepseek",
                        })
        
        return {
            "response_text": response_text,
            "citations": citations,
        }
