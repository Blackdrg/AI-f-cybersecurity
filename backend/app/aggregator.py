from typing import List, Dict, Any
import asyncio
from collections import defaultdict
from .providers.base import BaseProvider
from .providers.mock_provider import MockProvider

# Optional providers (may have extra dependencies)
try:
    from .providers.bing_provider import BingProvider
    _BING_AVAILABLE = True
except ImportError:
    _BING_AVAILABLE = False
    BingProvider = None

try:
    from .providers.wikipedia_provider import WikipediaProvider
    _WIKIPEDIA_AVAILABLE = True
except ImportError:
    _WIKIPEDIA_AVAILABLE = False
    WikipediaProvider = None


class ResultAggregator:
    """Aggregates and ranks results from multiple providers."""

    def __init__(self):
        self.providers = {
            "mock": MockProvider()
        }
        if _BING_AVAILABLE:
            self.providers["bing"] = BingProvider()
        if _WIKIPEDIA_AVAILABLE:
            self.providers["wikipedia"] = WikipediaProvider()

    async def enrich(self, query: str, providers: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Enrich query using specified providers and aggregate results."""
        # Validate providers
        valid_providers = [p for p in providers if p in self.providers]

        if not valid_providers:
            valid_providers = ["mock"]  # Fallback to mock

        # Execute searches in parallel
        tasks = []
        for provider_name in valid_providers:
            provider = self.providers[provider_name]
            task = provider.search(query, limit=limit)
            tasks.append(task)

        # Wait for all searches to complete
        search_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        all_results = []
        provider_calls = []

        for i, result in enumerate(search_results):
            provider_name = valid_providers[i]
            if isinstance(result, Exception):
                # Log error and continue
                provider_calls.append({
                    "provider": provider_name,
                    "success": False,
                    "error": str(result),
                    "results_count": 0
                })
                continue

            provider_calls.append({
                "provider": provider_name,
                "success": True,
                "results_count": len(result)
            })

            # Add provider info to each result
            for r in result:
                r["provider"] = provider_name
                all_results.append(r)

        # Rank and deduplicate results
        ranked_results = self._rank_and_deduplicate(all_results, limit)

        return ranked_results, provider_calls

    def _rank_and_deduplicate(self, results: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Rank results by confidence and remove duplicates."""
        # Group by URL to deduplicate
        url_groups = defaultdict(list)

        for result in results:
            url = result.get("url", "").lower()
            if url:
                url_groups[url].append(result)
            else:
                # If no URL, use title as key
                title = result.get("title", "").lower()
                url_groups[title].append(result)

        # For each group, keep the highest confidence result
        deduplicated = []
        for group in url_groups.values():
            best_result = max(group, key=lambda x: x.get("confidence", 0))
            deduplicated.append(best_result)

        # Sort by confidence descending
        deduplicated.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return deduplicated[:limit]

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self.providers.keys())
