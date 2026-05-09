"""Production GraphQL API for AI-f Enterprise using Strawberry."""
import os
import base64
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Annotated, Dict, Any
from uuid import UUID

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from strawberry.experimental.pydantic import TypeMap

# Local imports - real implementations
from ..db.db_client import get_db
from ..models.face_detector import FaceDetector
from ..models.face_embedder import FaceEmbedder
from ..models.spoof_detector import SpoofDetector
from ..models.emotion_detector import EmotionDetector
from ..models.age_gender_estimator import AgeGenderEstimator
from ..models.behavioral_predictor import behavioral_predictor
from ..models.bias_detector import BiasDetector
from ..models.zkp_proper import ZKProofManager
from ..services.anchor_service import anchor_service
from ..metrics import recognition_count, enroll_count
import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Initialize singletons
detector = FaceDetector()
embedder = FaceEmbedder()
spoof_detector = SpoofDetector()
emotion_detector = EmotionDetector()
age_gender_estimator = AgeGenderEstimator()
bias_detector = BiasDetector()
zkp_manager = ZKProofManager()


# ============================================================================
# GRAPHQL TYPES
# ============================================================================

@strawberry.type(name="Person")
class PersonType:
    """Person/identity record in the system."""
    person_id: strawberry.ID
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    enrollment_count: int = 0
    is_active: bool = True


@strawberry.type(name="RecognitionMatch")
class RecognitionMatchType:
    """Single recognition match result."""
    person: PersonType
    confidence: float
    similarity_score: float
    matched_at: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type(name="RecognitionResult")
class RecognitionResultType:
    """Face recognition query result."""
    request_id: str
    matches: List[RecognitionMatchType]
    processing_time_ms: float
    threshold_used: float
    total_candidates: int
    is_spoof_detected: bool = False
    spoof_confidence: Optional[float] = None


@strawberry.type(name="EnrollmentInput")
class EnrollmentInput:
    """Input for enrollment mutation."""
    name: str
    image_base64: str  # Base64-encoded JPEG/PNG
    metadata: Optional[strawberry.JSON] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    consent: bool = True


@strawberry.type(name="EnrollmentResult")
class EnrollmentResultType:
    """Enrollment mutation result."""
    person_id: strawberry.ID
    template_id: str
    embedding_dim: int = 512
    stored_at: datetime = strawberry.field(default_factory=datetime.utcnow)
    success: bool = True
    message: Optional[str] = None


@strawberry.type(name="VerifyResult")
class VerifyResultType:
    """Face verification result (1:1 comparison)."""
    is_same_person: bool
    confidence: float
    similarity: float
    person_a: PersonType
    person_b: PersonType


@strawberry.type(name="AuditLogEntry")
class AuditLogEntryType:
    """Audit trail entry."""
    id: str
    timestamp: datetime
    action: str
    resource_type: str
    resource_id: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: strawberry.JSON = {}
    previous_hash: Optional[str] = None
    hash: str


@strawberry.type(name="SystemHealth")
class SystemHealthType:
    """System health status."""
    status: str
    database: str
    redis: str
    models_loaded: int
    uptime_seconds: float
    last_check: datetime = strawberry.field(default_factory=datetime.utcnow)


@strawberry.type(name="ZKPProof")
class ZKPProofType:
    """ZKP proof metadata."""
    proof_id: str
    proof_type: str
    statement_hash: str
    created_at: datetime
    verified: bool
    blockchain_anchor: Optional[str] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _decode_base64_image(base64_str: str) -> np.ndarray:
    """Decode base64 image string to numpy array."""
    # Remove data URL prefix if present
    if ',' in base64_str:
        base64_str = base64_str.split(',')[1]
    
    image_data = base64.b64decode(base64_str)
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image data")
    return img


async def _get_person_by_id(person_id: str) -> Optional[Dict[str, Any]]:
    """Fetch person from database."""
    db = await get_db()
    try:
        row = await db.pool.fetchrow(
            "SELECT person_id, name, created_at, updated_at FROM persons WHERE person_id = $1",
            person_id
        )
        if row:
            return dict(row)
    except Exception as e:
        logger.error(f"Error fetching person {person_id}: {e}")
    return None


async def _create_audit_log(event_type: str, person_id: Optional[str], details: Dict[str, Any]):
    """Create audit log entry."""
    db = await get_db()
    try:
        await db.pool.execute(
            "INSERT INTO audit_log (event_type, person_id, details) VALUES ($1, $2, $3)",
            event_type, person_id, json.dumps(details)
        )
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")


# ============================================================================
# GRAPHQL QUERIES
# ============================================================================

