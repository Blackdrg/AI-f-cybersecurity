from typing import List, Dict, Any
import asyncio
import random
from .base import BaseProvider


class MockProvider(BaseProvider):
    """Mock provider for testing and demo purposes."""

    def __init__(self):
        super().__init__("mock")

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return mock search results."""
        await asyncio.sleep(0.2)  # Simulate API delay

        mock_results = [
            {
                "title": f"{query} - Professional Profile",
                "snippet": f"John Doe is a software engineer with 10 years of experience. He specializes in AI and machine learning technologies. Currently working at TechCorp Inc.",
                "url": f"https://example.com/profile/{query.lower().replace(' ', '-')}",
                "confidence": 0.85,
                "raw": {"source": "mock", "type": "profile"}
            },
            {
                "title": f"{query} - LinkedIn",
                "snippet": f"View {query}'s professional profile on LinkedIn. Connect with professionals in your network.",
                "url": f"https://linkedin.com/in/{query.lower().replace(' ', '')}",
                "confidence": 0.75,
                "raw": {"source": "mock", "type": "social"}
            },
            {
                "title": f"{query} - News Article",
                "snippet": f"Recent article featuring {query} in technology innovation. Published in Tech News Today.",
                "url": f"https://news.example.com/article/{query.lower().replace(' ', '-')}",
                "confidence": 0.60,
                "raw": {"source": "mock", "type": "news"}
            }
        ]

        # Randomize and limit results
        random.shuffle(mock_results)
        results = mock_results[:min(limit, len(mock_results))]

        # Apply redaction
        for result in results:
            result["snippet"] = self._redact_sensitive_info(result["snippet"])

        return results
