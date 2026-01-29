"""Google SGE/AI Overview engine adapter."""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.browser.playwright_manager import PlaywrightManager
from app.browser.human_simulator import HumanSimulator
from app.config import settings
from app.engines.base import BaseEngine


class GoogleSGEEngine(BaseEngine):
    """Google SGE/AI Overview crawler adapter."""
    
    name = "google_sge"
    base_url = "https://www.google.com"
    
    async def crawl(
        self,
        query: str,
        browser_manager: PlaywrightManager,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Crawl Google for SGE/AI Overview results."""
        config = config or {}
        page = await browser_manager.new_page()
        simulator = HumanSimulator(page)
        
        try:
            # Navigate to Google
            await page.goto(self.base_url)
            await simulator.random_delay(1000, 2000)
            
            # Find search input
            search_selector = 'textarea[name="q"], input[name="q"]'
            await page.wait_for_selector(search_selector, timeout=10000)
            
            # Type query
            await simulator.type_text(search_selector, query)
            await simulator.random_delay(500, 1000)
            
            # Submit
            await page.keyboard.press("Enter")
            
            # Wait for results
            await page.wait_for_load_state("networkidle")
            await simulator.random_delay(2000, 4000)
            
            # Check for AI Overview / SGE
            ai_selectors = [
                '[data-attrid="SGEAnswer"]',
                '[class*="AI Overview"]',
                '[jsname*="sge"]',
                'div[data-hveid] [data-md]',  # AI generated content marker
            ]
            
            ai_content_found = False
            for selector in ai_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        ai_content_found = True
                        break
                except Exception:
                    pass
            
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
                "has_ai_overview": ai_content_found,
            }
        finally:
            await page.close()
    
    async def parse_response(self, page_content: str) -> Dict[str, Any]:
        """Parse Google SGE response page."""
        soup = BeautifulSoup(page_content, "lxml")
        
        # Try to extract AI Overview content
        response_text = ""
        
        # Multiple possible selectors for AI content
        ai_selectors = [
            '[data-attrid="SGEAnswer"]',
            '[class*="sge"]',
            'div[data-md]',  # Markdown content
        ]
        
        for selector in ai_selectors:
            elements = soup.select(selector)
            if elements:
                response_text = "\n".join(
                    el.get_text(strip=True, separator="\n") for el in elements
                )
                if response_text:
                    break
        
        # Extract citations from AI Overview sources
        citations = []
        
        # AI Overview source links
        source_selectors = [
            '[data-attrid="SGEAnswer"] a[href]',
            '[class*="sge"] a[href*="http"]',
        ]
        
        seen_urls = set()
        for selector in source_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get("href", "")
                # Clean Google redirect URLs
                if "/url?q=" in href:
                    href = href.split("/url?q=")[1].split("&")[0]
                
                if href and href.startswith("http") and href not in seen_urls:
                    seen_urls.add(href)
                    citations.append({
                        "position": len(citations) + 1,
                        "url": href,
                        "title": link.get_text(strip=True),
                        "source": "google_sge",
                    })
        
        # Also get regular search results as potential citations
        search_results = soup.select('div.g a[href]')
        for link in search_results[:10]:  # Top 10 results
            href = link.get("href", "")
            if href.startswith("http") and href not in seen_urls:
                seen_urls.add(href)
                citations.append({
                    "position": len(citations) + 1,
                    "url": href,
                    "title": link.get_text(strip=True),
                    "source": "google_organic",
                })
        
        return {
            "response_text": response_text,
            "citations": citations,
        }
