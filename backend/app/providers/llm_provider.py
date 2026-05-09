from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os
import logging

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    @abstractmethod
    async def chat_completion(self, messages: List[Dict[str, str]], model: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Get a chat completion response."""
        pass

    @abstractmethod
    async def get_health_status(self) -> str:
        """Return 'healthy', 'degraded', or 'unhealthy'."""
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI Python package is not installed. Install with: pip install openai")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.air_gapped = os.getenv("AIR_GAPPED", "false").lower() == "true"
        
        if self.air_gapped:
            self.client = None
            logger = logging.getLogger(__name__)
            logger.warning("Air-gapped mode: OpenAI API disabled")
        elif not self.api_key:
            self.client = None
            logger = logging.getLogger(__name__)
            env = os.getenv("ENVIRONMENT", "development")
            if env in ["production", "prod"]:
                logger.error("OPENAI_API_KEY not set in production - AI assistant features will fail")
            else:
                logger.warning("OPENAI_API_KEY not set - AI assistant features will be degraded")
        else:
            self.client = openai.OpenAI(api_key=self.api_key)

    async def chat_completion(self, messages: List[Dict[str, str]], model: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        if self.air_gapped or not self.client:
            raise ValueError("OpenAI client not available (air-gapped mode or missing API key)")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI error: {str(e)}")

    async def get_health_status(self) -> str:
        if not self.api_key:
            return "unconfigured"
        try:
            # Simple check by listing models
            self.client.models.list()
            return "healthy"
        except Exception:
            return "degraded"

class LocalLLMProvider(LLMProvider):
    """Fallback LLM provider when OpenAI is unavailable."""
    async def chat_completion(self, messages: List[Dict[str, str]], model: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        # Mocking a local LLM response
        user_query = messages[-1].get("content", "")
        return f"[LOCAL LLM FALLBACK]: I'm currently working in offline/fallback mode. Regarding your query '{user_query}', please check your OpenAI API key for a more detailed response."

    async def get_health_status(self) -> str:
        return "healthy"  # Local mode is always healthy
