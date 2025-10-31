from typing import List, Dict, Any
import aiohttp
from .base import BaseProvider


class WikipediaProvider(BaseProvider):
    """Wikipedia API provider for public enrichment."""

    def __init__(self):
        super().__init__("wikipedia")
        self.base_url = "https://en.wikipedia.org/api/rest_v1/page/summary"

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search using Wikipedia API."""
        # Clean query for Wikipedia
        clean_query = query.replace(" ", "_")

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{clean_query}"
                async with session.get(url) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()

                    # Check if it's a disambiguation page or actual article
                    if data.get("type") == "disambiguation":
                        return []  # Skip disambiguation pages

                    snippet = self._redact_sensitive_info(
                        data.get("extract", ""))
                    result = {
                        "title": data.get("title", ""),
                        "snippet": snippet[:500] + "..." if len(snippet) > 500 else snippet,
                        "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "confidence": self._calculate_confidence(data),
                        "raw": {
                            "source": "wikipedia",
                            "description": data.get("description", ""),
                            "type": data.get("type", "")
                        }
                    }

                    return [result] if result["url"] else []

        except Exception as e:
            # Log error in production
            return []

    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """Calculate confidence based on Wikipedia article quality."""
        confidence = 0.7  # Base confidence for Wikipedia

        # Higher confidence for featured articles (simplified check)
        if len(data.get("extract", "")) > 1000:
            confidence += 0.1

        # Check for references to authority
        extract = data.get("extract", "").lower()
        if any(term in extract for term in ["university", "award", "prize", "president", "ceo"]):
            confidence += 0.1

        return min(confidence, 1.0)
