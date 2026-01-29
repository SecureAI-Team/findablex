"""Engine adapters for different AI search engines."""
from typing import Dict, Optional, Type

from app.engines.base import BaseEngine
from app.engines.perplexity import PerplexityEngine
from app.engines.google_sge import GoogleSGEEngine
from app.engines.qwen_web import QwenWebEngine
from app.engines.deepseek import DeepSeekEngine
from app.engines.doubao import DoubaoEngine
from app.engines.kimi import KimiEngine
from app.engines.chatglm import ChatGLMEngine
from app.engines.chatgpt import ChatGPTEngine


class EngineFactory:
    """Factory for creating engine instances."""
    
    _engines: Dict[str, Type[BaseEngine]] = {
        # International
        "perplexity": PerplexityEngine,
        "google_sge": GoogleSGEEngine,
        "chatgpt": ChatGPTEngine,
        # China
        "qwen": QwenWebEngine,
        "deepseek": DeepSeekEngine,
        "doubao": DoubaoEngine,
        "kimi": KimiEngine,
        "chatglm": ChatGLMEngine,
    }
    
    @classmethod
    def get(cls, engine_name: str) -> Optional[BaseEngine]:
        """Get an engine instance by name."""
        engine_class = cls._engines.get(engine_name)
        if engine_class:
            return engine_class()
        return None
    
    @classmethod
    def register(cls, name: str, engine_class: Type[BaseEngine]):
        """Register a new engine."""
        cls._engines[name] = engine_class
    
    @classmethod
    def list_engines(cls) -> list:
        """List all available engines."""
        return list(cls._engines.keys())
