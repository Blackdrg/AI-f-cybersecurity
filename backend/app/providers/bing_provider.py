from typing import List, Dict, Any
import os
import aiohttp
from .base import BaseProvider


class BingProvider(BaseProvider):
    """Bing Search API provider for public enrichment."""

    def __init__(self):
        api_key = os.getenv('BING_API_KEY')
        super().__init__("bing", api_key)
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search using Bing Web Search API."""
        if not self.api_key:
            return []  # Return empty if no API key

        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {
            "q": query,
            "count": min(limit, 50),  # Bing max is 50
            "responseFilter": "Webpages",
            "safeSearch": "Moderate"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, headers=headers, params=params) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()
                    results = []

                    for item in data.get("webPages", {}).get("value", []):
                        snippet = self._redact_sensitive_info(
                            item.get("snippet", ""))
                        result = {
                            "title": item.get("name", ""),
                            "snippet": snippet,
                            "url": item.get("url", ""),
                            "confidence": self._calculate_confidence(item),
                            "raw": {
                                "source": "bing",
                                "displayUrl": item.get("displayUrl", ""),
                                "dateLastCrawled": item.get("dateLastCrawled", "")
                            }
                        }
                        results.append(result)

                    return results[:limit]

        except Exception as e:
            # Log error in production
            return []

    def _calculate_confidence(self, item: Dict[str, Any]) -> float:
        """Calculate confidence based on Bing-specific factors."""
        confidence = 0.5  # Base confidence

        # Higher confidence for more recent content
        if "dateLastCrawled" in item:
            # Could parse date and adjust confidence
            confidence += 0.1

        # Adjust based on URL authority (simplified)
        url = item.get("url", "").lower()
        if any(domain in url for domain in ["wikipedia.org", "linkedin.com", "github.com"]):
            confidence += 0.2

        return min(confidence, 1.0)

    async def get_health_status(self) -> str:
        if not self.api_key:
            return "unconfigured"
        try:
            # Simple check by making a minimal request
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            params = {"q": "test", "count": 1}
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return "healthy"
                    return "degraded"
        except Exception:
            return "unhealthy"
