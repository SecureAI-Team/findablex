"""
API-based crawler service - uses AI provider APIs instead of browser automation.

Supports:
- DeepSeek (deepseek.com) - OpenAI compatible API with web search
- Qwen/通义千问 (dashscope.aliyuncs.com) - Alibaba's DashScope API
- Kimi (moonshot.cn) - Moonshot AI API
- Perplexity (perplexity.ai) - pplx API with built-in search
- ChatGPT (openai.com) - OpenAI API

These APIs can run on headless servers without browser requirements.
"""
import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx

from app.config import dynamic
from app.services.credential_service import CredentialService

logger = logging.getLogger(__name__)


class APIEngineBase(ABC):
    """Base class for API-based AI engines."""
    
    name: str = ""
    display_name: str = ""
    api_base_url: str = ""
    supports_web_search: bool = False
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    @abstractmethod
    async def query(
        self,
        question: str,
        enable_web_search: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a query and return the result.
        
        Returns:
            {
                "response_text": str,      # AI's answer
                "citations": list,          # List of cited sources
                "model": str,               # Model used
                "response_time_ms": int,    # Response time
                "tokens_used": int,         # Token count (if available)
                "raw_response": dict,       # Raw API response for debugging
            }
        """
        pass
    
    def _extract_urls_from_text(self, text: str) -> List[Dict[str, str]]:
        """Extract URLs from text and create citation objects."""
        # URL regex pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\])]+'
        urls = re.findall(url_pattern, text)
        
        citations = []
        seen_urls = set()
        
        for url in urls:
            # Clean URL (remove trailing punctuation)
            url = url.rstrip('.,;:!?')
            
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Extract domain
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc
            except:
                domain = url.split('/')[2] if '/' in url else url
            
            citations.append({
                "position": len(citations) + 1,
                "url": url,
                "title": domain,
                "domain": domain,
                "source": self.name,
            })
        
        return citations


class DeepSeekAPIEngine(APIEngineBase):
    """
    DeepSeek API engine with web search support.
    
    API Docs: https://platform.deepseek.com/api-docs
    """
    
    name = "deepseek_api"
    display_name = "DeepSeek (API)"
    api_base_url = "https://api.deepseek.com/v1"
    supports_web_search = True
    
    async def query(
        self,
        question: str,
        enable_web_search: bool = True,
    ) -> Dict[str, Any]:
        """Execute query using DeepSeek API."""
        start_time = datetime.now(timezone.utc)
        
        # DeepSeek uses OpenAI-compatible API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # System prompt to encourage citation-style responses
        system_prompt = """你是一个专业的信息检索助手。请根据用户的问题提供准确、详细的回答。
如果你引用了网络信息，请在回答中包含相关的来源链接。
回答格式要求：
1. 先给出直接答案
2. 然后提供详细解释
3. 如果有相关来源，请列出"""
        
        if enable_web_search:
            system_prompt += "\n请搜索最新的网络信息来回答问题。"
        
        payload = {
            "model": "deepseek-chat",  # or deepseek-coder for code questions
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": False,
        }
        
        # Note: DeepSeek's web search is enabled by default for certain queries
        # For explicit web search, use deepseek-search model when available
        
        try:
            response = await self.client.post(
                f"{self.api_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Extract response text
            response_text = ""
            if data.get("choices"):
                response_text = data["choices"][0].get("message", {}).get("content", "")
            
            # Extract citations from response text
            citations = self._extract_urls_from_text(response_text)
            
            # Token usage
            tokens_used = 0
            if data.get("usage"):
                tokens_used = data["usage"].get("total_tokens", 0)
            
            return {
                "response_text": response_text,
                "citations": citations,
                "model": data.get("model", "deepseek-chat"),
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used,
                "raw_response": data,
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[DeepSeek API] HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[DeepSeek API] Error: {e}")
            raise


class QwenAPIEngine(APIEngineBase):
    """
    Qwen (通义千问) API engine via Alibaba DashScope.
    
    API Docs: https://help.aliyun.com/document_detail/2712576.html
    """
    
    name = "qwen_api"
    display_name = "通义千问 (API)"
    api_base_url = "https://dashscope.aliyuncs.com/api/v1"
    supports_web_search = True
    
    async def query(
        self,
        question: str,
        enable_web_search: bool = True,
    ) -> Dict[str, Any]:
        """Execute query using Qwen DashScope API."""
        start_time = datetime.now(timezone.utc)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # System prompt
        system_prompt = """你是通义千问，一个由阿里云开发的AI助手。
请根据用户的问题提供准确、详细的回答。如果引用了信息来源，请包含链接。"""
        
        payload = {
            "model": "qwen-max",  # or qwen-turbo, qwen-plus
            "input": {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ]
            },
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 4096,
                "result_format": "message",
            }
        }
        
        # Enable web search if supported
        if enable_web_search:
            payload["parameters"]["enable_search"] = True
        
        try:
            response = await self.client.post(
                f"{self.api_base_url}/services/aigc/text-generation/generation",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Extract response text (DashScope format)
            response_text = ""
            if data.get("output", {}).get("choices"):
                response_text = data["output"]["choices"][0].get("message", {}).get("content", "")
            elif data.get("output", {}).get("text"):
                response_text = data["output"]["text"]
            
            # Extract citations
            citations = self._extract_urls_from_text(response_text)
            
            # Check for search results in response
            if data.get("output", {}).get("search_info"):
                for idx, item in enumerate(data["output"]["search_info"].get("search_results", [])):
                    citations.append({
                        "position": len(citations) + 1,
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "domain": item.get("site_name", ""),
                        "source": "qwen_api",
                    })
            
            # Token usage
            tokens_used = 0
            if data.get("usage"):
                tokens_used = data["usage"].get("total_tokens", 0)
            
            return {
                "response_text": response_text,
                "citations": citations,
                "model": data.get("model", "qwen-max"),
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used,
                "raw_response": data,
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[Qwen API] HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[Qwen API] Error: {e}")
            raise


class KimiAPIEngine(APIEngineBase):
    """
    Kimi (Moonshot AI) API engine.
    
    API Docs: https://platform.moonshot.cn/docs/api-reference
    """
    
    name = "kimi_api"
    display_name = "Kimi (API)"
    api_base_url = "https://api.moonshot.cn/v1"
    supports_web_search = True
    
    async def query(
        self,
        question: str,
        enable_web_search: bool = True,
    ) -> Dict[str, Any]:
        """Execute query using Kimi/Moonshot API."""
        start_time = datetime.now(timezone.utc)
        
        # Kimi uses OpenAI-compatible API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # System prompt
        system_prompt = """你是 Kimi，由 Moonshot AI 提供的人工智能助手。
请根据用户的问题提供准确、详细的回答。如果需要，请搜索网络获取最新信息，并在回答中包含信息来源。"""
        
        payload = {
            "model": "moonshot-v1-128k",  # or moonshot-v1-8k, moonshot-v1-32k
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": False,
        }
        
        # Kimi supports web search via special model or tool
        if enable_web_search:
            # Use web search tool if available
            payload["tools"] = [
                {
                    "type": "web_search",
                    "web_search": {
                        "enable": True,
                    }
                }
            ]
        
        try:
            response = await self.client.post(
                f"{self.api_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Extract response text
            response_text = ""
            if data.get("choices"):
                response_text = data["choices"][0].get("message", {}).get("content", "")
            
            # Extract citations from response text
            citations = self._extract_urls_from_text(response_text)
            
            # Check for tool call results (web search)
            if data.get("choices"):
                tool_calls = data["choices"][0].get("message", {}).get("tool_calls", [])
                for tool_call in tool_calls:
                    if tool_call.get("type") == "web_search":
                        results = tool_call.get("web_search", {}).get("results", [])
                        for item in results:
                            citations.append({
                                "position": len(citations) + 1,
                                "url": item.get("url", ""),
                                "title": item.get("title", ""),
                                "domain": item.get("host", ""),
                                "source": "kimi_api",
                            })
            
            # Token usage
            tokens_used = 0
            if data.get("usage"):
                tokens_used = data["usage"].get("total_tokens", 0)
            
            return {
                "response_text": response_text,
                "citations": citations,
                "model": data.get("model", "moonshot-v1-128k"),
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used,
                "raw_response": data,
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[Kimi API] HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[Kimi API] Error: {e}")
            raise


class PerplexityAPIEngine(APIEngineBase):
    """
    Perplexity API engine with built-in web search.
    
    API Docs: https://docs.perplexity.ai/reference/post_chat_completions
    """
    
    name = "perplexity_api"
    display_name = "Perplexity (API)"
    api_base_url = "https://api.perplexity.ai"
    supports_web_search = True  # Always has web search
    
    async def query(
        self,
        question: str,
        enable_web_search: bool = True,
    ) -> Dict[str, Any]:
        """Execute query using Perplexity API."""
        start_time = datetime.now(timezone.utc)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Perplexity-specific models
        # - llama-3.1-sonar-small-128k-online: Fast, with search
        # - llama-3.1-sonar-large-128k-online: Better quality, with search
        # - llama-3.1-sonar-huge-128k-online: Best quality, with search
        
        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {"role": "user", "content": question},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
            "return_citations": True,  # Request citations
            "return_related_questions": False,
        }
        
        try:
            response = await self.client.post(
                f"{self.api_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Extract response text
            response_text = ""
            if data.get("choices"):
                response_text = data["choices"][0].get("message", {}).get("content", "")
            
            # Extract citations from API response
            citations = []
            if data.get("citations"):
                for idx, url in enumerate(data["citations"]):
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        domain = parsed.netloc
                    except:
                        domain = url
                    
                    citations.append({
                        "position": idx + 1,
                        "url": url,
                        "title": domain,
                        "domain": domain,
                        "source": "perplexity_api",
                    })
            
            # Also extract URLs from text
            text_citations = self._extract_urls_from_text(response_text)
            for c in text_citations:
                if c["url"] not in [x["url"] for x in citations]:
                    c["position"] = len(citations) + 1
                    citations.append(c)
            
            # Token usage
            tokens_used = 0
            if data.get("usage"):
                tokens_used = data["usage"].get("total_tokens", 0)
            
            return {
                "response_text": response_text,
                "citations": citations,
                "model": data.get("model", "llama-3.1-sonar-large-128k-online"),
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used,
                "raw_response": data,
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[Perplexity API] HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[Perplexity API] Error: {e}")
            raise


class ChatGPTAPIEngine(APIEngineBase):
    """
    ChatGPT (OpenAI) API engine.
    
    API Docs: https://platform.openai.com/docs/api-reference
    """
    
    name = "chatgpt_api"
    display_name = "ChatGPT (API)"
    api_base_url = "https://api.openai.com/v1"
    supports_web_search = False  # Native ChatGPT doesn't have web search
    
    async def query(
        self,
        question: str,
        enable_web_search: bool = True,
    ) -> Dict[str, Any]:
        """Execute query using OpenAI API."""
        start_time = datetime.now(timezone.utc)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # System prompt
        system_prompt = """You are ChatGPT, a helpful AI assistant.
Please provide accurate and detailed answers to the user's questions.
If you reference any information sources, please include the URLs."""
        
        payload = {
            "model": "gpt-4o",  # or gpt-4o-mini, gpt-4-turbo
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        
        try:
            response = await self.client.post(
                f"{self.api_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Extract response text
            response_text = ""
            if data.get("choices"):
                response_text = data["choices"][0].get("message", {}).get("content", "")
            
            # Extract citations from response text
            citations = self._extract_urls_from_text(response_text)
            
            # Token usage
            tokens_used = 0
            if data.get("usage"):
                tokens_used = data["usage"].get("total_tokens", 0)
            
            return {
                "response_text": response_text,
                "citations": citations,
                "model": data.get("model", "gpt-4o"),
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used,
                "raw_response": data,
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[ChatGPT API] HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"[ChatGPT API] Error: {e}")
            raise


# ============================================================================
# API Engine Registry
# ============================================================================

API_ENGINES = {
    "deepseek_api": DeepSeekAPIEngine,
    "qwen_api": QwenAPIEngine,
    "kimi_api": KimiAPIEngine,
    "perplexity_api": PerplexityAPIEngine,
    "chatgpt_api": ChatGPTAPIEngine,
}

# Map web crawler engine names to API engine names
WEB_TO_API_ENGINE_MAP = {
    "deepseek": "deepseek_api",
    "qwen": "qwen_api",
    "kimi": "kimi_api",
    "perplexity": "perplexity_api",
    "chatgpt": "chatgpt_api",
}

# API key configuration keys (for dynamic settings)
API_KEY_CONFIG = {
    "deepseek_api": "ai.deepseek_api_key",
    "qwen_api": "ai.qwen_api_key",
    "kimi_api": "ai.kimi_api_key",
    "perplexity_api": "ai.perplexity_api_key",
    "chatgpt_api": "ai.openai_api_key",
}


class APICrawlerService:
    """
    Service for executing crawler tasks via API instead of browser automation.
    
    Benefits:
    - No browser required (works on headless servers)
    - Faster execution
    - More reliable (no DOM parsing issues)
    - Lower resource usage
    
    Limitations:
    - Requires API keys
    - Some engines may have different response formats
    - Rate limits apply
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self._engines: Dict[str, APIEngineBase] = {}
    
    async def get_engine(
        self,
        engine_name: str,
        workspace_id: Optional[UUID] = None,
    ) -> Optional[APIEngineBase]:
        """
        Get an API engine instance with configured API key.
        
        Priority for API key:
        1. Workspace-level credential (if workspace_id provided)
        2. Platform-level dynamic setting
        """
        # Map web engine name to API engine name if needed
        api_engine_name = WEB_TO_API_ENGINE_MAP.get(engine_name, engine_name)
        
        if api_engine_name not in API_ENGINES:
            logger.warning(f"[API Crawler] Engine not supported: {engine_name}")
            return None
        
        # Check cache
        cache_key = f"{api_engine_name}:{workspace_id or 'platform'}"
        if cache_key in self._engines:
            return self._engines[cache_key]
        
        # Get API key
        api_key = None
        
        # Try workspace credential first
        if workspace_id and self.db:
            try:
                cred_service = CredentialService(self.db)
                cred = await cred_service.get_credential(
                    workspace_id=workspace_id,
                    engine=api_engine_name,
                    credential_type="api_key",
                )
                if cred:
                    api_key = await cred_service.decrypt_credential(cred)
            except Exception as e:
                logger.debug(f"[API Crawler] Failed to get workspace credential: {e}")
        
        # Fall back to platform setting
        if not api_key:
            config_key = API_KEY_CONFIG.get(api_engine_name)
            if config_key:
                api_key = await dynamic.get(config_key)
        
        if not api_key:
            logger.warning(f"[API Crawler] No API key configured for {api_engine_name}")
            return None
        
        # Create engine instance
        engine_class = API_ENGINES[api_engine_name]
        engine = engine_class(api_key)
        
        # Cache it
        self._engines[cache_key] = engine
        
        return engine
    
    async def is_api_available(
        self,
        engine_name: str,
        workspace_id: Optional[UUID] = None,
    ) -> bool:
        """Check if API mode is available for an engine."""
        engine = await self.get_engine(engine_name, workspace_id)
        return engine is not None
    
    async def execute_query(
        self,
        engine_name: str,
        question: str,
        workspace_id: Optional[UUID] = None,
        enable_web_search: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a single query using API.
        
        Returns:
            {
                "success": bool,
                "response_text": str,
                "citations": list,
                "model": str,
                "response_time_ms": int,
                "tokens_used": int,
                "error": str | None,
            }
        """
        engine = await self.get_engine(engine_name, workspace_id)
        
        if not engine:
            return {
                "success": False,
                "response_text": "",
                "citations": [],
                "model": "",
                "response_time_ms": 0,
                "tokens_used": 0,
                "error": f"API engine not available: {engine_name}",
            }
        
        try:
            result = await engine.query(question, enable_web_search)
            return {
                "success": True,
                "response_text": result["response_text"],
                "citations": result["citations"],
                "model": result["model"],
                "response_time_ms": result["response_time_ms"],
                "tokens_used": result["tokens_used"],
                "error": None,
            }
        except Exception as e:
            logger.error(f"[API Crawler] Query failed: {e}")
            return {
                "success": False,
                "response_text": "",
                "citations": [],
                "model": "",
                "response_time_ms": 0,
                "tokens_used": 0,
                "error": str(e),
            }
    
    async def execute_batch(
        self,
        engine_name: str,
        questions: List[str],
        workspace_id: Optional[UUID] = None,
        enable_web_search: bool = True,
        concurrency: int = 3,
        delay_between_requests: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple queries with rate limiting.
        
        Args:
            engine_name: Engine to use
            questions: List of questions
            workspace_id: Optional workspace for credentials
            enable_web_search: Enable web search
            concurrency: Max concurrent requests
            delay_between_requests: Delay between requests (seconds)
        
        Returns:
            List of results
        """
        results = []
        semaphore = asyncio.Semaphore(concurrency)
        
        async def query_with_semaphore(q: str, idx: int) -> Tuple[int, Dict[str, Any]]:
            async with semaphore:
                if idx > 0:
                    await asyncio.sleep(delay_between_requests)
                result = await self.execute_query(
                    engine_name, q, workspace_id, enable_web_search
                )
                return idx, result
        
        # Execute with concurrency limit
        tasks = [
            query_with_semaphore(q, i) 
            for i, q in enumerate(questions)
        ]
        
        completed = await asyncio.gather(*tasks)
        
        # Sort by original order
        completed.sort(key=lambda x: x[0])
        results = [r[1] for r in completed]
        
        return results
    
    async def close(self):
        """Close all engine connections."""
        for engine in self._engines.values():
            await engine.close()
        self._engines.clear()


# ============================================================================
# Helper function for task processing
# ============================================================================

async def should_use_api_mode(
    engine_name: str,
    workspace_id: Optional[UUID] = None,
    db_session=None,
) -> bool:
    """
    Determine if API mode should be used for a given engine.
    
    Returns True if:
    1. Engine supports API mode
    2. API key is configured
    """
    service = APICrawlerService(db_session)
    try:
        return await service.is_api_available(engine_name, workspace_id)
    finally:
        await service.close()
