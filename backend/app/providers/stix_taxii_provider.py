"""
STIX/TAXII Integration - Industry-standard threat intelligence sharing.
Supports STIX 2.1 and TAXII 2.1 protocols.
"""
import os
import logging
import asyncio
import json
import hashlib
import base64
from typing import Optional, Dict, Any, List, Iterator
from datetime import datetime, timedelta

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


class TAXIICollection:
    """Represents a TAXII Collection object."""

    def __init__(self, name: str, description: str, id: str = None,
                 can_read: bool = True, can_write: bool = False,
                 media_types: List[str] = None):
        self.id = id or str(hashlib.sha256(name.encode()).hexdigest()[:32])
        self.name = name
        self.description = description
        self.can_read = can_read
        self.can_write = can_write
        self.media_types = media_types or ["application/stix+json;version=2.1"]


class STIXTaxiiClient:
    """STIX/TAXII 2.1 client for consuming and producing threat intelligence."""

    def __init__(self, base_url: str, username: str = None, password: str = None,
                 api_key: str = None, collection_id: str = None):
        self.base_url = base_url.rstrip('/')
        self.username = username or os.getenv("TAXII_USERNAME")
        self.password = password or os.getenv("TAXII_PASSWORD")
        self.api_key = api_key or os.getenv("TAXII_API_KEY")
        self.collection_id = collection_id or os.getenv("TAXII_COLLECTION_ID")
        self._client: Optional[httpx.AsyncClient] = None
        self._auth_token: Optional[str] = None
        self._collections_cache: List[TAXIICollection] = []
        self._cache_expiry = 0

    def _get_headers(self) -> Dict[str, str]:
        """Build authorization headers."""
        headers = {
            "Accept": "application/taxii+json;version=2.1",
            "Content-Type": "application/taxii+json;version=2.1"
        }
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True
            )
        return self._client

    async def close(self):
        """Close the HTTP client session."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def authenticate(self) -> bool:
        """Authenticate with the TAXII server if credentials provided."""
        if not self.username or not self.password:
            return bool(self.api_key)

        try:
            client = self._get_client()
            resp = await client.post(
                f"{self.base_url}/token/",
                data={"username": self.username, "password": self.password}
            )
            if resp.status_code == 200:
                self._auth_token = resp.json().get("token")
                return True
            logger.warning(f"TAXII authentication failed: {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"TAXII authentication error: {e}")
            return False

    async def list_collections(self) -> List[TAXIICollection]:
        """List available TAXII Collections."""
        try:
            client = self._get_client()
            url = f"{self.base_url}/collections/"
            if self.collection_id:
                url = f"{self.base_url}/collections/{self.collection_id}/"

            resp = await client.get(url, headers=self._get_headers())
            resp.raise_for_status()
            data = resp.json()

            collections = []
            for obj in data.get("collections", []):
                meta = obj.get("metadata", {})
                can_read = "read" in str(meta.get("can_read", True))
                can_write = "write" in str(meta.get("can_write", False))
                collections.append(TAXIICollection(
                    name=obj.get("title", obj.get("id", "")),
                    description=meta.get("description", ""),
                    id=obj.get("id", ""),
                    can_read=can_read,
                    can_write=can_write,
                    media_types=obj.get("media_types", [])
                ))

            self._collections_cache = collections
            return collections
        except Exception as e:
            logger.error(f"TAXII list collections failed: {e}")
            return []

    async def get_objects(self, limit: int = 100, added_after: datetime = None,
                          match_id: str = None, since: datetime = None,
                          types: List[str] = None) -> Iterator[Dict[str, Any]]:
        """Retrieve STIX objects from the collection."""
        if not self.collection_id:
            collections = await self.list_collections()
            if collections:
                self.collection_id = collections[0].id

        if not self.collection_id:
            logger.error("No collection ID specified")
            return

        try:
            client = self._get_client()
            url = f"{self.base_url}/collections/{self.collection_id}/objects/"
            params = {"limit": str(limit)}

            if added_after:
                params["added_after"] = added_after.isoformat() + "Z"
            if match_id:
                params["match[id]"] = match_id
            if since:
                params["match[created]"] = since.isoformat() + "Z"
            if types:
                params["match[type]"] = ",".join(types)

            while url:
                resp = await client.get(url, headers=self._get_headers(), params=params)
                resp.raise_for_status()
                data = resp.json()

                for obj in data.get("objects", []):
                    yield self._parse_stix_object(obj)

                # Handle pagination
                url = data.get("more", False) and data.get("next", "")
                params = {}  # Params included in next URL

        except Exception as e:
            logger.error(f"TAXII object retrieval failed: {e}")

    async def poll_collection(self, period: timedelta = None,
                              manifest_id: str = None) -> List[Dict[str, Any]]:
        """Poll the collection for new or updated content."""
        if not self.collection_id:
            collections = await self.list_collections()
            if collections:
                self.collection_id = collections[0].id

        url = f"{self.base_url}/collections/{self.collection_id}/poll-requests/"
        params = {}

        if manifest_id:
            params["manifest_id"] = manifest_id

        try:
            client = self._get_client()
            resp = await client.get(url, headers=self._get_headers(), params=params)

            if resp.status_code == 202:
                # Poll was accepted, get results
                poll_url = resp.headers.get("Location", "")
                if poll_url:
                    await asyncio.sleep(2)  # Wait for poll to process
                    result_resp = await client.get(poll_url, headers=self._get_headers())
                    result_data = result_resp.json()
                    return [
                        self._parse_stix_object(obj)
                        for obj in result_data.get("objects", [])
                    ]
            return []
        except Exception as e:
            logger.error(f"TAXII poll failed: {e}")
            return []

    def _parse_stix_object(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a STIX 2.1 object into our internal format."""
        obj_type = obj.get("type", "unknown")
        stix_id = obj.get("id", "")

        parsed = {
            "stix_id": stix_id,
            "type": obj_type,
            "source": "stix_taxii",
            "created": obj.get("created"),
            "modified": obj.get("modified"),
            "revoked": obj.get("revoked", False),
            "labels": obj.get("labels", []),
            "tags": obj.get("labels", []),
            "confidence": obj.get("confidence", 0),
        }

        # Parse based on STIX type
        if obj_type == "indicator":
            pattern = obj.get("pattern", "")
            parsed.update({
                "indicator_value": self._extract_pattern_value(pattern),
                "pattern_type": obj.get("pattern_type", "stix"),
                "pattern": pattern,
                "valid_from": obj.get("valid_from"),
                "valid_until": obj.get("valid_until"),
                "threat_score": obj.get("confidence", 50) * 2,  # Scale 0-100
                "ioc_type": self._infer_ioc_type(pattern),
                "description": obj.get("description", ""),
            })
        elif obj_type == "indicator-relationship":
            parsed.update({
                "relationship_type": obj.get("relationship_type", ""),
                "source_ref": obj.get("source_ref", ""),
                "target_ref": obj.get("target_ref", ""),
            })
        elif obj_type == "threat-actor":
            parsed.update({
                "name": obj.get("name", ""),
                "description": obj.get("description", ""),
                "threat_actor_types": obj.get("threat_actor_types", []),
                "aliases": obj.get("aliases", []),
                "threat_score": 70,
            })
        elif obj_type == "malware":
            parsed.update({
                "name": obj.get("name", ""),
                "description": obj.get("description", ""),
                "malware_types": obj.get("malware_types", []),
                "is_family": obj.get("is_family", False),
                "threat_score": 80,
            })
        elif obj_type == "attack-pattern":
            parsed.update({
                "name": obj.get("name", ""),
                "description": obj.get("description", ""),
                "kill_chain_phases": [
                    p.get("phase_name", "")
                    for p in obj.get("kill_chain_phases", [])
                ],
                "threat_score": 60,
            })
        elif obj_type == "campaign":
            parsed.update({
                "name": obj.get("name", ""),
                "description": obj.get("description", ""),
                "first_seen": obj.get("first_seen"),
                "last_seen": obj.get("last_seen"),
                "objective": obj.get("objective", ""),
                "threat_score": 75,
            })
        elif obj_type == "report":
            parsed.update({
                "name": obj.get("name", ""),
                "description": obj.get("description", ""),
                "published": obj.get("published"),
                "report_types": obj.get("report_types", []),
            })
        else:
            parsed["raw_object"] = obj

        return parsed

    @staticmethod
    def _extract_pattern_value(pattern: str) -> str:
        """Extract the actual indicator value from a STIX pattern."""
        # STIX pattern examples:
        # [file:hashes.MD5 = 'd41d8cd98f00b204e9800998ecf8427e']
        # [domain:value = 'example.com']
        # [ipv4-addr:value = '192.168.1.1']
        import re
        match = re.search(r"= *'([^']+)'", pattern)
        if match:
            return match.group(1)
        return pattern

    @staticmethod
    def _infer_ioc_type(pattern: str) -> str:
        """Infer IOC type from STIX pattern."""
        import re
        if "ipv4-addr" in pattern or "ipv6-addr" in pattern:
            return "ip"
        elif "domain" in pattern:
            return "domain"
        elif "url" in pattern:
            return "url"
        elif "file:hashes" in pattern:
            if "SHA-256" in pattern:
                return "sha256"
            elif "SHA-1" in pattern:
                return "sha1"
            elif "MD5" in pattern:
                return "md5"
            return "hash"
        elif "email" in pattern:
            return "email"
        return "unknown"


