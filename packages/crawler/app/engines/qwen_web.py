"""Qwen (通义千问) web crawler adapter."""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.browser.playwright_manager import PlaywrightManager
from app.browser.human_simulator import HumanSimulator
from app.config import settings
from app.engines.base import BaseEngine


class QwenWebEngine(BaseEngine):
    """Qwen (通义千问) web crawler adapter."""
    
    name = "qwen"
    base_url = "https://tongyi.aliyun.com/qianwen"
    
    async def crawl(
        self,
        query: str,
        browser_manager: PlaywrightManager,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl Qwen web interface."""
        config = config or {}
        page = await browser_manager.new_page()
        simulator = HumanSimulator(page)
        
        try:
            # Navigate to Qwen
            await page.goto(self.base_url)
            await simulator.random_delay(2000, 3000)
            
            # Check for login requirement
            # Note: Qwen might require login for full functionality
            
            # Find input area
            input_selectors = [
                'textarea',
                '[contenteditable="true"]',
                'input[type="text"]',
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
            
            # Type query
            await input_element.click()
            await simulator.random_delay(500, 1000)
            await page.keyboard.type(query)
            await simulator.random_delay(500, 1000)
            
            # Find and click send button
            send_selectors = [
                'button[type="submit"]',
                '[class*="send"]',
                '[aria-label*="发送"]',
            ]
            
            for selector in send_selectors:
                try:
                    send_btn = await page.query_selector(selector)
                    if send_btn:
                        await send_btn.click()
                        break
                except Exception:
                    pass
            
            # Wait for response
            await simulator.random_delay(5000, 10000)
            
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
    
    async def parse_response(self, page_content: str) -> Dict[str, Any]:
        """Parse Qwen response page."""
        soup = BeautifulSoup(page_content, "lxml")
        
        # Extract response text
        response_text = ""
        
        # Possible response container selectors
        response_selectors = [
            '[class*="message"][class*="assistant"]',
            '[class*="response"]',
            '[class*="answer"]',
            '[class*="markdown"]',
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
        link_selectors = [
            '[class*="reference"] a',
            '[class*="source"] a',
            '[class*="citation"] a',
        ]
        
        for selector in link_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get("href", "")
                if href and href.startswith("http"):
                    citations.append({
                        "position": len(citations) + 1,
                        "url": href,
                        "title": link.get_text(strip=True),
                        "source": "qwen",
                    })
        
        return {
            "response_text": response_text,
            "citations": citations,
        }
