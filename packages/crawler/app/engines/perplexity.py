"""Perplexity AI engine adapter."""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.browser.playwright_manager import PlaywrightManager
from app.browser.human_simulator import HumanSimulator
from app.config import settings
from app.engines.base import BaseEngine


class PerplexityEngine(BaseEngine):
    """Perplexity AI crawler adapter."""
    
    name = "perplexity"
    base_url = "https://www.perplexity.ai"
    
    async def crawl(
        self,
        query: str,
        browser_manager: PlaywrightManager,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl Perplexity for a query."""
        config = config or {}
        page = await browser_manager.new_page()
        simulator = HumanSimulator(page)
        
        try:
            # Navigate to Perplexity
            await page.goto(self.base_url)
            await simulator.random_delay(1000, 2000)
            
            # Find search input
            search_selector = 'textarea[placeholder*="Ask"]'
            await page.wait_for_selector(search_selector, timeout=10000)
            
            # Type query with human-like behavior
            await simulator.type_text(search_selector, query)
            await simulator.random_delay(500, 1000)
            
            # Submit query
            await page.keyboard.press("Enter")
            
            # Wait for response
            response_selector = '[class*="prose"]'
            await page.wait_for_selector(response_selector, timeout=30000)
            
            # Wait for response to fully load
            await simulator.random_delay(3000, 5000)
            
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
        """Parse Perplexity response page."""
        soup = BeautifulSoup(page_content, "lxml")
        
        # Extract response text
        response_text = ""
        response_divs = soup.select('[class*="prose"]')
        if response_divs:
            response_text = response_divs[-1].get_text(strip=True, separator="\n")
        
        # Extract citations
        citations = []
        citation_links = soup.select('[class*="citation"], [class*="source"] a')
        
        for i, link in enumerate(citation_links):
            href = link.get("href", "")
            title = link.get_text(strip=True)
            
            if href and not href.startswith("javascript:"):
                citations.append({
                    "position": i + 1,
                    "url": href,
                    "title": title,
                    "source": "perplexity",
                })
        
        return {
            "response_text": response_text,
            "citations": citations,
        }