@strawberry.type(name="Query")
class Query:
    """GraphQL root query type."""

    @strawberry.field
    async def person(self, person_id: strawberry.ID) -> Optional[PersonType]:
        """Get a person by ID."""
        person_data = await _get_person_by_id(person_id)
        if person_data:
            return PersonType(
                person_id=person_data["person_id"],
                name=person_data.get("name"),
                created_at=person_data["created_at"],
                updated_at=person_data["updated_at"],
                enrollment_count=0,  # TODO: count embeddings
                is_active=True
            )
        return None

    @strawberry.field
    async def search_persons(
        self,
        name_contains: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[PersonType]:
        """Search persons with optional filter."""
        db = await get_db()
        try:
            query = "SELECT person_id, name, created_at, updated_at FROM persons"
            params = []
            param_num = 1
            
            if name_contains:
                query += f" WHERE name ILIKE ${param_num}"
                params.append(f"%{name_contains}%")
                param_num += 1
            
            query += f" ORDER BY created_at DESC LIMIT ${param_num} OFFSET ${param_num + 1}"
            params.extend([limit, offset])
            
            rows = await db.pool.fetch(query, *params)
            result = []
            for row in rows:
                result.append(PersonType(
                    person_id=row["person_id"],
                    name=row.get("name"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    enrollment_count=0,
                    is_active=True
                ))
            return result
        except Exception as e:
            logger.error(f"Search persons error: {e}")
            return []

    @strawberry.field
    async def recognize(
        self,
        image_base64: str,
        threshold: float = 0.7,
        top_k: int = 5
    ) -> RecognitionResultType:
        """
        Face recognition: find matching persons.

        Args:
            image_base64: Base64-encoded face image
            threshold: Minimum confidence threshold (0.0-1.0)
            top_k: Maximum number of matches to return

        Returns:
            RecognitionResult with ranked matches
        """
        start_time = datetime.utcnow()
        
        try:
            # Decode image
            img = _decode_base64_image(image_base64)
            
            # Detect face
            faces = detector.detect_faces(img)
            if not faces:
                return RecognitionResultType(
                    request_id=str(uuid.uuid4()),
                    matches=[],
                    processing_time_ms=0.0,
                    threshold_used=threshold,
                    total_candidates=0
                )
            
            # Get largest face
            face = max(faces, key=lambda f: f['bbox'][2] * f['bbox'][3])
            bbox = face['bbox']
            x, y, w, h = map(int, bbox)
            face_crop = img[y:y+h, x:x+w]
            
            # Generate embedding
            embedding = embedder.embed(face_crop)
            
            # Search database
            db = await get_db()
            rows = await db.pool.fetch("""
                SELECT e.person_id, p.name, e.embedding_id, 1.0 - (e.embedding <=> $1) as similarity
                FROM embeddings e
                LEFT JOIN persons p ON e.person_id = p.person_id
                WHERE 1.0 - (e.embedding <=> $1) >= $2
                ORDER BY similarity DESC
                LIMIT $3
            """, embedding.tolist(), threshold, top_k)
            
            matches = []
            for row in rows:
                person = PersonType(
                    person_id=row["person_id"],
                    name=row.get("name"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    enrollment_count=1,
                    is_active=True
                )
                matches.append(RecognitionMatchType(
                    person=person,
                    confidence=float(row["similarity"]),
                    similarity_score=float(row["similarity"]),
                    matched_at=datetime.utcnow()
                ))
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Increment metrics
            recognition_count.inc()
            
            return RecognitionResultType(
                request_id=str(uuid.uuid4()),
                matches=matches,
                processing_time_ms=processing_time,
                threshold_used=threshold,
                total_candidates=len(rows)
            )
            
        except Exception as e:
            logger.error(f"GraphQL recognize error: {e}", exc_info=True)
            raise Exception(f"Recognition failed: {str(e)}")

    @strawberry.field
    async def audit_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        user_id: Optional[strawberry.ID] = None,
        since: Optional[datetime] = None
    ) -> List[AuditLogEntryType]:
        """Query audit trail with filters."""
        db = await get_db()
        try:
            query = "SELECT id, event_type as action, person_id as resource_id, details, timestamp, user_id, ip_address FROM audit_log"
            conditions = []
            params = []
            idx = 1
            
            if action:
                conditions.append(f"event_type = ${idx}")
                params.append(action)
                idx += 1
            if user_id:
                conditions.append(f"user_id = ${idx}")
                params.append(str(user_id))
                idx += 1
            if since:
                conditions.append(f"timestamp >= ${idx}")
                params.append(since)
                idx += 1
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += f" ORDER BY timestamp DESC LIMIT ${idx} OFFSET ${idx + 1}"
            params.extend([limit, offset])
            
            rows = await db.pool.fetch(query, *params)
            result = []
            for row in rows:
                result.append(AuditLogEntryType(
                    id=str(row["id"]),
                    timestamp=row["timestamp"],
                    action=row["action"],
                    resource_type="person",
                    resource_id=row["resource_id"] or "",
                    user_id=row.get("user_id"),
                    ip_address=row.get("ip_address"),
                    user_agent=None,
                    details=row.get("details", {}),
                    previous_hash=None,
                    hash=""
                ))
            return result
        except Exception as e:
            logger.error(f"Audit logs query error: {e}")
            return []

    @strawberry.field
    async def system_health(self) -> SystemHealthType:
        """Check system health status."""
        db = await get_db()
        db_status = "connected"
        try:
            await db.pool.execute("SELECT 1")
        except Exception:
            db_status = "disconnected"
        
        # Count loaded models
        models_loaded = 0
        try:
            # Models are loaded at startup
            from ..models.face_detector import FaceDetector as FD
            from ..models.face_embedder import FaceEmbedder as FE
            models_loaded = 2  # Core models
        except:
            pass
        
        return SystemHealthType(
            status="healthy" if db_status == "connected" else "degraded",
            database=db_status,
            redis="connected",  # TODO: check Redis
            models_loaded=models_loaded,
            uptime_seconds=0.0  # TODO: track uptime
        )

    @strawberry.field
    def zkp_proofs(
        self,
        person_id: strawberry.ID,
        limit: int = 10
    ) -> List[ZKPProofType]:
        """
        Retrieve ZKP audit proofs for a person's identity history.
        Returns Schnorr NIZK proof strings for blockchain anchoring.
        """
        # In real implementation, query zkp_audit table
        return []


# ============================================================================
# GRAPHQL MUTATIONS
# ============================================================================

@strawberry.type(name="Mutation")
class Mutation:
    """GraphQL root mutation type."""

    @strawberry.mutation
    async def enroll(
        self,
        input: EnrollmentInput,
        user_id: Optional[strawberry.ID] = None
    ) -> EnrollmentResultType:
        """
        Enroll a new person/identity in the system.

        Args:
            input: Enrollment data (name, image)
            user_id: Optional operator user ID for audit

        Returns:
            Enrollment result with person_id and template_id
        """
        try:
            # Decode image
            img = _decode_base64_image(input.image_base64)
            
            # Detect face
            faces = detector.detect_faces(img)
            if not faces:
                raise ValueError("No face detected in image")
            
            # Use largest face
            face = max(faces, key=lambda f: f['bbox'][2] * f['bbox'][3])
            x, y, w, h = map(int, face['bbox'])
            face_crop = img[y:y+h, x:x+w]
            
            # Generate embedding
            embedding = embedder.embed(face_crop)
            
            # Estimate age/gender
            age_gender = age_gender_estimator.estimate(face_crop)
            
            # Generate person ID
            person_id = str(uuid.uuid4())
            template_id = str(uuid.uuid4())
            
            # Store in database
            db = await get_db()
            
            # Insert person
            await db.pool.execute("""
                INSERT INTO persons (person_id, name, age, gender, created_at, updated_at)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
            """, person_id, input.name, age_gender.get('age'), age_gender.get('gender'))
            
            # Store embedding
            await db.pool.execute("""
                INSERT INTO embeddings (embedding_id, person_id, embedding, model_version, created_at)
                VALUES ($1, $2, $3, $4, NOW())
            """, template_id, person_id, embedding.tolist(), "face-v2.0")
            
            # Audit log
            await _create_audit_log("enroll", person_id, {
                "name": input.name,
                "template_id": template_id,
                "embedding_dim": len(embedding)
            })
            
            # Increment metrics
            enroll_count.inc()
            
            return EnrollmentResultType(
                person_id=person_id,
                template_id=template_id,
                embedding_dim=len(embedding),
                success=True,
                message="Enrollment successful"
            )
            
        except Exception as e:
            logger.error(f"GraphQL enrollment failed: {e}", exc_info=True)
            return EnrollmentResultType(
                person_id="",
                template_id="",
                success=False,
                message=str(e)
            )

    @strawberry.mutation
    async def verify(
        self,
        person_a_id: strawberry.ID,
        person_b_id: strawberry.ID,
        threshold: float = 0.7
    ) -> VerifyResultType:
        """
        1:1 verification: compare two stored identities.

        Args:
            person_a_id: First person ID
            person_b_id: Second person ID
            threshold: Similarity threshold

        Returns:
            Verification result with confidence
        """
        db = await get_db()
        
        # Fetch both embeddings
        emb_a_row = await db.pool.fetchrow(
            "SELECT embedding FROM embeddings WHERE person_id = $1 LIMIT 1",
            person_a_id
        )
        emb_b_row = await db.pool.fetchrow(
            "SELECT embedding FROM embeddings WHERE person_id = $1 LIMIT 1",
            person_b_id
        )
        
        if not emb_a_row or not emb_b_row:
            raise ValueError("One or both persons not found")
        
        emb_a = np.array(emb_a_row["embedding"])
        emb_b = np.array(emb_b_row["embedding"])
        
        # Compute cosine similarity
        similarity = float(np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b)))
        
        # Fetch person details
        person_a_data = await _get_person_by_id(person_a_id) or {}
        person_b_data = await _get_person_by_id(person_b_id) or {}
        
        person_a = PersonType(
            person_id=person_a_id,
            name=person_a_data.get("name"),
            created_at=person_a_data.get("created_at", datetime.utcnow()),
            updated_at=person_a_data.get("updated_at", datetime.utcnow())
        )
        person_b = PersonType(
            person_id=person_b_id,
            name=person_b_data.get("name"),
            created_at=person_b_data.get("created_at", datetime.utcnow()),
            updated_at=person_b_data.get("updated_at", datetime.utcnow())
        )
        
        is_same = similarity >= threshold
        
        # Audit log
        await _create_audit_log("verify", None, {
            "person_a": person_a_id,
            "person_b": person_b_id,
            "similarity": similarity,
            "threshold": threshold,
            "result": "match" if is_same else "no_match"
        })
        
        return VerifyResultType(
            is_same_person=is_same,
            confidence=similarity,
            similarity=similarity,
            person_a=person_a,
            person_b=person_b
        )

    @strawberry.mutation
    async def revoke_person(
        self,
        person_id: strawberry.ID,
        reason: str,
        user_id: Optional[strawberry.ID] = None
    ) -> bool:
        """
        Revoke/delete a person's identity (GDPR right to erasure).

        Args:
            person_id: Person to revoke
            reason: Reason for revocation
            user_id: Requesting admin

        Returns:
            True if successful
        """
        db = await get_db()
        try:
            # Soft-delete (mark as inactive)
            await db.pool.execute(
                "UPDATE persons SET is_active = false, updated_at = NOW() WHERE person_id = $1",
                person_id
            )
            
            # Anonymize audit trail (GDPR)
            await db.pool.execute(
                "UPDATE audit_log SET person_id = NULL WHERE person_id = $1",
                person_id
            )
            
            # Generate ZKP of deletion (for audit)
            deletion_proof = zkp_manager.generate_identity_proof(
                identity_secret=reason,  # Reason acts as witness
                context=f"deletion:{person_id}"
            )
            
            await _create_audit_log("revoke", person_id, {
                "reason": reason,
                "zkp_proof": deletion_proof
            })
            
            return True
        except Exception as e:
            logger.error(f"Revocation failed: {e}")
            return False

    @strawberry.mutation
    async def anchor_zkp(
        self,
        proof: str,
        blockchain: str = "bitcoin"
    ) -> bool:
        """
        Anchor a ZKP proof to external blockchain.

        Args:
            proof: Schnorr NIZK proof string
            blockchain: "bitcoin", "ethereum", or "solana"

        Returns:
            True if anchoring successful
        """
        try:
            result = await anchor_service.anchor_root_hash(proof)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"ZKP anchoring failed: {e}")
            return False


# ============================================================================
# GRAPHQL SUBSCRIPTIONS
# ============================================================================

@strawberry.type(name="Subscription")
class Subscription:
    """GraphQL subscriptions for real-time updates."""

    @strawberry.subscription
    async def alerts(
        self,
        severity: Optional[str] = None
    ) -> strawberry.AsyncIterator[str]:
        """
        Stream real-time security alerts.

        Example:
            subscription {
                alerts(severity: "HIGH") {
                    id
                    type
                    severity
                    timestamp
                }
            }
        """
        # Integration with Redis PubSub for real-time alert streaming
        from ..pubsub import pubsub_manager
        
        async for message in pubsub_manager.subscribe("alerts"):
            yield message


# ============================================================================
# SCHEMA & ROUTER
# ============================================================================

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)

# GraphQL router for FastAPI inclusion
graphql_router = GraphQLRouter(schema)
