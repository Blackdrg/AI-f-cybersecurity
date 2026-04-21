from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os
import openai

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
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None

    async def chat_completion(self, messages: List[Dict[str, str]], model: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        if not self.client:
            raise ValueError("OpenAI client not configured")
        
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
