from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import asyncio
import time


class BaseProvider(ABC):
    """Base class for public enrichment providers."""

    def __init__(self, name: str, api_key: Optional[str] = None):
        self.name = name
        self.api_key = api_key

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for information about a person or entity.

        Args:
            query: Search query (e.g., person name)
            limit: Maximum number of results to return

        Returns:
            List of result dictionaries with keys: title, snippet, url, confidence, raw
        """
        pass

    @abstractmethod
    async def get_health_status(self) -> str:
        """Return 'healthy', 'degraded', or 'unhealthy'."""
        pass

    async def _make_request(self, url: str, params: Dict[str, Any] = None, headers: Dict[str, Any] = None) -> Dict[str, Any]:
        """Helper method for making HTTP requests with rate limiting."""
        # Placeholder for actual HTTP request logic
        # In real implementation, use aiohttp or httpx
        await asyncio.sleep(0.1)  # Simulate network delay
        return {"results": []}  # Mock response

    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for a result."""
        # Simple confidence based on relevance (override in subclasses)
        return 0.5

    def _redact_sensitive_info(self, text: str) -> str:
        """Redact sensitive information from text."""
        import re
        # Basic redaction patterns
        patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]'),  # SSN
            (r'\b\d{4} \d{4} \d{4} \d{4}\b', '[CARD REDACTED]'),  # Credit card
            # Email
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]'),
            (r'\b\d{10}\b', '[PHONE REDACTED]'),  # Phone
        ]
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        return text
