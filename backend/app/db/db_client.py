try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

import numpy as np
from typing import List, Dict, Any, Optional
import os
import uuid
import json
import hashlib
from datetime import datetime, timedelta
from ..security.secrets_vault import vault
try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None

try:
    import boto3
    from botocore.exceptions import NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None
    NoCredentialsError = Exception


class DBClient:
    def __init__(self, read_replicas: list = None):
        self.pool = None
        self.read_replica_pools = []
        self.kms_client = self._init_kms()
        self.encryption_key = self._load_encryption_key()
        
        # Initialize read replicas if provided
        if read_replicas:
            self.read_replica_urls = read_replicas
        else:
            # Read from environment variable (comma-separated)
            replica_urls = os.getenv('DB_READ_REPLICAS', '')
            self.read_replica_urls = [url.strip() for url in replica_urls.split(',') if url.strip()]
        
        self.current_replica_index = 0


    async def init_db(self):
        from ..offline.sync import get_offline_sync
        await get_offline_sync()
        
        if ASYNCPG_AVAILABLE:
            try:
                # Retrieve DB credentials from Vault if configured, fallback to environment
                db_user = os.getenv('DB_USER', 'postgres')
                db_password = vault.get_secret('DB_PASSWORD')
                if db_password is None:
                    db_password = os.getenv('DB_PASSWORD', 'password')
                db_name = os.getenv('DB_NAME', 'face_recognition')
                db_host = os.getenv('DB_HOST', 'localhost')
                db_port = int(os.getenv('DB_PORT', 5432))
            
                # Initialize primary connection pool
                self.pool = await asyncpg.create_pool(
                    user=db_user,
                    password=db_password,
                    database=db_name,
                    host=db_host,
                    port=db_port,
                    min_size=5,
                    max_size=20
                )
                await self._create_tables()
                
                # Initialize read replica pools if configured
                await self._init_read_replicas(db_user, db_password, db_name)
            except Exception as e:
                import logging
                logging.getLogger('__name__').warning(f"PostgreSQL connection failed: {e}. Using in-memory fallback.")
                self.pool = None
        else:
            # Fallback: offline SQLite primary
            self.pool = None
    
    async def _init_read_replicas(self, db_user: str, db_password: str, db_name: str):
        """
        Initialize read replica connection pools for load balancing reads.
        """
        if not self.read_replica_urls:
            return
        
        for replica_url in self.read_replica_urls:
            try:
                # Parse replica URL (format: host:port or full connection string)
                if '://' in replica_url:
                    # Full connection string
                    replica_pool = await asyncpg.create_pool(
                        replica_url,
                        min_size=2,
                        max_size=10
                    )
                else:
                    # host:port format
                    if ':' in replica_url:
                        replica_host, replica_port = replica_url.split(':')
                        replica_port = int(replica_port)
                    else:
                        replica_host = replica_url
                        replica_port = 5432
                    
                    replica_pool = await asyncpg.create_pool(
                        user=db_user,
                        password=db_password,
                        database=db_name,
                        host=replica_host,
                        port=replica_port,
                        min_size=2,
                        max_size=10
                    )
                
                self.read_replica_pools.append(replica_pool)
                print(f"Read replica connected: {replica_url}")
            except Exception as e:
                print(f"Failed to connect to read replica {replica_url}: {e}")
    
    async def _get_read_pool(self):
        """
        Get a read replica pool using round-robin load balancing.
        Falls back to primary pool if no replicas available.
        """
        if self.read_replica_pools:
            pool = self.read_replica_pools[self.current_replica_index]
            self.current_replica_index = (self.current_replica_index + 1) % len(self.read_replica_pools)
            return pool
        return self.pool


    async def _create_tables(self):
        async with self.pool.acquire() as conn:
            # Enable pgvector
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # Persons table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS persons (
                    person_id UUID PRIMARY KEY,
                    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
                    name TEXT,
                    age INTEGER,
                    gender TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    consent_record_id UUID
                );
            """)

            # Embeddings table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    embedding_id UUID PRIMARY KEY,
                    person_id UUID REFERENCES persons(person_id),
                    embedding VECTOR(512),  -- Face embedding
                    voice_embedding VECTOR(192),  -- Voice embedding (optional)
                    gait_embedding VECTOR(7),  -- Gait embedding (Hu Moments, 7-d)
                    camera_id TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # Consent logs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS consent_logs (
                    consent_record_id UUID PRIMARY KEY,
                    person_id UUID,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    client_id TEXT,
                    consent_text_version TEXT,
                    captured_ip TEXT,
                    signed_token TEXT
                );
            """)

            # Audit log (Forensic Ledger - Tamper-proof hash-chained)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    action TEXT,
                    person_id UUID,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    details JSONB,
                    previous_hash TEXT,
                    hash TEXT
                );
            """)

            # Feedback table for adaptive learning
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id UUID PRIMARY KEY,
                    person_id UUID,
                    recognition_id UUID,  -- Link to recognition event
                    correct_person_id UUID,
                    confidence_score FLOAT,
                    feedback_type TEXT,  -- 'correct', 'incorrect', 'unknown'
                    timestamp TIMESTAMP DEFAULT NOW()
                );
            """)

            # Model versions for OTA updates - Model Registry
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    version VARCHAR(100) NOT NULL,
                    framework VARCHAR(50) NOT NULL,
                    architecture TEXT,
                    input_shape INTEGER[],
                    output_dim INTEGER,
                    description TEXT,
                    training_dataset TEXT,
                    metrics JSONB,
                    model_path TEXT NOT NULL,
                    size_bytes BIGINT,
                    checksum CHAR(64) NOT NULL,
                    signature TEXT,
                    status VARCHAR(50) DEFAULT 'staging',
                    tags JSONB DEFAULT '[]',
                    min_requirements JSONB DEFAULT '{}',
                    uploaded_by TEXT REFERENCES users(user_id),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    download_count INTEGER DEFAULT 0,
                    promoted_at TIMESTAMP,
                    CONSTRAINT unique_name_version UNIQUE(name, version)
                );
            """)
            
            # Index for model lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_versions_name ON model_versions(name);
                CREATE INDEX IF NOT EXISTS idx_model_versions_status ON model_versions(status);
            """)

            # Federated learning updates
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS federated_updates (
                    update_id UUID PRIMARY KEY,
                    device_id TEXT,
                    model_gradients JSONB,
                    num_samples INTEGER,
                    timestamp TIMESTAMP DEFAULT NOW()
                );
            """)

            # Edge devices
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS edge_devices (
                    device_id TEXT PRIMARY KEY,
                    model_version UUID REFERENCES model_versions(version_id),
                    last_seen TIMESTAMP DEFAULT NOW(),
                    status TEXT
                );
            """)

            # Public enrichment tables
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS consents (
                    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    subject_id TEXT,
                    consent_text_version TEXT,
                    granted_at TIMESTAMPTZ,
                    granted_by TEXT,
                    ip_addr TEXT,
                    token TEXT,
                    expires_at TIMESTAMPTZ
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS enrichment_results (
                    enrich_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    query TEXT,
                    subject TEXT,
                    summary JSONB,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    expires_at TIMESTAMPTZ,
                    requested_by TEXT,
                    purpose TEXT
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    action TEXT,
                    user_id TEXT,
                    target_enrich_id UUID,
                    provider_calls JSONB,
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            """)

            # B2B - Organizations, Teams, Members, API Keys
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL,
                    subscription_tier TEXT DEFAULT 'free',
                    billing_email TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS org_members (
                    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
                    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
                    role TEXT DEFAULT 'viewer',
                    joined_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (org_id, user_id)
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
                    api_key TEXT UNIQUE NOT NULL,
                    name TEXT,
                    scopes JSONB,
                    last_used TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # Camera & Stream Management
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cameras (
                    camera_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    rtsp_url TEXT,
                    location TEXT,
                    status TEXT DEFAULT 'offline',
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # Recognition Events (Timeline & Analytics)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS recognition_events (
                    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
                    camera_id UUID REFERENCES cameras(camera_id),
                    person_id UUID REFERENCES persons(person_id),
                    confidence_score FLOAT,
                    image_path TEXT,
                    metadata JSONB,
                    timestamp TIMESTAMP DEFAULT NOW()
                );
            """)

            # Rule Engine & Alerts
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    condition JSONB,
                    actions JSONB,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    rule_id UUID REFERENCES alert_rules(rule_id) ON DELETE CASCADE,
                    event_id UUID REFERENCES recognition_events(event_id),
                    status TEXT DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # System Health & SLA Tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS system_health (
                    id SERIAL PRIMARY KEY,
                    service_name TEXT,
                    status TEXT,
                    latency_ms FLOAT,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT NOW()
                );
            """)

            # SaaS - Users, Plans, Subscriptions, Payments, Usage, Support
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE,
                    name TEXT,
                    full_name TEXT,
                    hashed_password TEXT,
                    subscription_tier TEXT DEFAULT 'free',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    name TEXT,
                    price FLOAT,
                    currency TEXT,
                    interval TEXT,
                    features JSONB,
                    limits JSONB
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    subscription_id TEXT PRIMARY KEY,
                    user_id TEXT REFERENCES users(user_id),
                    plan_id TEXT REFERENCES plans(plan_id),
                    status TEXT,
                    current_period_end TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id TEXT PRIMARY KEY,
                    user_id TEXT REFERENCES users(user_id),
                    amount FLOAT,
                    currency TEXT,
                    status TEXT,
                    stripe_payment_id TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    user_id TEXT REFERENCES users(user_id),
                    period_start TIMESTAMP,
                    period_end TIMESTAMP,
                    recognitions_used INTEGER DEFAULT 0,
                    enrollments_used INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, period_start, period_end)
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    user_id TEXT REFERENCES users(user_id),
                    subject TEXT,
                    description TEXT,
                    priority TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)

    def _init_kms(self):
        # Initialize AWS KMS client
        if BOTO3_AVAILABLE:
            try:
                return boto3.client('kms', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            except NoCredentialsError:
                # Fallback to local key
                return None
        else:
            return None

    def _load_encryption_key(self) -> bytes:
        # Use centralized secrets vault
        key = vault.get_encryption_key()
        
        # Ensure it's exactly 32 bytes and base64 encoded for Fernet
        import base64
        key_bytes = key.encode()[:32].ljust(32, b'\0')
        return base64.urlsafe_b64encode(key_bytes)

    def _encrypt_embedding(self, embedding: np.ndarray) -> bytes:
        if CRYPTOGRAPHY_AVAILABLE:
            fernet = Fernet(self.encryption_key)
            data = embedding.tobytes()
            return fernet.encrypt(data)
        else:
            # Fallback: no encryption
            return embedding.tobytes()

    def _decrypt_embedding(self, encrypted_data: bytes) -> np.ndarray:
        if CRYPTOGRAPHY_AVAILABLE:
            fernet = Fernet(self.encryption_key)
            data = fernet.decrypt(encrypted_data)
            return np.frombuffer(data, dtype=np.float32)
        else:
            # Fallback: no decryption
            return np.frombuffer(encrypted_data, dtype=np.float32)

    async def rotate_embedding_keys(self, old_key_str: str, new_key_str: str, batch_size: int = 1000):
        """
        Re-encrypt all stored embeddings (face, voice, gait) using new key.
        Processes in batches within transactions to allow resumable operation.
        """
        import logging
        logger = logging.getLogger("key-rotation")
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("cryptography not available; skipping key rotation")
            return
        
        if self.pool is None:
            logger.warning("Database pool not initialized; skipping key rotation")
            return
        
        # Prepare Fernet instances
        try:
            old_fernet = Fernet(old_key_str.encode() if isinstance(old_key_str, str) else old_key_str)
            new_fernet = Fernet(new_key_str.encode() if isinstance(new_key_str, str) else new_key_str)
        except Exception as e:
            logger.error(f"Invalid Fernet key format: {e}")
            return

        last_id = None
        total_processed = 0

        while True:
            async with self.pool.acquire() as conn:
                # Fetch next batch ordered by embedding_id
                if last_id is None:
                    query = """
                        SELECT embedding_id, embedding, voice_embedding, gait_embedding
                        FROM embeddings
                        ORDER BY embedding_id
                        LIMIT $1
                    """
                    rows = await conn.fetch(query, batch_size)
                else:
                    query = """
                        SELECT embedding_id, embedding, voice_embedding, gait_embedding
                        FROM embeddings
                        WHERE embedding_id > $1
                        ORDER BY embedding_id
                        LIMIT $2
                    """
                    rows = await conn.fetch(query, last_id, batch_size)

                if not rows:
                    break

                # Process batch in a single transaction
                async with conn.transaction():
                    for row in rows:
                        emb_id = row['embedding_id']
                        updated = False
                        # Face embedding
                        if row['embedding']:
                            try:
                                dec_bytes = old_fernet.decrypt(row['embedding'])
                                new_enc = new_fernet.encrypt(dec_bytes)
                                await conn.execute(
                                    "UPDATE embeddings SET embedding = $1 WHERE embedding_id = $2",
                                    new_enc, emb_id
                                )
                                updated = True
                            except Exception as e:
                                logger.error(f"Failed to rotate face embedding {emb_id}: {e}")
                                raise  # rollback batch
                        # Voice embedding
                        if row['voice_embedding']:
                            try:
                                dec_bytes = old_fernet.decrypt(row['voice_embedding'])
                                new_enc = new_fernet.encrypt(dec_bytes)
                                await conn.execute(
                                    "UPDATE embeddings SET voice_embedding = $1 WHERE embedding_id = $2",
                                    new_enc, emb_id
                                )
                                updated = True
                            except Exception as e:
                                logger.error(f"Failed to rotate voice embedding {emb_id}: {e}")
                                raise
                        # Gait embedding
                        if row['gait_embedding']:
                            try:
                                dec_bytes = old_fernet.decrypt(row['gait_embedding'])
                                new_enc = new_fernet.encrypt(dec_bytes)
                                await conn.execute(
                                    "UPDATE embeddings SET gait_embedding = $1 WHERE embedding_id = $2",
                                    new_enc, emb_id
                                )
                                updated = True
                            except Exception as e:
                                logger.error(f"Failed to rotate gait embedding {emb_id}: {e}")
                                raise
                        if not updated:
                            logger.warning(f"No embeddings found for {emb_id}")
                total_processed += len(rows)
                last_id = rows[-1]['embedding_id']
                logger.info(f"Rotated embeddings for {len(rows)} records (total: {total_processed})")

        logger.info(f"Embedding rotation complete. Total processed: {total_processed}")

    async def enroll_person(self, person_id: str, name: str, embeddings: List[np.ndarray], consent_record: Dict[str, Any], camera_id: str = None, voice_embeddings: List[np.ndarray] = None, gait_embedding: np.ndarray = None, age: int = None, gender: str = None) -> str:
        if self.pool is None:
            # In-memory implementation
            self._in_memory_db['persons'][person_id] = {
                'person_id': person_id, 'name': name, 'age': age, 'gender': gender, 'consent_record_id': consent_record['consent_record_id']}
            for i, emb in enumerate(embeddings):
                emb_id = str(uuid.uuid4())
                encrypted_emb = self._encrypt_embedding(emb)
                voice_emb = voice_embeddings[i] if voice_embeddings and i < len(
                    voice_embeddings) else None
                encrypted_voice = self._encrypt_embedding(
                    voice_emb) if voice_emb is not None else None
                encrypted_gait = self._encrypt_embedding(
                    gait_embedding) if gait_embedding is not None else None
                self._in_memory_db['embeddings'][emb_id] = {'embedding_id': emb_id, 'person_id': person_id, 'embedding': encrypted_emb,
                                                            'voice_embedding': encrypted_voice, 'gait_embedding': encrypted_gait, 'camera_id': camera_id}
            self._in_memory_db['consent_logs'][consent_record['consent_record_id']
                                               ] = consent_record
            self._in_memory_db['audit_log'].append({'action': 'enroll', 'person_id': person_id, 'details': {'num_embeddings': len(
                embeddings), 'has_voice': voice_embeddings is not None, 'has_gait': gait_embedding is not None}})
            return person_id

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Insert person
                await conn.execute("""
                    INSERT INTO persons (person_id, name, age, gender, consent_record_id)
                    VALUES ($1, $2, $3, $4, $5)
                """, person_id, name, age, gender, consent_record['consent_record_id'])

                # Insert embeddings (plain vectors for pgvector similarity search)
                for i, emb in enumerate(embeddings):
                    emb_id = str(uuid.uuid4())
                    # Convert numpy arrays to Python lists for pgvector
                    emb_list = emb.tolist()
                    voice_emb = voice_embeddings[i] if voice_embeddings and i < len(
                        voice_embeddings) else None
                    voice_list = voice_emb.tolist() if voice_emb is not None else None
                    gait_list = gait_embedding.tolist() if gait_embedding is not None else None
                    await conn.execute("""
                        INSERT INTO embeddings (embedding_id, person_id, embedding, voice_embedding, gait_embedding, camera_id)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, emb_id, person_id, emb_list, voice_list, gait_list, camera_id)

                # Insert consent log
                await conn.execute("""
                    INSERT INTO consent_logs (consent_record_id, person_id, client_id, consent_text_version, captured_ip, signed_token)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, consent_record['consent_record_id'], person_id, consent_record.get('client_id'), consent_record.get('consent_text_version'), consent_record.get('captured_ip'), consent_record.get('signed_token'))

                # Audit log with forensic hash chaining
                last_log = await conn.fetchrow("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1")
                prev_hash = last_log['hash'] if last_log else "0" * 64
                
                import hashlib
                import json
                log_content = f"{prev_hash}{'enroll'}{person_id}{json.dumps({'num_embeddings': len(embeddings)})}"
                current_hash = hashlib.sha256(log_content.encode()).hexdigest()

                await conn.execute("""
                    INSERT INTO audit_log (action, person_id, details, previous_hash, hash)
                    VALUES ('enroll', $1, $2, $3, $4)
                """, person_id, {'num_embeddings': len(embeddings), 'has_voice': voice_embeddings is not None, 'has_gait': gait_embedding is not None}, prev_hash, current_hash)

        return person_id

    async def recognize_faces(self, query_embedding: np.ndarray, top_k: int = 1, threshold: float = 0.6, camera_id: str = None, voice_embedding: np.ndarray = None, gait_embedding: np.ndarray = None) -> List[Dict[str, Any]]:
        # Multi-modal fusion: combine face, voice, gait scores
        async with self.pool.acquire() as conn:
            face_query = """
                SELECT person_id, embedding <=> $1 as distance
                FROM embeddings
                WHERE camera_id = $3 OR $3 IS NULL
                ORDER BY embedding <=> $1
                LIMIT $2
            """
            face_results = await conn.fetch(face_query, query_embedding.tolist(), top_k * 2, camera_id)  # Get more candidates

            matches = []
            for row in face_results:
                face_distance = row['distance']
                if face_distance > threshold:
                    continue

                person_id = row['person_id']
                combined_score = 1 - face_distance  # Start with face score

                # Add voice score if available
                if voice_embedding is not None:
                    voice_row = await conn.fetchrow("""
                        SELECT voice_embedding <=> $1 as distance
                        FROM embeddings
                        WHERE person_id = $2 AND voice_embedding IS NOT NULL
                        LIMIT 1
                    """, voice_embedding.tolist(), person_id)
                    if voice_row and voice_row['distance'] <= threshold:
                        # Weight: voice contributes 20% of face score
                        combined_score += (1 - voice_row['distance']) * 0.2

                # Add gait score if available
                if gait_embedding is not None:
                    gait_row = await conn.fetchrow("""
                        SELECT gait_embedding <=> $1 as distance
                        FROM embeddings
                        WHERE person_id = $2 AND gait_embedding IS NOT NULL
                        LIMIT 1
                    """, gait_embedding.tolist(), person_id)
                    if gait_row and gait_row['distance'] <= threshold:
                        # Weight
                        combined_score += (1 - gait_row['distance']) * 0.2

                if combined_score >= (1 - threshold):  # Adjusted threshold
                    person = await conn.fetchrow("SELECT name, age, gender FROM persons WHERE person_id = $1", person_id)
                    matches.append({
                        'person_id': person_id,
                        'name': person['name'],
                        'age': person['age'],
                        'gender': person['gender'],
                        'distance': 1 - combined_score,  # Convert back to distance
                        'score': combined_score
                    })

            # Sort by combined score and limit to top_k
            matches.sort(key=lambda x: x['score'], reverse=True)
            return matches[:top_k]

    async def get_person(self, person_id: str) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            person = await conn.fetchrow("SELECT * FROM persons WHERE person_id = $1", person_id)
            if not person:
                return None

            embeddings = await conn.fetch("SELECT embedding_id FROM embeddings WHERE person_id = $1", person_id)
            consent = await conn.fetchrow("SELECT * FROM consent_logs WHERE person_id = $1", person_id)

            return {
                'person_id': person['person_id'],
                'name': person['name'],
                'age': person['age'],
                'gender': person['gender'],
                'embeddings': [e['embedding_id'] for e in embeddings],
                'consent_record': dict(consent) if consent else None
            }

    async def delete_person(self, person_id: str) -> bool:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Delete embeddings
                await conn.execute("DELETE FROM embeddings WHERE person_id = $1", person_id)
                # Delete consent log
                await conn.execute("DELETE FROM consent_logs WHERE person_id = $1", person_id)
                # Delete feedback
                await conn.execute("DELETE FROM feedback WHERE person_id = $1", person_id)
                # Delete person
                await conn.execute("DELETE FROM persons WHERE person_id = $1", person_id)
                # Delete audit logs related to this person
                await conn.execute("DELETE FROM audit_log WHERE person_id = $1", person_id)
                # Audit log for the deletion itself (anonymized)
                await conn.execute("""
                    INSERT INTO audit_log (action, details)
                    VALUES ('gdpr_delete', $1)
                """, {'deleted_person_id': person_id})

        return True

    async def get_person_full_data(self, person_id: str) -> Optional[Dict[str, Any]]:
        """GDPR Data Export: Collects all data related to a person."""
        async with self.pool.acquire() as conn:
            person = await conn.fetchrow("SELECT * FROM persons WHERE person_id = $1", person_id)
            if not person: return None
            
            embeddings = await conn.fetch("SELECT * FROM embeddings WHERE person_id = $1", person_id)
            consent = await conn.fetchrow("SELECT * FROM consent_logs WHERE person_id = $1", person_id)
            audit = await conn.fetch("SELECT * FROM audit_log WHERE person_id = $1", person_id)
            feedback = await conn.fetch("SELECT * FROM feedback WHERE person_id = $1", person_id)
            
            # Convert UUIDs and Datetimes to strings for JSON serialization
            import json
            def serial(obj):
                if isinstance(obj, (datetime, uuid.UUID)):
                    return str(obj)
                raise TypeError("Type not serializable")

            return {
                "identity": dict(person) if person else None,
                "biometrics": [dict(e) for e in embeddings],
                "consent": dict(consent) if consent else None,
                "activity_history": [dict(a) for a in audit],
                "feedback": [dict(f) for f in feedback]
            }

    async def submit_feedback(self, person_id: str, recognition_id: str, correct_person_id: str, confidence_score: float, feedback_type: str) -> bool:
        async with self.pool.acquire() as conn:
            feedback_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO feedback (feedback_id, person_id, recognition_id, correct_person_id, confidence_score, feedback_type)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, feedback_id, person_id, recognition_id, correct_person_id, confidence_score, feedback_type)
        return True

    # Public Enrichment Methods
    async def create_consent(self, subject_id: Optional[str], consent_text_version: str, granted_by: str, ip_addr: str, purpose: str) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            consent_id = str(uuid.uuid4())
            token = f"consent:{consent_id}"  # Simple token for demo
            expires_at = datetime.utcnow() + timedelta(days=30)
            await conn.execute("""
                INSERT INTO consents (consent_id, subject_id, consent_text_version, granted_at, granted_by, ip_addr, token, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, consent_id, subject_id, consent_text_version, datetime.utcnow(), granted_by, ip_addr, token, expires_at)
            return {
                "consent_id": consent_id,
                "token": token,
                "expires_at": expires_at.isoformat()
            }

    async def validate_consent(self, token: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM consents WHERE token = $1 AND expires_at > now()
            """, token)
            return dict(row) if row else None
    
    async def get_consent(self, consent_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific consent record by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM consents WHERE consent_id = $1
            """, consent_id)
            return dict(row) if row else None
    
    async def revoke_consent(self, consent_id: str, reason: str) -> bool:
        """Mark consent as revoked."""
        async with self.pool.acquire() as conn:
            # Set expires_at to now (effectively revoking)
            # In production, you might add a revoked_at column
            result = await conn.execute("""
                UPDATE consents 
                SET expires_at = NOW()
                WHERE consent_id = $1 AND expires_at > now()
            """, consent_id)
            return result == "UPDATE 1"
    
    async def get_consent_history(self, subject_id: str) -> List[Dict[str, Any]]:
        """Get all consent records for a subject."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM consents WHERE subject_id = $1
                ORDER BY granted_at DESC
            """, subject_id)
            return [dict(row) for row in rows]
    
    async def get_active_consents(self, subject_id: str, purpose: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get currently valid (non-expired) consents for subject."""
        async with self.pool.acquire() as conn:
            if purpose:
                rows = await conn.fetch("""
                    SELECT * FROM consents 
                    WHERE subject_id = $1 
                      AND expires_at > now()
                      AND purpose = $2
                """, subject_id, purpose)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM consents 
                    WHERE subject_id = $1 AND expires_at > now()
                """, subject_id)
            return [dict(row) for row in rows]

    async def save_enrichment_result(self, query: str, subject: str, summary: List[Dict[str, Any]], requested_by: str, purpose: str, ttl_days: int = 7) -> str:
        async with self.pool.acquire() as conn:
            enrich_id = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(days=ttl_days)
            await conn.execute("""
                INSERT INTO enrichment_results (enrich_id, query, subject, summary, expires_at, requested_by, purpose)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, enrich_id, query, subject, summary, expires_at, requested_by, purpose)
            return enrich_id

    async def get_enrichment_result(self, enrich_id: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM enrichment_results WHERE enrich_id = $1 AND expires_at > now()
            """, enrich_id)
            return dict(row) if row else None

    async def log_audit(self, action: str, user_id: str, target_enrich_id: Optional[str], provider_calls: List[Dict[str, Any]], metadata: Dict[str, Any]) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO audit_logs (action, user_id, target_enrich_id, provider_calls, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, action, user_id, target_enrich_id, provider_calls, metadata)

    async def get_audit_logs(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            if user_id:
                rows = await conn.fetch("""
                    SELECT * FROM audit_logs WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2
                """, user_id, limit)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT $1
                """, limit)
            return [dict(row) for row in rows]

    async def flag_for_review(self, enrich_id: str, reason: Optional[str] = None) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE enrichment_results SET summary = jsonb_set(summary, '{flagged}', 'true'::jsonb) WHERE enrich_id = $1
            """, enrich_id)
            # Log the flag action
            await self.log_audit("flag_for_review", "system", enrich_id, [], {"reason": reason or "User flagged"})
            return True

    async def delete_enrichment_result(self, enrich_id: str) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM enrichment_results WHERE enrich_id = $1", enrich_id)
            await self.log_audit("delete_result", "admin", enrich_id, [], {})
            return True

    # SaaS Database Methods
    async def create_user(self, user_id: str, email: str, name: str, subscription_tier: str = "free") -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, email, name, subscription_tier, created_at)
                VALUES ($1, $2, $3, $4, NOW())
            """, user_id, email, name, subscription_tier)
        return True

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return dict(row) if row else None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
            return dict(row) if row else None

    async def update_user(self, user_id: str, email: str, name: str, subscription_tier: str) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users SET email = $1, name = $2, subscription_tier = $3 WHERE user_id = $4
            """, email, name, subscription_tier, user_id)
        return True

    async def delete_user(self, user_id: str) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
        return True

    # Plans
    async def get_all_plans(self) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM plans ORDER BY price")
            return [dict(row) for row in rows]

    async def get_plan_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM plans WHERE plan_id = $1", plan_id)
            return dict(row) if row else None

    # Subscriptions
    async def create_subscription(self, subscription_id: str, user_id: str, plan_id: str, status: str = "active", expires_at: Optional[datetime] = None) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO subscriptions (subscription_id, user_id, plan_id, status, created_at, expires_at)
                VALUES ($1, $2, $3, $4, NOW(), $5)
            """, subscription_id, user_id, plan_id, status, expires_at)
        return True

    async def get_user_by_stripe_customer(self, stripe_customer_id: str) -> Optional[Dict[str, Any]]:
        """Look up user by their Stripe customer ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT u.* FROM users u
                JOIN subscriptions s ON u.user_id = s.user_id
                WHERE s.stripe_customer_id = $1
                LIMIT 1
            """, stripe_customer_id)
            return dict(row) if row else None
    
    async def link_stripe_customer(self, user_id: str, stripe_customer_id: str) -> bool:
        """Link Stripe customer ID to user record."""
        async with self.pool.acquire() as conn:
            # Add stripe_customer_id column if not exists (migration required)
            await conn.execute("""
                UPDATE subscriptions 
                SET stripe_customer_id = $1 
                WHERE user_id = $2 AND status = 'active'
            """, stripe_customer_id, user_id)
            return True
    
    async def downgrade_to_free_tier(self, user_id: str) -> bool:
        """Downgrade user to free tier after payment failure."""
        async with self.pool.acquire() as conn:
            # Cancel all active subscriptions
            await conn.execute("""
                UPDATE subscriptions 
                SET status = 'cancelled' 
                WHERE user_id = $1 AND status = 'active'
            """, user_id)
            # Set user tier to free
            await conn.execute("""
                UPDATE users 
                SET subscription_tier = 'free' 
                WHERE user_id = $1
            """, user_id)
            # Reset usage tracking
            await conn.execute("""
                DELETE FROM usage WHERE user_id = $1
            """, user_id)
            return True
    
    async def update_subscription_plan(self, user_id: str, new_plan_id: str) -> bool:
        """Update user's subscription plan (upgrade/downgrade)."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE subscriptions 
                SET plan_id = $1, updated_at = NOW()
                WHERE user_id = $2 AND status = 'active'
            """, new_plan_id, user_id)
            # Also update user tier
            await conn.execute("""
                UPDATE users 
                SET subscription_tier = $1 
                WHERE user_id = $2
            """, new_plan_id, user_id)
            return result == "UPDATE 1"
    
    async def deactivate_subscription(self, user_id: str) -> bool:
        """Deactivate subscription (cancellation)."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE subscriptions 
                SET status = 'cancelled', cancelled_at = NOW()
                WHERE user_id = $1 AND status = 'active'
            """, user_id)
            # Downgrade user to free
            await conn.execute("""
                UPDATE users 
                SET subscription_tier = 'free' 
                WHERE user_id = $1
            """, user_id)
            return result == "UPDATE 1"
    
    async def extend_subscription(self, subscription_id: str, new_end_date: datetime) -> bool:
        """Extend subscription expiry after successful renewal."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE subscriptions 
                SET expires_at = $1, status = 'active'
                WHERE subscription_id = $2
            """, new_end_date, subscription_id)
            return result == "UPDATE 1"
    
    async def mark_payment_failed(self, payment_intent_id: str) -> bool:
        """Mark a payment as failed."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE payments 
                SET status = 'failed', updated_at = NOW()
                WHERE stripe_payment_id = $1
            """, payment_intent_id)
            return True
    
    async def log_payment(self, user_id: str, amount: float, currency: str, 
                         status: str, stripe_payment_id: Optional[str] = None, 
                         metadata: Optional[Dict] = None) -> bool:
        """Log payment event."""
        async with self.pool.acquire() as conn:
            payment_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO payments (payment_id, user_id, amount, currency, status, stripe_payment_id, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7)
            """, payment_id, user_id, amount, currency, status, stripe_payment_id, json.dumps(metadata or {}))
            return True

    async def cancel_subscription(self, subscription_id: str) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE subscriptions SET status = 'cancelled' WHERE subscription_id = $1
            """, subscription_id)
        return True

    async def get_subscription_history(self, user_id: str) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC
            """, user_id)
            return [dict(row) for row in rows]

    # Payments
    async def create_payment(self, payment_id: str, user_id: str, amount: float, currency: str = "USD", status: str = "pending", stripe_payment_id: Optional[str] = None) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO payments (payment_id, user_id, amount, currency, status, stripe_payment_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """, payment_id, user_id, amount, currency, status, stripe_payment_id)
        return True

    async def get_payment_history(self, user_id: str) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM payments WHERE user_id = $1 ORDER BY created_at DESC
            """, user_id)
            return [dict(row) for row in rows]

    # Usage
    async def get_usage(self, user_id: str) -> Optional[Dict[str, Any]]:
        now = datetime.utcnow()
        period_start = now.replace(day=1)
        if now.month == 12:
            period_end = now.replace(year=now.year + 1, month=1, day=1)
        else:
            period_end = now.replace(month=now.month + 1, day=1)
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM usage 
                WHERE user_id = $1 AND period_start = $2 AND period_end = $3
            """, user_id, period_start, period_end)
            if row:
                return dict(row)
            
            # Get user's plan limits
            sub = await self.get_subscription(user_id)
            if sub:
                plan = await self.get_plan_by_id(sub['plan_id'])
                if plan and plan.get('limits'):
                    return {
                        'user_id': user_id,
                        'period_start': period_start,
                        'period_end': period_end,
                        'recognitions_used': 0,
                        'enrollments_used': 0,
                        'recognitions_limit': plan['limits'].get('recognitions', 100),
                        'enrollments_limit': plan['limits'].get('enrollments', 10)
                    }
            
            return {
                'user_id': user_id,
                'period_start': period_start,
                'period_end': period_end,
                'recognitions_used': 0,
                'enrollments_used': 0,
                'recognitions_limit': 100,
                'enrollments_limit': 10
            }

    async def increment_usage(self, user_id: str, recognition: int = 0, enrollment: int = 0) -> bool:
        usage = await self.get_usage(user_id)
        if not usage:
            return False
            
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE usage SET 
                    recognitions_used = recognitions_used + $1,
                    enrollments_used = enrollments_used + $2
                WHERE user_id = $3 AND period_start = $4 AND period_end = $5
            """, recognition, enrollment, user_id, usage['period_start'], usage['period_end'])
        return True

    # Support Tickets
    async def create_ticket(self, ticket_id: str, user_id: str, subject: str, description: str, priority: str = "medium") -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO support_tickets (ticket_id, user_id, subject, description, priority, status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, 'open', NOW(), NOW())
            """, ticket_id, user_id, subject, description, priority)
        return True

    async def get_tickets(self, user_id: str) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM support_tickets WHERE user_id = $1 ORDER BY created_at DESC
            """, user_id)
            return [dict(row) for row in rows]

    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM support_tickets WHERE ticket_id = $1", ticket_id)
            return dict(row) if row else None

    # B2B & Org Methods
    async def create_organization(self, name: str, billing_email: str) -> str:
        async with self.pool.acquire() as conn:
            org_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO organizations (org_id, name, billing_email)
                VALUES ($1, $2, $3)
            """, org_id, name, billing_email)
            return org_id

    async def add_org_member(self, org_id: str, user_id: str, role: str = 'viewer') -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO org_members (org_id, user_id, role)
                VALUES ($1, $2, $3)
                ON CONFLICT (org_id, user_id) DO UPDATE SET role = $3
            """, org_id, user_id, role)
            return True

    async def get_user_orgs(self, user_id: str) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT o.*, m.role 
                FROM organizations o
                JOIN org_members m ON o.org_id = m.org_id
                WHERE m.user_id = $1
            """, user_id)
            return [dict(row) for row in rows]

    # API Keys
    async def create_api_key(self, org_id: str, name: str, scopes: List[str]) -> str:
        import secrets
        api_key = f"fr_{secrets.token_urlsafe(32)}"
        async with self.pool.acquire() as conn:
            key_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO api_keys (key_id, org_id, api_key, name, scopes)
                VALUES ($1, $2, $3, $4, $5)
            """, key_id, org_id, api_key, name, scopes)
            return api_key

    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT k.*, o.name as org_name, o.subscription_tier
                FROM api_keys k
                JOIN organizations o ON k.org_id = o.org_id
                WHERE k.api_key = $1
            """, api_key)
            if row:
                await conn.execute("UPDATE api_keys SET last_used = NOW() WHERE api_key = $1", api_key)
                return dict(row)
            return None

    # Camera Management
    async def add_camera(self, org_id: str, name: str, rtsp_url: str = None, location: str = None) -> str:
        async with self.pool.acquire() as conn:
            camera_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO cameras (camera_id, org_id, name, rtsp_url, location)
                VALUES ($1, $2, $3, $4, $5)
            """, camera_id, org_id, name, rtsp_url, location)
            return camera_id

    async def get_org_cameras(self, org_id: str) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM cameras WHERE org_id = $1", org_id)
            return [dict(row) for row in rows]

    # Recognition Events & Timeline
    async def log_recognition_event(self, org_id: str, person_id: Optional[str], camera_id: Optional[str], confidence: float, metadata: Dict[str, Any] = None) -> str:
        offline_sync = await get_offline_sync()
        event_id = str(uuid.uuid4())
        if self.pool is None:
            await offline_sync.cache_event({
                'event_id': event_id,
                'org_id': org_id,
                'person_id': person_id,
                'camera_id': camera_id,
                'confidence': confidence,
                'metadata': metadata
            })
        else:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO recognition_events (event_id, org_id, person_id, camera_id, confidence_score, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, event_id, org_id, person_id, camera_id, confidence, metadata)
        return event_id


    async def get_person_timeline(self, person_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT e.*, c.name as camera_name, c.location as camera_location
                FROM recognition_events e
                LEFT JOIN cameras c ON e.camera_id = c.camera_id
                WHERE e.person_id = $1
                ORDER BY e.timestamp DESC
                LIMIT $2
            """, person_id, limit)
            return [dict(row) for row in rows]

    async def get_org_events(self, org_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT e.*, p.name as person_name, c.name as camera_name
                FROM recognition_events e
                LEFT JOIN persons p ON e.person_id = p.person_id
                LEFT JOIN cameras c ON e.camera_id = c.camera_id
                WHERE e.org_id = $1
                ORDER BY e.timestamp DESC
                LIMIT $2
            """, org_id, limit)
            return [dict(row) for row in rows]

    async def update_ticket(self, ticket_id: str, description: Optional[str] = None, priority: Optional[str] = None) -> bool:
        async with self.pool.acquire() as conn:
            if description:
                await conn.execute("UPDATE support_tickets SET description = $1, updated_at = NOW() WHERE ticket_id = $2", description, ticket_id)
            if priority:
                await conn.execute("UPDATE support_tickets SET priority = $1, updated_at = NOW() WHERE ticket_id = $2", priority, ticket_id)
        return True

    async def delete_ticket(self, ticket_id: str) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM support_tickets WHERE ticket_id = $1", ticket_id)
        return True

    async def log_health_check(self, service: str, status: str, latency: float = 0, error: str = None):
        """Logs a health check for SLA monitoring."""
        if not self.pool: return False
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO system_health (service_name, status, latency_ms, error_message)
                VALUES ($1, $2, $3, $4)
            """, service, status, latency, error)
        return True

    # Model Registry Methods
    async def store_model_metadata(self, metadata) -> bool:
        """Store model metadata in DB"""
        if not self.pool:
            return False
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO model_versions 
                (name, version, framework, architecture, input_shape, output_dim,
                 description, training_dataset, metrics, model_path, size_bytes,
                 checksum, signature, status, tags, min_requirements, uploaded_by,
                 created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, NOW(), NOW())
                ON CONFLICT (name, version) DO UPDATE SET
                    framework = EXCLUDED.framework,
                    architecture = EXCLUDED.architecture,
                    input_shape = EXCLUDED.input_shape,
                    output_dim = EXCLUDED.output_dim,
                    description = EXCLUDED.description,
                    metrics = EXCLUDED.metrics,
                    size_bytes = EXCLUDED.size_bytes,
                    checksum = EXCLUDED.checksum,
                    signature = EXCLUDED.signature,
                    status = EXCLUDED.status,
                    tags = EXCLUDED.tags,
                    min_requirements = EXCLUDED.min_requirements,
                    updated_at = NOW()
            """,
            metadata.name, metadata.version, metadata.framework,
            metadata.architecture, json.dumps(metadata.input_shape), metadata.output_dim,
            metadata.description, metadata.training_dataset,
            json.dumps(metadata.metrics), f"{metadata.model_id}.{metadata.framework}",
            metadata.size_bytes, metadata.checksum, metadata.signature,
            metadata.status, json.dumps(metadata.tags or []),
            json.dumps(metadata.min_requirements or {}),
            metadata.uploaded_by
            )
        return True
    
    async def get_model_metadata(self, model_id: str) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM model_versions WHERE version_id = $1", model_id)
            return dict(row) if row else None
    
    async def list_model_metadata(self, name_filter: str = None, status: str = None) -> List[Dict]:
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM model_versions"
            params = []
            conditions = []
            if name_filter:
                conditions.append(f"name LIKE ${len(params)+1}")
                params.append(f"%{name_filter}%")
            if status:
                conditions.append(f"status = ${len(params)+1}")
                params.append(status)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY created_at DESC"
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def get_production_model(self, name: str) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM model_versions WHERE name = $1 AND status = 'production' ORDER BY created_at DESC LIMIT 1",
                name
            )
            return dict(row) if row else None
    
    async def update_model_status(self, model_id: str, status: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE model_versions SET status = $1, updated_at = NOW() WHERE version_id = $2",
                status, model_id
            )
            if status == "production":
                await conn.execute(
                    "UPDATE model_versions SET promoted_at = NOW() WHERE version_id = $1",
                    model_id
                )
            return result == "UPDATE 1"
    
    async def update_model_status_by_name(self, name: str, status: str, exclude_version: str = None) -> int:
        """Update status for all versions of a model except excluded"""
        async with self.pool.acquire() as conn:
            if exclude_version:
                result = await conn.execute(
                    "UPDATE model_versions SET status = $1 WHERE name = $2 AND version_id != $3",
                    status, name, exclude_version
                )
            else:
                result = await conn.execute(
                    "UPDATE model_versions SET status = $1 WHERE name = $2",
                    status, name
                )
            return int(result.split()[1]) if result.startswith('UPDATE') else 0
    
    async def increment_model_downloads(self, model_id: str) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE model_versions SET download_count = download_count + 1 WHERE version_id = $1",
                model_id
            )
            return True
    
    async def delete_model_metadata(self, model_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM model_versions WHERE version_id = $1", model_id)
            return result == "DELETE 1"
    
    async def get_config(self, key: str, default=None):
        """Get system configuration value (for registry settings)"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM system_config WHERE key = $1", key)
            return row['value'] if row else default

    # ============================================
    # Audit & Chain Integrity
    # ============================================
    async def log_audit_event(self, action: str, person_id: Optional[str] = None, 
                              details: Dict = None, zkp_proof: Optional[Dict] = None) -> str:
        """
        Log an event to the hash-chained audit_log.
        Returns the generated event ID.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Get last hash
                last_log = await conn.fetchrow("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1")
                prev_hash = last_log['hash'] if last_log else "0" * 64
                
                event_id = str(uuid.uuid4())
                timestamp = datetime.utcnow()
                
                # Compute hash of current log
                content = f"{event_id}|{action}|{person_id or ''}|{json.dumps(details or {})}|{prev_hash}|{timestamp.isoformat()}"
                current_hash = hashlib.sha256(content.encode()).hexdigest()
                
                await conn.execute("""
                    INSERT INTO audit_log (action, person_id, details, previous_hash, hash, zkp_proof)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, action, person_id, json.dumps(details or {}), prev_hash, current_hash, json.dumps(zkp_proof or {}))
                
                return event_id

    async def get_audit_logs_range(self, start_id: int = None, end_id: int = None) -> List[Dict]:
        """Get audit logs within an ID range (for chain verification)"""
        async with self.pool.acquire() as conn:
            if start_id and end_id:
                rows = await conn.fetch("SELECT * FROM audit_log WHERE id BETWEEN $1 AND $2 ORDER BY id", start_id, end_id)
            elif start_id:
                rows = await conn.fetch("SELECT * FROM audit_log WHERE id >= $1 ORDER BY id", start_id)
            else:
                rows = await conn.fetch("SELECT * FROM audit_log ORDER BY id")
            return [dict(row) for row in rows]

    async def verify_audit_chain(self) -> List[Dict]:
        """Verify tamper-evident chain; return list of broken links."""
        async with self.pool.acquire() as conn:
            logs = await conn.fetch("SELECT id, previous_hash, hash FROM audit_log ORDER BY id")
            broken = []
            for i in range(1, len(logs)):
                prev = logs[i-1]
                curr = logs[i]
                if curr['previous_hash'] != prev['hash']:
                    broken.append({
                        "broken_at_id": curr['id'],
                        "expected_prev": curr['previous_hash'],
                        "actual_prev": prev['hash']
                    })
            return broken

    # ============================================
    # MFA
    # ============================================
    async def log_mfa_attempt(self, user_id: str, attempt_type: str, success: bool, 
                              ip_address: str = None, user_agent: str = None) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO mfa_attempts (user_id, attempt_type, success, ip_address, user_agent)
                VALUES ($1, $2, $3, $4, $5)
            """, user_id, attempt_type, success, ip_address, user_agent)
            return True

    # ============================================
    # Video Recognition
    # ============================================
    async def log_video_recognition(self, video_path: str, camera_id: str, 
                                    org_id: str, total_frames: int, recognized_faces: List) -> str:
        """Log a video processing summary as a recognition_event"""
        event_id = str(uuid.uuid4())
        # Store a summary record
        summary = {
            "video_path": video_path,
            "total_frames": total_frames,
            "recognitions": len(recognized_faces),
            "faces": recognized_faces
        }
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO recognition_events 
                (event_id, org_id, camera_id, person_id, metadata)
                VALUES ($1, $2, $3, NULL, $4)
            """, event_id, org_id, camera_id, json.dumps(summary))
        return event_id

    # ============================================
    # Sessions Cleanup
    # ============================================
    async def cleanup_expired_sessions(self, max_age_hours: int) -> int:
        """Delete sessions older than given hours. Returns count deleted."""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM sessions 
                WHERE expires_at < NOW() - INTERVAL '1 second' * ($1 * 3600)
            """, max_age_hours)
            # Result like 'DELETE 5'
            parts = result.split()
            return int(parts[1]) if len(parts) >= 2 else 0

    async def delete_expired_sessions(self, max_age_hours: int) -> int:
        """Alias for cleanup_expired_sessions"""
        return await self.cleanup_expired_sessions(max_age_hours)

    # ============================================
    # Redis Cache Cleanup
    # ============================================
    async def cleanup_redis_cache(self, pattern: str = "*") -> int:
        """Delete keys matching pattern from Redis. Returns count deleted."""
        import redis.asyncio as redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        client = await redis.from_url(redis_url, decode_responses=True)
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
        return len(keys)

    # ============================================
    # User Organizations
    # ============================================
    async def get_user_orgs(self, user_id: str) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT o.*, m.role as user_role 
                FROM org_members m
                JOIN organizations o ON m.org_id = o.org_id
                WHERE m.user_id = $1
            """, user_id)
            return [dict(row) for row in rows]

    # ============================================
    # Recognition Queries
    # ============================================
    async def get_recognitions_since(self, org_id: str, since: datetime) -> List[Dict]:
        """Get recognition events for an organization since a datetime"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM recognition_events 
                WHERE org_id = $1 AND timestamp >= $2
                ORDER BY timestamp DESC
            """, org_id, since)
            return [dict(row) for row in rows]

    async def get_recent_recognitions(self, org_id: str, hours: int = 24) -> List[Dict]:
        """Get recent recognition events within last N hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return await self.get_recognitions_since(org_id, cutoff)

    async def get_unscored_recognitions(self, org_id: str, limit: int = 1000) -> List[Dict]:
        """Get recent recognitions that haven't been risk-scored yet"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM recognition_events
                WHERE org_id = $1 AND risk_score IS NULL
                ORDER BY timestamp DESC
                LIMIT $2
            """, org_id, limit)
            return [dict(row) for row in rows]

    async def update_risk_score(self, event_id: str, risk: float) -> bool:
        """Update risk_score for a recognition event"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE recognition_events SET risk_score = $1 WHERE event_id = $2",
                risk, event_id
            )
            return result == "UPDATE 1"

    # ============================================
    # Bias Reports
    # ============================================
    async def store_bias_report(self, org_id: str, report: Dict) -> str:
        """Store a bias/fairness audit report"""
        report_id = str(uuid.uuid4())
        report_date = datetime.utcnow().date()
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO bias_reports (report_id, org_id, report_date, metrics)
                VALUES ($1, $2, $3, $4)
            """, report_id, org_id, report_date, json.dumps(report))
        return report_id

    # ============================================
    # OTA & Edge Devices
    # ============================================
    async def create_ota_job(self, device_id: str, model_version: str) -> str:
        """Create an OTA update job for an edge device"""
        update_id = str(uuid.uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO ota_updates (update_id, device_id, model_version, status)
                VALUES ($1, $2, $3, 'pending')
            """, update_id, device_id, model_version)
        return update_id

    async def get_active_edge_devices(self) -> List[Dict]:
        """Get all active/online edge devices"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM edge_devices WHERE status = 'active'")
            return [dict(row) for row in rows]


# Global instance
_db_client = None


async def get_db():
    global _db_client
    if _db_client is None:
        _db_client = DBClient()
        await _db_client.init_db()
    return _db_client


async def init_db():
    """
    Initialize the database connection pool.
    This function is called at application startup.
    """
    await get_db()

