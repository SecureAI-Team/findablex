"""Base engine adapter class."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.browser.playwright_manager import PlaywrightManager


class BaseEngine(ABC):
    """Base class for search engine adapters."""
    
    name: str = "base"
    base_url: str = ""
    
    @abstractmethod
    async def crawl(
        self,
        query: str,
        browser_manager: PlaywrightManager,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Crawl a query on this engine.
        
        Returns:
            {
                "query": str,
                "response_text": str,
                "citations": List[Dict],
                "raw_html": str,
                "screenshot_path": str,
                "crawled_at": str,
                "engine": str,
            }
        """
        pass
    
    @abstractmethod
    async def parse_response(self, page_content: str) -> Dict[str, Any]:
        """
        Parse the page content to extract response and citations.
        
        Returns:
            {
                "response_text": str,
                "citations": List[Dict],
            }
        """
        pass
    
    async def take_screenshot(
        self,
        page,
        query: str,
        output_dir: str,
    ) -> str:
        """Take a screenshot of the page."""
        import os
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in query[:30] if c.isalnum() or c in " -_")
        filename = f"{self.name}_{safe_query}_{timestamp}.png"
        filepath = os.path.join(output_dir, filename)
        
        await page.screenshot(path=filepath, full_page=True)
        return filepath