class STIXFeedManager:
    """Manages periodic ingestion of STIX/TAXII threat feeds."""

    def __init__(self, feed_configs: List[Dict[str, Any]]):
        """
        Args:
            feed_configs: List of feed configurations with keys:
                - name, url, collection_id, username, password, api_key, poll_interval_seconds
        """
        self.feed_configs = feed_configs
        self._clients: Dict[str, STIXTaxiiClient] = {}
        self._last_poll: Dict[str, datetime] = {}
        self._stats: Dict[str, Dict[str, int]] = {}

        for config in feed_configs:
            name = config["name"]
            self._clients[name] = STIXTaxiiClient(
                base_url=config["url"],
                username=config.get("username"),
                password=config.get("password"),
                api_key=config.get("api_key"),
                collection_id=config.get("collection_id")
            )
            self._stats[name] = {"total_fetched": 0, "new_iocs": 0, "errors": 0}

    async def authenticate_all(self) -> Dict[str, bool]:
        """Authenticate with all configured feeds."""
        results = {}
        for name, client in self._clients.items():
            try:
                results[name] = await client.authenticate()
            except Exception as e:
                logger.error(f"Failed to authenticate with feed {name}: {e}")
                results[name] = False
        return results

    async def poll_feed(self, name: str) -> List[Dict[str, Any]]:
        """Poll a specific feed for new indicators."""
        if name not in self._clients:
            logger.error(f"Unknown feed: {name}")
            return []

        client = self._clients[name]
        config = next(c for c in self.feed_configs if c["name"] == name)
        poll_interval = config.get("poll_interval_seconds", 3600)

        try:
            since = self._last_poll.get(name)
            if since is None:
                since = datetime.utcnow() - timedelta(seconds=poll_interval)

            iocs = []
            async for obj in client.get_objects(
                since=since,
                types=["indicator"]
            ):
                iocs.append(obj)

            if iocs:
                self._last_poll[name] = datetime.utcnow()
                self._stats[name]["total_fetched"] += len(iocs)
                self._stats[name]["new_iocs"] += len(iocs)

            return iocs
        except Exception as e:
            logger.error(f"Polling feed {name} failed: {e}")
            self._stats[name]["errors"] += 1
            return []

    async def poll_all_feeds(self) -> Dict[str, List[Dict[str, Any]]]:
        """Poll all configured feeds and return aggregated results."""
        results = {}
        for name in self._clients:
            results[name] = await self.poll_feed(name)
        return results

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics for each feed."""
        return self._stats.copy()

    async def close(self):
        """Close all client connections."""
        for client in self._clients.values():
            await client.close()


# Example feed configurations for production use
DEFAULT_TAXII_FEEDS = [
    {
        "name": "alienvault",
        "url": "https://otx.alienvault.com/taxii",
        "collection_id": None,  # Auto-discover
        "poll_interval_seconds": 3600,
    },
    {
        "name": "misp",
        "url": os.getenv("MISP_URL", "").rstrip("/") + "/taxii",
        "collection_id": None,
        "poll_interval_seconds": 1800,
    },
    {
        "name": "cisa_known_exploited",
        "url": "https://cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        "collection_id": None,
        "poll_interval_seconds": 7200,
    },
]