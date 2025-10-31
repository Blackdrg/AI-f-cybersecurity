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
from datetime import datetime, timedelta
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
    def __init__(self):
        self.pool = None
        self.kms_client = self._init_kms()
        self.encryption_key = self._load_encryption_key()

    async def init_db(self):
        if ASYNCPG_AVAILABLE:
            self.pool = await asyncpg.create_pool(
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password'),
                database=os.getenv('DB_NAME', 'face_recognition'),
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5432))
            )
            await self._create_tables()
        else:
            # Fallback: in-memory storage for testing
            self.pool = None
            self._in_memory_db = {
                'persons': {},
                'embeddings': {},
                'consent_logs': {},
                'audit_log': [],
                'feedback': {},
                'model_versions': {},
                'federated_updates': {},
                'edge_devices': {},
                'consents': {},
                'enrichment_results': {},
                'audit_logs': [],
                'users': {}  # Added users table for in-memory
            }

    async def _create_tables(self):
        async with self.pool.acquire() as conn:
            # Enable pgvector
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # Persons table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS persons (
                    person_id UUID PRIMARY KEY,
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
                    gait_embedding VECTOR(128),  -- Gait embedding (optional)
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

            # Audit log (append-only)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    action TEXT,
                    person_id UUID,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    details JSONB
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

            # Model versions for OTA updates
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    version_id UUID PRIMARY KEY,
                    model_data BYTEA,
                    created_at TIMESTAMP DEFAULT NOW(),
                    description TEXT
                );
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

            # Users table for SaaS
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id UUID PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    subscription_tier TEXT NOT NULL,
                    created_at TEXT NOT NULL
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
        # Use KMS for key management
        if self.kms_client:
            try:
                key_id = os.getenv('KMS_KEY_ID', 'alias/face-recognition-key')
                response = self.kms_client.generate_data_key(
                    KeyId=key_id, KeySpec='AES_256')
                return response['Plaintext']
            except Exception:
                # Fallback if KMS fails
                pass
        # Fallback for POC - generate a proper Fernet key
        import base64
        key = os.getenv('ENCRYPTION_KEY',
                        'your-32-byte-secret-key-here123456789012')  # 32 bytes
        # Ensure it's exactly 32 bytes
        key_bytes = key.encode()[:32].ljust(32, b'\0')
        # Fernet requires base64-encoded key
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

    async def execute(self, query: str, params: tuple = None):
        if self.pool is None:
            # In-memory implementation - basic support for users table
            if 'INSERT INTO users' in query:
                user_id = params[0]
                email = params[1]
                name = params[2]
                subscription_tier = params[3]
                created_at = params[4]
                if 'users' not in self._in_memory_db:
                    self._in_memory_db['users'] = {}
                self._in_memory_db['users'][user_id] = {
                    'user_id': user_id,
                    'email': email,
                    'name': name,
                    'subscription_tier': subscription_tier,
                    'created_at': created_at
                }
            elif 'UPDATE users' in query:
                email = params[0]
                name = params[1]
                subscription_tier = params[2]
                user_id = params[3]
                if user_id in self._in_memory_db.get('users', {}):
                    self._in_memory_db['users'][user_id].update({
                        'email': email,
                        'name': name,
                        'subscription_tier': subscription_tier
                    })
            elif 'DELETE FROM users' in query:
                user_id = params[0]
                if 'users' in self._in_memory_db and user_id in self._in_memory_db['users']:
                    del self._in_memory_db['users'][user_id]
            # For other queries, do nothing
            return None
        else:
            async with self.pool.acquire() as conn:
                if params:
                    await conn.execute(query, *params)
                else:
                    await conn.execute(query)

    async def fetch_one(self, query: str, params: tuple = None):
        if self.pool is None:
            # In-memory implementation
            if 'SELECT * FROM users WHERE user_id = ?' in query:
                user_id = params[0]
                return self._in_memory_db.get('users', {}).get(user_id)
            return None
        else:
            async with self.pool.acquire() as conn:
                if params:
                    return await conn.fetchrow(query, *params)
                else:
                    return await conn.fetchrow(query)

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

                # Insert embeddings (encrypted)
                for i, emb in enumerate(embeddings):
                    emb_id = str(uuid.uuid4())
                    encrypted_emb = self._encrypt_embedding(emb)
                    voice_emb = voice_embeddings[i] if voice_embeddings and i < len(
                        voice_embeddings) else None
                    encrypted_voice = self._encrypt_embedding(
                        voice_emb) if voice_emb is not None else None
                    encrypted_gait = self._encrypt_embedding(
                        gait_embedding) if gait_embedding is not None else None

                    await conn.execute("""
                        INSERT INTO embeddings (embedding_id, person_id, embedding, voice_embedding, gait_embedding, camera_id)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, emb_id, person_id, encrypted_emb, encrypted_voice, encrypted_gait, camera_id)

                # Insert consent log
                await conn.execute("""
                    INSERT INTO consent_logs (consent_record_id, person_id, client_id, consent_text_version, captured_ip, signed_token)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, consent_record['consent_record_id'], person_id, consent_record.get('client_id'), consent_record.get('consent_text_version'), consent_record.get('captured_ip'), consent_record.get('signed_token'))

                # Audit log
                await conn.execute("""
                    INSERT INTO audit_log (action, person_id, details)
                    VALUES ('enroll', $1, $2)
                """, person_id, {'num_embeddings': len(embeddings), 'has_voice': voice_embeddings is not None, 'has_gait': gait_embedding is not None})

        return person_id

    async def recognize_faces(self, query_embedding: np.ndarray, top_k: int = 1, threshold: float = 0.4, camera_id: str = None, voice_embedding: np.ndarray = None, gait_embedding: np.ndarray = None) -> List[Dict[str, Any]]:
        if self.pool is None:
            # In-memory implementation
            matches = []
            for emb_id, emb_data in self._in_memory_db['embeddings'].items():
                # Filter by camera_id if specified
                if camera_id and emb_data.get('camera_id') != camera_id:
                    continue

                # Decrypt and compute face distance
                face_emb = self._decrypt_embedding(emb_data['embedding'])
                face_distance = 1 - np.dot(query_embedding, face_emb) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(face_emb))
                if face_distance > threshold:
                    continue

                person_id = emb_data['person_id']
                combined_score = 1 - face_distance  # Start with face score

                # Add voice score if available
                if voice_embedding is not None and emb_data.get('voice_embedding') is not None:
                    voice_emb = self._decrypt_embedding(
                        emb_data['voice_embedding'])
                    voice_distance = 1 - np.dot(voice_embedding, voice_emb) / (
                        np.linalg.norm(voice_embedding) * np.linalg.norm(voice_emb))
                    if voice_distance <= threshold:
                        combined_score += (1 - voice_distance) * 0.3

                # Add gait score if available
                if gait_embedding is not None and emb_data.get('gait_embedding') is not None:
                    gait_emb = self._decrypt_embedding(
                        emb_data['gait_embedding'])
                    gait_distance = 1 - np.dot(gait_embedding, gait_emb) / (
                        np.linalg.norm(gait_embedding) * np.linalg.norm(gait_emb))
                    if gait_distance <= threshold:
                        combined_score += (1 - gait_distance) * 0.2

                if combined_score >= (1 - threshold):  # Adjusted threshold
                    person = self._in_memory_db['persons'].get(person_id)
                    if person:
                        matches.append({
                            'person_id': person_id,
                            'name': person['name'],
                            'age': person.get('age'),
                            'gender': person.get('gender'),
                            'distance': 1 - combined_score,  # Convert back to distance
                            'score': combined_score
                        })

            # Sort by combined score and limit to top_k
            matches.sort(key=lambda x: x['score'], reverse=True)
            return matches[:top_k]

        async with self.pool.acquire() as conn:
            # Multi-modal fusion: combine face, voice, gait scores
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
                        # Weight
                        combined_score += (1 - voice_row['distance']) * 0.3

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
                # Audit log
                await conn.execute("""
                    INSERT INTO audit_log (action, person_id, details)
                    VALUES ('delete', $1, $2)
                """, person_id, {'deleted': True})

        return True

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


async def init_db():
    db = DBClient()
    await db.init_db()
    return db

# Global instance
db_client = None


async def get_db():
    global db_client
    if db_client is None:
        db_client = DBClient()
        await db_client.init_db()
    return db_client
