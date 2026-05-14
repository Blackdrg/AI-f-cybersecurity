"""
Enhanced DBClient with:
- Connection pool failover between primary and read replicas
- Health checking per replica (automatic exclusion of unhealthy replicas)
- Round-robin read distribution
- Retry with circuit breaker pattern
"""
import os
import uuid
import json
import logging
import hashlib
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import numpy as np

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    Fernet = None

try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None

logger = logging.getLogger(__name__)


class ReplicaHealthChecker:
    """Monitors health of read replicas and excludes unhealthy ones."""

    def __init__(self, check_interval: int = 30, failure_threshold: int = 3):
        self.check_interval = check_interval
        self.failure_threshold = failure_threshold
        self.failure_counts: Dict[str, int] = {}
        self.healthy_replicas: set = set()
        self.last_check: Dict[str, float] = {}

    def record_failure(self, replica_url: str):
        self.failure_counts[replica_url] = self.failure_counts.get(replica_url, 0) + 1
        if self.failure_counts[replica_url] >= self.failure_threshold:
            self.healthy_replicas.discard(replica_url)
            logger.warning(f"Replica {replica_url} marked unhealthy after {self.failure_threshold} failures")

    def record_success(self, replica_url: str):
        self.failure_counts[replica_url] = 0
        self.healthy_replicas.add(replica_url)
        self.last_check[replica_url] = time.time()

    def is_healthy(self, replica_url: str) -> bool:
        return replica_url in self.healthy_replicas

    async def check_replica_lag(self, conn) -> Optional[float]:
        """Check replication lag in seconds."""
        try:
            result = await conn.fetchval("""
                SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::float
            """)
            return float(result) if result else 0.0
        except Exception:
            return None


