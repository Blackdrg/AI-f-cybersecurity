"""
IOC (Indicator of Compromise) Database Models and Repository
Persistent storage for threat intelligence indicators.
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
import hashlib
import json

from app.db.db_client import get_db


class IOCType:
    """Supported IOC types."""
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    DOMAIN = "domain"
    URL = "url"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    EMAIL = "email"
    FILE_PATH = "file_path"
    MUTEX = "mutex"
    REGISTRY_KEY = "registry_key"
    CVE = "cve"


class IOCSource:
    """IOC data sources."""
    OTX = "otx"
    MISP = "misp"
    VIRUSTOTAL = "virustotal"
    ABUSEIPDB = "abuseipdb"
    URLHAUS = "urlhaus"
    EMERGING_THREATS = "emerging_threats"
    STIX_TAXII = "stix_taxii"
    PASIVEDNS = "passivedns"
    SHODAN = "shodan"
    CUSTOM = "custom"


class IOCSeverity:
    """IOC severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IOCStatus:
    """IOC lifecycle status."""
    NEW = "new"
    ANALYZING = "analyzing"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    EXPIRED = "expired"
    REMOVED = "removed"


@dataclass
class IOC:
    """Represents an Indicator of Compromise."""
    ioc_id: str = ""
    indicator: str = ""
    ioc_type: str = ""
    source: str = ""
    source_id: str = ""
    severity: str = IOCSeverity.MEDIUM
    confidence: float = 0.0
    threat_score: int = 0
    status: str = IOCStatus.NEW
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    description: str = ""
    country: str = ""
    city: str = ""
    asn: str = ""
    organization: str = ""
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    seen_count: int = 0
    related_iocs: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.ioc_id:
            self.ioc_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = datetime.utcnow()

    def fingerprint(self) -> str:
        """Generate unique fingerprint for deduplication."""
        raw = f"{self.indicator}:{self.ioc_type}:{self.source}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        if self.first_seen and isinstance(self.first_seen, datetime):
            d["first_seen"] = self.first_seen.isoformat()
        if self.last_seen and isinstance(self.last_seen, datetime):
            d["last_seen"] = self.last_seen.isoformat()
        if self.created_at and isinstance(self.created_at, datetime):
            d["created_at"] = self.created_at.isoformat()
        if self.updated_at and isinstance(self.updated_at, datetime):
            d["updated_at"] = self.updated_at.isoformat()
        return d


class IOCRepository:
    """Repository for persistent IOC storage and retrieval."""

    def __init__(self, db_client=None):
        self.db_client = db_client

    async def initialize(self):
        """Ensure DB client is initialized."""
        if self.db_client is None:
            self.db_client = get_db()

    async def create_tables(self):
        """Create IOC-related database tables if they don't exist."""
        await self.initialize()
        async with self.db_client.pool.acquire() as conn:
            # Main IOC table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS threat_intel_iocs (
                    ioc_id VARCHAR(36) PRIMARY KEY,
                    indicator TEXT NOT NULL,
                    ioc_type VARCHAR(20) NOT NULL,
                    source VARCHAR(30) NOT NULL,
                    source_id TEXT,
                    severity VARCHAR(20) DEFAULT 'medium',
                    confidence FLOAT DEFAULT 0.0,
                    threat_score INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'new',
                    first_seen TIMESTAMP WITH TIME ZONE,
                    last_seen TIMESTAMP WITH TIME ZONE,
                    tags TEXT[] DEFAULT '{}',
                    description TEXT,
                    country VARCHAR(2),
                    city TEXT,
                    asn TEXT,
                    organization TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    metadata JSONB DEFAULT '{}',
                    fingerprint VARCHAR(64) UNIQUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    seen_count INTEGER DEFAULT 1
                );
            """)

            # IOC relationships table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ioc_relationships (
                    id SERIAL PRIMARY KEY,
                    ioc_id VARCHAR(36) REFERENCES threat_intel_iocs(ioc_id),
                    related_ioc_id VARCHAR(36) REFERENCES threat_intel_iocs(ioc_id),
                    relationship_type VARCHAR(30) DEFAULT 'related',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)

            # IOC feed tracking table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS threat_feeds (
                    feed_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    feed_type VARCHAR(30) NOT NULL,
                    url TEXT,
                    api_key_hash VARCHAR(128),
                    last_sync TIMESTAMP WITH TIME ZONE,
                    sync_interval INTEGER DEFAULT 3600,
                    is_active BOOLEAN DEFAULT TRUE,
                    total_indicators INTEGER DEFAULT 0,
                    new_indicators INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)

            # IOC sync log
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ioc_sync_log (
                    id SERIAL PRIMARY KEY,
                    feed_id INTEGER REFERENCES threat_feeds(feed_id),
                    sync_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    sync_end TIMESTAMP WITH TIME ZONE,
                    indicators_fetched INTEGER DEFAULT 0,
                    indicators_new INTEGER DEFAULT 0,
                    indicators_updated INTEGER DEFAULT 0,
                    indicators_failed INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'running',
                    error_message TEXT
                );
            """)

            # Create indexes for fast lookups
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_ioc_indicator ON threat_intel_iocs(LOWER(indicator))",
                "CREATE INDEX IF NOT EXISTS idx_ioc_type ON threat_intel_iocs(ioc_type)",
                "CREATE INDEX IF NOT EXISTS idx_ioc_source ON threat_intel_iocs(source)",
                "CREATE INDEX IF NOT EXISTS idx_ioc_severity ON threat_intel_iocs(severity)",
                "CREATE INDEX IF NOT EXISTS idx_ioc_status ON threat_intel_iocs(status)",
                "CREATE INDEX IF NOT EXISTS idx_ioc_threat_score ON threat_intel_iocs(threat_score)",
                "CREATE INDEX IF NOT EXISTS idx_ioc_last_seen ON threat_intel_iocs(last_seen DESC)",
                "CREATE INDEX IF NOT EXISTS idx_ioc_fingerprint ON threat_intel_iocs(fingerprint)",
                "CREATE INDEX IF NOT EXISTS idx_ioc_active ON threat_intel_iocs(is_active) WHERE is_active = TRUE",
                "CREATE INDEX IF NOT EXISTS idx_ioc_composite ON threat_intel_iocs(ioc_type, severity, is_active)",
                "CREATE INDEX IF NOT EXISTS idx_ioc_seen_count ON threat_intel_iocs(seen_count DESC)",
            ]
            for idx_sql in indexes:
                try:
                    await conn.execute(idx_sql)
                except Exception as e:
                    logger.debug(f"Index creation skipped: {e}")

            logger.info("IOC tables and indexes created")

    async def upsert_ioc(self, ioc: IOC) -> str:
        """Insert or update an IOC."""
        await self.initialize()
        fingerprint = ioc.fingerprint()
        try:
            existing = await self.db_client.pool.fetchrow(
                "SELECT ioc_id, seen_count, threat_score FROM threat_intel_iocs WHERE fingerprint = $1",
                fingerprint
            )
            if existing:
                # Update existing IOC
                new_seen_count = existing['seen_count'] + 1
                new_score = max(existing['threat_score'], ioc.threat_score)
                await self.db_client.pool.execute(
                    """
                    UPDATE threat_intel_iocs SET
                        last_seen = $1, updated_at = NOW(),
                        seen_count = $2, threat_score = $3,
                        confidence = GREATEST(confidence, $4),
                        status = CASE WHEN $5 > threat_score THEN $6 ELSE status END,
                        source_id = COALESCE($7, source_id),
                        metadata = COALESCE($8, metadata)
                    WHERE fingerprint = $9
                    """,
                    ioc.last_seen, new_seen_count, new_score,
                    ioc.confidence, ioc.threat_score, ioc.status,
                    ioc.source_id, json.dumps(ioc.metadata) if ioc.metadata else None,
                    fingerprint
                )
                return existing['ioc_id']
            else:
                # Insert new IOC
                await self.db_client.pool.execute(
                    """
                    INSERT INTO threat_intel_iocs (
                        ioc_id, indicator, ioc_type, source, source_id,
                        severity, confidence, threat_score, status,
                        first_seen, last_seen, tags, description,
                        country, city, asn, organization,
                        metadata, fingerprint, seen_count
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                    """,
                    ioc.ioc_id, ioc.indicator, ioc.ioc_type, ioc.source, ioc.source_id,
                    ioc.severity, ioc.confidence, ioc.threat_score, ioc.status,
                    ioc.first_seen, ioc.last_seen, ioc.tags, ioc.description,
                    ioc.country, ioc.city, ioc.asn, ioc.organization,
                    json.dumps(ioc.metadata) if ioc.metadata else '{}',
                    fingerprint, ioc.seen_count
                )
                return ioc.ioc_id
        except Exception as e:
            logger.error(f"IOC upsert failed: {e}")
            raise

    async def bulk_upsert(self, iocs: List[IOC]):
        """Bulk upsert IOCs efficiently."""
        await self.initialize()
        for ioc in iocs:
            try:
                await self.upsert_ioc(ioc)
            except Exception as e:
                logger.error(f"Failed to upsert IOC {ioc.indicator}: {e}")

    async def lookup(self, indicator: str, ioc_type: str = None) -> List[Dict[str, Any]]:
        """Look up IOCs matching the indicator."""
        await self.initialize()
        try:
            if ioc_type:
                rows = await self.db_client.pool.fetch(
                    """
                    SELECT ioc_id, indicator, ioc_type, source, severity, confidence,
                           threat_score, status, first_seen, last_seen, tags,
                           country, city, asn, organization, seen_count, metadata
                    FROM threat_intel_iocs
                    WHERE LOWER(indicator) = LOWER($1) AND ioc_type = $2
                    ORDER BY threat_score DESC, last_seen DESC
                    """,
                    indicator, ioc_type
                )
            else:
                rows = await self.db_client.pool.fetch(
                    """
                    SELECT ioc_id, indicator, ioc_type, source, severity, confidence,
                           threat_score, status, first_seen, last_seen, tags,
                           country, city, asn, organization, seen_count, metadata
                    FROM threat_intel_iocs
                    WHERE LOWER(indicator) = LOWER($1)
                    ORDER BY threat_score DESC, last_seen DESC
                    """,
                    indicator
                )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"IOC lookup failed: {e}")
            return []

    async def query_by_type(self, ioc_type: str, severity: str = None,
                            active_only: bool = True, limit: int = 1000) -> List[Dict]:
        """Query IOCs by type with optional filters."""
        await self.initialize()
        try:
            base_query = "SELECT ioc_id, indicator, ioc_type, source, severity, threat_score, status FROM threat_intel_iocs WHERE 1=1"
            params = []
            param_idx = 1

            if ioc_type:
                base_query += f" AND ioc_type = ${param_idx}"
                params.append(ioc_type)
                param_idx += 1

            if active_only:
                base_query += f" AND is_active = TRUE"

            if severity:
                base_query += f" AND severity = ${param_idx}"
                params.append(severity)
                param_idx += 1

            base_query += f" ORDER BY threat_score DESC LIMIT ${param_idx}"
            params.append(limit)

            rows = await self.db_client.pool.fetch(base_query, *params)
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"IOC query failed: {e}")
            return []

    async def update_feed_sync(self, feed_name: str, feed_type: str,
                               indicators_fetched: int, new_count: int,
                               sync_duration_sec: float, status: str = "completed"):
        """Track feed synchronization results."""
        await self.initialize()
        try:
            async with self.db_client.pool.acquire() as conn:
                # Upsert feed
                await conn.execute("""
                    INSERT INTO threat_feeds (name, feed_type, last_sync, total_indicators, new_indicators)
                    VALUES ($1, $2, NOW(), $3, $4)
                    ON CONFLICT (name) DO UPDATE SET
                        last_sync = NOW(),
                        total_indicators = threat_feeds.total_indicators + $3,
                        new_indicators = threat_feeds.new_indicators + $4
                """, feed_name, feed_type, indicators_fetched, new_count)

                # Log sync event
                feed_id = await conn.fetchval(
                    "SELECT feed_id FROM threat_feeds WHERE name = $1", feed_name
                )
                if feed_id:
                    await conn.execute("""
                        INSERT INTO ioc_sync_log (feed_id, indicators_fetched, indicators_new, status)
                        VALUES ($1, $2, $3, $4)
                    """, feed_id, indicators_fetched, new_count, status)
        except Exception as e:
            logger.error(f"Feed sync tracking failed: {e}")

    async def expire_old_iocs(self, days_old: int = 90):
        """Mark old IOCs as expired."""
        await self.initialize()
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff.replace(day=cutoff.day - days_old)
        await self.db_client.pool.execute(
            """
            UPDATE threat_intel_iocs
            SET status = 'expired', is_active = FALSE, updated_at = NOW()
            WHERE last_seen < $1 AND status = 'confirmed'
            """,
            cutoff
        )


# Global singleton
_ioc_repo: Optional[IOCRepository] = None


def get_ioc_repository() -> IOCRepository:
    """Get global IOC repository instance."""
    global _ioc_repo
    if _ioc_repo is None:
        _ioc_repo = IOCRepository()
    return _ioc_repo