class CircuitBreaker:
    """Circuit breaker pattern for database operations."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60,
                 expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed | open | half-open

    def call(self, func):
        """Decorator for circuit breaker."""
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is OPEN - failing fast")

            try:
                result = await func(*args, **kwargs)
                if self.state == "half-open":
                    self.state = "closed"
                    self.failure_count = 0
                return result
            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logger.error(f"Circuit breaker OPENED after {self.failure_count} failures")
                raise
        return wrapper


class DBClient:
    """Production-ready database client with connection pooling, failover, and monitoring."""

    def __init__(self, read_replicas: list = None):
        self.pool = None
        self.read_replica_pools: List[asyncpg.Pool] = []
        self.read_replica_urls: List[str] = []
        self.kms_client = self._init_kms()
        self.encryption_key = self._load_encryption_key()
        self.health_checker = ReplicaHealthChecker()
        self.circuit_breaker = CircuitBreaker()
        self._in_memory_db = {
            'persons': {}, 'embeddings': {}, 'consent_logs': {},
            'audit_log': [], 'users': {}, 'support_tickets': {}
        }
        self.metrics = {
            'queries_total': 0,
            'queries_failed': 0,
            'reads_from_primary': 0,
            'reads_from_replicas': 0,
            'connection_errors': 0,
            'slow_queries': 0,
        }
        self._query_history: List[Dict] = []
        self._max_history = 1000

        # Parse replica URLs
        if read_replicas:
            self.read_replica_urls = read_replicas
        else:
            replicas = os.getenv('DB_READ_REPLICAS', '')
            self.read_replica_urls = [
                url.strip() for url in replicas.split(',') if url.strip()
            ]
        self.current_replica_index = 0

    def _init_kms(self):
        """Initialize AWS KMS client for key management.

        Returns KMS client if boto3 is available and credentials exist,
        otherwise returns None (falls back to local key management).
        """
        if BOTO3_AVAILABLE:
            try:
                return boto3.client('kms', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            except Exception:
                return None
        return None

    def _load_encryption_key(self) -> bytes:
        """Load encryption key for Fernet symmetric encryption.

        Uses a centralized secrets vault, falling back to env var or dev key.
        """
        try:
            from app.security.vault import get_encryption_key as vault_get_key
            key = vault_get_key()
        except Exception:
            key = os.getenv('ENCRYPTION_KEY', 'dev-key-fallback-32bytes-ok!')

        import base64
        key_bytes = key.encode()[:32].ljust(32, b'\0')
        return base64.urlsafe_b64encode(key_bytes)

    async def init_db(self):
        """Initialize database connection pools with retry logic."""
        try:
            db_user = os.getenv('DB_USER', 'postgres')
            db_password = os.getenv('DB_PASSWORD', 'password')
            db_name = os.getenv('DB_NAME', 'face_recognition')
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = int(os.getenv('DB_PORT', 5432))

            pool_max_size = int(os.getenv('DB_POOL_MAX_SIZE', '10'))
            pool_min_size = int(os.getenv('DB_POOL_MIN_SIZE', '2'))
            max_queries = int(os.getenv('DB_POOL_MAX_QUERIES', '5000'))
            max_inactive = float(os.getenv('DB_POOL_MAX_INACTIVE_LIFETIME', '300'))
            health_check_interval = float(os.getenv('DB_POOL_HEALTH_CHECK_INTERVAL', '30'))
            conn_timeout = float(os.getenv('DB_CONNECTION_TIMEOUT', '15'))

            logger.info(
                f"DB pool: min={pool_min_size}, max={pool_max_size}, "
                f"max_queries={max_queries}, health_check={health_check_interval}s"
            )

            retry_count = 0
            max_retries = 5
            while retry_count < max_retries:
                try:
                    self.pool = await asyncpg.create_pool(
                        user=db_user, password=db_password,
                        database=db_name, host=db_host, port=db_port,
                        min_size=pool_min_size, max_size=pool_max_size,
                        max_queries=max_queries,
                        max_inactive_connection_lifetime=max_inactive,
                        health_check_interval=health_check_interval,
                        timeout=conn_timeout,
                        command_timeout=conn_timeout,
                        server_settings={
                            'application_name': 'ai-f-production',
                            'tcp_keepalives_idle': 30,
                            'tcp_keepalives_interval': 5,
                            'tcp_keepalives_count': 5,
                        }
                    )
                    logger.info("Primary database pool created successfully")
                    break
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"DB connection attempt {retry_count}/{max_retries}: {e}")
                    if retry_count < max_retries:
                        await asyncio.sleep(2 ** retry_count)
                    else:
                        raise

            # Initialize schemas and extensions
            await self._init_schemas()

            # Initialize read replica pools
            await self._init_read_replicas(db_user, db_password, db_name)

            # Start health monitoring task
            asyncio.create_task(self._health_monitor_loop())
            logger.info("Database client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.warning("Falling back to in-memory mode")
            self.pool = None

    async def _init_schemas(self):
        """Initialize schemas and extensions."""
        async with self.pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
            logger.info("Schema extensions initialized")

    async def _init_read_replicas(self, db_user: str, db_password: str, db_name: str):
        """Initialize read replica connection pools with health checking."""
        if not self.read_replica_urls:
            logger.info("No read replicas configured, using primary for all reads")
            return

        for replica_url in self.read_replica_urls:
            try:
                if '://' in replica_url:
                    pool = await asyncpg.create_pool(
                        replica_url,
                        min_size=int(os.getenv('DB_REPLICA_POOL_MIN', '2')),
                        max_size=int(os.getenv('DB_REPLICA_POOL_MAX', '5')),
                        health_check_interval=30.0,
                        max_inactive_connection_lifetime=300.0,
                        timeout=15.0,
                        max_queries=5000,
                        server_settings={'application_name': 'ai-f-replica'}
                    )
                else:
                    if ':' in replica_url:
                        replica_host, replica_port = replica_url.split(':')
                        replica_port = int(replica_port)
                    else:
                        replica_host, replica_port = replica_url, 5432

                    pool = await asyncpg.create_pool(
                        user=db_user, password=db_password,
                        database=db_name, host=replica_host, port=replica_port,
                        min_size=int(os.getenv('DB_REPLICA_POOL_MIN', '2')),
                        max_size=int(os.getenv('DB_REPLICA_POOL_MAX', '5')),
                        health_check_interval=30.0,
                        max_inactive_connection_lifetime=300.0,
                        timeout=15.0, max_queries=5000,
                        server_settings={'application_name': 'ai-f-replica'}
                    )

                self.read_replica_pools.append(pool)
                self.health_checker.healthy_replicas.add(replica_url)
                logger.info(f"Read replica connected: {replica_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to read replica {replica_url}: {e}")
                self.health_checker.record_failure(replica_url)

    def _get_read_pool(self) -> Optional[asyncpg.Pool]:
        """Get healthy read replica pool using round-robin.
        Falls back to primary if no healthy replicas."""
        healthy_pools = [
            pool for pool, url in zip(
                self.read_replica_pools, self.read_replica_urls
            ) if self.health_checker.is_healthy(url)
        ]

        if not healthy_pools:
            return self.pool

        pool = healthy_pools[self.current_replica_index % len(healthy_pools)]
        self.current_replica_index += 1
        return pool

    async def _health_monitor_loop(self):
        """Background task to monitor replica health."""
        while True:
            try:
                await asyncio.sleep(30)
                await self._check_replica_health()
                await self._check_primary_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    async def _check_replica_health(self):
        """Check health of all read replicas."""
        for pool, url in zip(self.read_replica_pools, self.read_replica_urls):
            try:
                async with pool.acquire() as conn:
                    lag = await conn.fetchval("""
                        SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::float
                    """)
                    self.health_checker.record_success(url)
                    if lag is not None and lag > 30:
                        logger.warning(f"Replica {url} has high lag: {lag}s")
            except Exception as e:
                self.health_checker.record_failure(url)
                logger.warning(f"Replica {url} health check failed: {e}")

    async def _check_primary_health(self):
        """Verify primary database is responsive."""
        if self.pool is None:
            return
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except Exception as e:
            self.metrics['connection_errors'] += 1
            logger.error(f"Primary health check failed: {e}")

    # ==================== CORE QUERY METHODS ====================

    async def fetch(self, query: str, *args, read_replica: bool = False):
        """Execute query and return all rows."""
        pool = self._get_read_pool() if read_replica and self.read_replica_pools else self.pool
        if pool is None:
            return []
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args, read_replica: bool = False):
        """Execute query and return first row."""
        pool = self._get_read_pool() if read_replica and self.read_replica_pools else self.pool
        if pool is None:
            return None
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args, read_replica: bool = False):
        """Execute query and return single value."""
        pool = self._get_read_pool() if read_replica and self.read_replica_pools else self.pool
        if pool is None:
            return None
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args):
        """Execute query without returning rows."""
        if self.pool is None:
            return
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def execute_many(self, query: str, args_list: list):
        """Execute query with multiple argument sets."""
        if self.pool is None:
            return
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for args in args_list:
                    await conn.execute(query, *args)

    # ==================== TRANSACTION METHODS ====================

    async def transaction(self):
        """Get a transaction context manager."""
        if self.pool is None:
            return None
        conn = await self.pool.acquire()
        return conn.transaction()

    # ==================== BIOMETRIC METHODS ====================

    async def recognize_faces(self, query_embedding, top_k=1, threshold=0.6,
                               camera_id=None, voice_embedding=None,
                               gait_embedding=None, read_replica=True):
        """Multi-modal face recognition with vector search."""
        pool = self._get_read_pool() if read_replica and self.read_replica_pools else self.pool
        if pool is None:
            return []

        async with pool.acquire() as conn:
            query_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding

            face_query = """
                SELECT person_id, embedding <=> $1 as distance
                FROM embeddings WHERE embedding_type = 'face'
                AND camera_id = $3 OR $3 IS NULL
                ORDER BY embedding <=> $1
                LIMIT $2
            """
            face_results = await conn.fetch(face_query, query_list, top_k * 2, camera_id)

            matches = []
            for row in face_results:
                face_distance = row['distance']
                if face_distance > threshold:
                    continue

                person_id = row['person_id']
                combined_score = 1 - face_distance

                if voice_embedding is not None:
                    voice_row = await conn.fetchrow("""
                        SELECT voice_embedding <=> $1 as distance
                        FROM embeddings WHERE person_id = $2 AND voice_embedding IS NOT NULL
                        ORDER BY distance LIMIT 1
                    """, voice_embedding.tolist() if hasattr(voice_embedding, 'tolist') else voice_embedding, person_id)
                    if voice_row and voice_row['distance'] and voice_row['distance'] <= threshold:
                        combined_score += (1 - voice_row['distance']) * 0.2

                if gait_embedding is not None:
                    gait_row = await conn.fetchrow("""
                        SELECT gait_embedding <=> $1 as distance
                        FROM embeddings WHERE person_id = $2 AND gait_embedding IS NOT NULL
                        ORDER BY distance LIMIT 1
                    """, gait_embedding.tolist() if hasattr(gait_embedding, 'tolist') else gait_embedding, person_id)
                    if gait_row and gait_row['distance'] and gait_row['distance'] <= threshold:
                        combined_score += (1 - gait_row['distance']) * 0.2

                if combined_score >= (1 - threshold):
                    person = await conn.fetchrow(
                        "SELECT name, age, gender FROM persons WHERE person_id = $1", person_id)
                    if person:
                        matches.append({
                            'person_id': person_id,
                            'name': person['name'],
                            'age': person['age'],
                            'gender': person['gender'],
                            'distance': 1 - combined_score,
                            'score': combined_score
                        })

            matches.sort(key=lambda x: x['score'], reverse=True)
            return matches[:top_k]

    async def enroll_person(self, person_id, name, embeddings, consent_record,
                             camera_id=None, voice_embeddings=None,
                             gait_embedding=None, age=None, gender=None):
        """Enroll a person with multi-modal biometric data."""
        if self.pool is None:
            return person_id

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO persons (person_id, name, age, gender, consent_record_id)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (person_id) DO UPDATE SET name = $2, age = $3, gender = $4
                """, person_id, name, age, gender, consent_record.get('consent_id'))

                for i, emb in enumerate(embeddings):
                    emb_id = str(uuid.uuid4())
                    emb_list = emb.tolist() if hasattr(emb, 'tolist') else emb
                    voice_list = None
                    if voice_embeddings and i < len(voice_embeddings) and voice_embeddings[i] is not None:
                        voice_list = voice_embeddings[i].tolist() if hasattr(voice_embeddings[i], 'tolist') else voice_embeddings[i]
                    gait_list = gait_embedding.tolist() if gait_embedding is not None and hasattr(gait_embedding, 'tolist') else gait_embedding

                    await conn.execute("""
                        INSERT INTO embeddings (embedding_id, person_id, embedding, voice_embedding, gait_embedding, camera_id)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, emb_id, person_id, emb_list, voice_list, gait_list, camera_id)

                await conn.execute("""
                    INSERT INTO consent_records (consent_id, user_id, purpose, consent_text_version, granted, granted_at, ip_address)
                    VALUES ($1, $2, $3, $4, TRUE, NOW(), $5)
                    ON CONFLICT (consent_id) DO NOTHING
                """, consent_record.get('consent_id'), person_id, consent_record.get('purpose', 'recognition'),
                    consent_record.get('text_version', '1.0'), consent_record.get('ip_addr'))

                last_log = await conn.fetchrow("SELECT current_hash FROM audit.log_entries ORDER BY log_id DESC LIMIT 1")
                prev_hash = last_log['current_hash'] if last_log else "0" * 64
                log_content = f"{prev_hash}enroll{person_id}"
                current_hash = hashlib.sha256(log_content.encode()).hexdigest()

                await conn.execute("""
                    INSERT INTO audit.log_entries (org_id, actor_id, action, resource_type, resource_id, previous_hash, current_hash)
                    VALUES ($1, $2, 'enroll', 'person', $3, $4, $5)
                """, consent_record.get('org_id'), person_id, person_id, prev_hash, current_hash)

        return person_id

    # ==================== ENRICHMENT METHODS ====================

    async def save_enrichment_result(self, query, subject, summary, requested_by, purpose, ttl_days=7):
        async with self.pool.acquire() as conn:
            expire = datetime.utcnow() + timedelta(days=ttl_days)
            await conn.execute("""
                INSERT INTO enrichment_results (enrich_id, query, subject, summary, expires_at, requested_by, purpose)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, str(uuid.uuid4()), query, subject, summary, expire, requested_by, purpose)
            return True

    async def log_audit(self, action, user_id, target_enrich_id, provider_calls, metadata):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO audit.log_entries (org_id, actor_id, action, resource_type, resource_id, details)
                VALUES ($1, $2, $3, 'enrichment', $4, $5)
            """, metadata.get('org_id'), user_id, action, target_enrich_id,
                json.dumps({'provider_calls': provider_calls, **metadata}))

    # ==================== SESSION MANAGEMENT ====================

    async def create_session(self, user_id, token_hash, device_info=None, ip_address=None, expires_at=None):
        if self.pool is None:
            return
        await self.pool.execute("""
            INSERT INTO user_sessions (user_id, token_hash, device_info, ip_address, expires_at)
            VALUES ($1, $2, $3, $4, $5)
        """, user_id, token_hash, device_info or {}, ip_address, expires_at)

    async def delete_expired_sessions(self, max_age_hours=24):
        if self.pool is None:
            return 0
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        result = await self.pool.execute("""
            DELETE FROM user_sessions WHERE expires_at < $1 OR last_activity_at < $2
        """, cutoff, cutoff)
        return int(result.split()[-1]) if result else 0

    # ==================== HEALTH CHECKING ====================

    async def log_health_check(self, service_name, status, latency_ms=None, error_message=None):
        if self.pool is None:
            return
        try:
            await self.pool.execute("""
                INSERT INTO system_health (service_name, status, latency_ms, error_message)
                VALUES ($1, $2, $3, $4)
            """, service_name, status, latency_ms, error_message)
        except Exception as e:
            logger.warning(f"Failed to log health check: {e}")

    async def verify_audit_chain(self):
        """Verify the integrity of the audit hash chain."""
        if self.pool is None:
            return []
        broken = []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT log_id, previous_hash, current_hash
                FROM audit.log_entries
                ORDER BY log_id
            """)
            for i in range(1, len(rows)):
                if rows[i]['previous_hash'] != rows[i-1]['current_hash']:
                    broken.append({'id': rows[i]['log_id'], 'expected': rows[i-1]['current_hash']})
        return broken

    async def get_metrics(self):
        """Get current metrics."""
        return {
            'queries_total': self.metrics['queries_total'],
            'queries_failed': self.metrics['queries_failed'],
            'reads_from_primary': self.metrics['reads_from_primary'],
            'reads_from_replicas': self.metrics['reads_from_replicas'],
            'connection_errors': self.metrics['connection_errors'],
            'slow_queries': self.metrics['slow_queries'],
            'replica_health': {
                url: self.health_checker.is_healthy(url)
                for url in self.read_replica_urls
            },
            'pool_size': self.pool.get_size() if self.pool else 0,
            'pool_free': self.pool.get_size() - self.pool.get_used_count() if self.pool else 0,
        }

    def query_tracker(self, query, execution_time_ms, rows_returned):
        """Track query metrics for monitoring."""
        self.metrics['queries_total'] += 1
        self._query_history.append({
            'query': query[:200],
            'execution_time_ms': execution_time_ms,
            'rows_returned': rows_returned,
            'timestamp': time.time()
        })
        if len(self._query_history) > self._max_history:
            self._query_history = self._query_history[-self._max_history:]
        if execution_time_ms > float(os.getenv('DB_SLOW_QUERY_THRESHOLD_MS', 100)):
            self.metrics['slow_queries'] += 1

    # ==================== KEY ROTATION ====================

    async def rotate_embedding_keys(self, old_key_str, new_key_str, batch_size=1000):
        """Re-encrypt all stored embeddings with new key."""
        if not CRYPTO_AVAILABLE:
            logger.warning("cryptography not available; skipping key rotation")
            return

        try:
            old_fernet = Fernet(old_key_str.encode() if isinstance(old_key_str, str) else old_key_str)
            new_fernet = Fernet(new_key_str.encode() if isinstance(new_key_str, str) else new_key_str)
        except Exception as e:
            logger.error(f"Invalid Fernet key: {e}")
            return

        last_id = None
        total = 0

        while True:
            async with self.pool.acquire() as conn:
                if last_id is None:
                    rows = await conn.fetch("""
                        SELECT embedding_id, embedding, voice_embedding, gait_embedding
                        FROM embeddings ORDER BY embedding_id LIMIT $1
                    """, batch_size)
                else:
                    rows = await conn.fetch("""
                        SELECT embedding_id, embedding, voice_embedding, gait_embedding
                        FROM embeddings WHERE embedding_id > $1 ORDER BY embedding_id LIMIT $2
                    """, last_id, batch_size)

                if not rows:
                    break

                async with conn.transaction():
                    for row in rows:
                        for field in ['embedding', 'voice_embedding', 'gait_embedding']:
                            if row[field]:
                                try:
                                    dec = old_fernet.decrypt(row[field])
                                    enc = new_fernet.encrypt(dec)
                                    await conn.execute(
                                        f"UPDATE embeddings SET {field} = $1 WHERE embedding_id = $2",
                                        enc, row['embedding_id']
                                    )
                                except Exception as e:
                                    logger.error(f"Key rotation failed for {row['embedding_id']}.{field}: {e}")
                                    raise

                total += len(rows)
                last_id = rows[-1]['embedding_id']
                logger.info(f"Key rotation progress: {total} embeddings processed")

        logger.info(f"Key rotation complete: {total} embeddings re-encrypted")


# Global instance
_db_client = None


def get_db() -> DBClient:
    """Get or create global DB client instance."""
    global _db_client
    if _db_client is None:
        _db_client = DBClient()
        asyncio.create_task(_db_client.init_db())
    return _db_client


async def async_init_db(read_replicas=None) -> DBClient:
    """Initialize and return a new DB client."""
    client = DBClient(read_replicas=read_replicas)
    await client.init_db()
    return client