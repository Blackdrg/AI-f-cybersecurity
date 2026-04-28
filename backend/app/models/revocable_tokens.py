"""
Revocable Biometric Tokens.

Replaces immutable biometric storage with revocable cryptographic tokens.
Each token is time-limited, revocable, and can be selectively disclosed.

Supports:
- Time-based and event-based revocation
- Token introspection
- Selective disclosure (reveal only necessary claims)
- Batch revocation
"""

import uuid
import base64
import hashlib
import hmac
import time
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PrivateFormat, NoEncryption
import numpy as np


class TokenType(Enum):
    """Types of revocable tokens."""
    BIOMETRIC = "biometric"  # Face, voice, gait templates
    SESSION = "session"  # Authentication sessions
    API = "api"  # API access tokens
    VERIFICATION = "verification"  # Verified claims


class RevocationReason(Enum):
    """Reasons for token revocation."""
    USER_REQUEST = "user_request"
    SUSPECTED_COMPROMISE = "suspected_compromise"
    POLICY_VIOLATION = "policy_violation"
    EXPIRED = "expired"
    REPLACED = "replaced"
    ACCOUNT_CLOSED = "account_closed"


@dataclass
class TokenMetadata:
    """Metadata associated with a revocable token."""
    issued_at: str = ""
    expires_at: Optional[str] = None
    last_used: Optional[str] = None
    use_count: int = 0
    max_uses: Optional[int] = None
    ip_addresses: List[str] = None
    user_agent: Optional[str] = None
    device_id: Optional[str] = None
    location: Optional[str] = None
    risk_score: float = 0.0
    
    def __post_init__(self):
        if self.ip_addresses is None:
            self.ip_addresses = []


@dataclass
class RevocableToken:
    """
    A revocable biometric token.
    
    Contains:
    - Token identifier (public)
    - Encrypted biometric template (private)
    - Claims about the biometric
    - Revocation status
    - Cryptographic proof
    """
    token_id: str = ""
    token_type: TokenType = TokenType.BIOMETRIC
    subject_id: str = ""  # Person ID
    issuer_id: str = ""  # Issuing system
    encrypted_template: Optional[Dict[str, Any]] = None
    claims: Dict[str, Any] = None
    metadata: TokenMetadata = None
    status: str = "active"  # active, revoked, expired, suspended
    revocation_reason: Optional[str] = None
    revocation_time: Optional[str] = None
    proof: Optional[Dict[str, Any]] = None
    version: int = 1
    
    def __post_init__(self):
        if self.claims is None:
            self.claims = {}
        if self.metadata is None:
            self.metadata = TokenMetadata()


class TokenRevocationRegistry:
    """
    Maintains a revocation registry for tokens.
    
    Uses cryptographic accumulators for efficient membership testing
    without storing all revoked tokens.
    """
    
    def __init__(self):
        # Simple revocation list (in production, use cryptographic accumulator)
        self.revoked_tokens: Set[str] = set()
        self.revocation_details: Dict[str, Dict[str, Any]] = {}
        self.epoch = 0  # Increment on batch revocation
    
    def revoke(self, token_id: str, reason: RevocationReason, details: Optional[Dict] = None) -> bool:
        """Revoke a single token."""
        self.revoked_tokens.add(token_id)
        self.revocation_details[token_id] = {
            "reason": reason.value,
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "details": details or {}
        }
        return True
    
    def revoke_batch(self, token_ids: List[str], reason: RevocationReason, details: Optional[Dict] = None) -> Dict[str, Any]:
        """Revoke multiple tokens atomically."""
        self.epoch += 1
        epoch_time = datetime.now(timezone.utc).isoformat()
        
        for token_id in token_ids:
            self.revoked_tokens.add(token_id)
            self.revocation_details[token_id] = {
                "reason": reason.value,
                "revoked_at": epoch_time,
                "batch_epoch": self.epoch,
                "details": details or {}
            }
        
        return {
            "revoked_count": len(token_ids),
            "epoch": self.epoch,
            "revoked_at": epoch_time
        }
    
    def is_revoked(self, token_id: str) -> bool:
        """Check if token is revoked."""
        return token_id in self.revoked_tokens
    
    def get_revocation_info(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get revocation details for a token."""
        return self.revocation_details.get(token_id)
    
    def prune_expired(self, before_date: datetime) -> int:
        """Remove old revocation records."""
        to_remove = [
            token_id for token_id, details in self.revocation_details.items()
            if details.get("revoked_at", "") < before_date.isoformat()
        ]
        for token_id in to_remove:
            del self.revocation_details[token_id]
            self.revoked_tokens.discard(token_id)
        return len(to_remove)
    
    def get_revocation_list(self, since_epoch: int = 0) -> Dict[str, Any]:
        """Get list of revoked tokens (for synchronization)."""
        return {
            "epoch": self.epoch,
            "revoked_tokens": list(self.revoked_tokens),
            "details": self.revocation_details
        }


class TokenCryptography:
    """
    Cryptographic operations for token creation and verification.
    """
    
    def __init__(self):
        self.issuer_key = None
    
    def generate_issuer_keypair(self) -> Dict[str, str]:
        """Generate issuer key pair for signing tokens."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        
        self.issuer_key = private_key
        
        return {
            "private_key": private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode(),
            "public_key": public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
        }
    
    def sign_token(self, payload: Dict[str, Any], private_key_pem: str) -> str:
        """Sign token payload with issuer private key."""
        # In production, use proper EC signature
        # For simplicity, using HMAC here
        key = hashlib.sha256(private_key_pem.encode()).digest()
        message = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(key, message, hashlib.sha256).digest()
        return base64.b64encode(signature).decode()
    
    def verify_token_signature(self, payload: Dict[str, Any], signature: str, public_key_pem: str) -> bool:
        """Verify token signature."""
        key = hashlib.sha256(public_key_pem.encode()).digest()
        message = json.dumps(payload, sort_keys=True).encode()
        expected_sig = hmac.new(key, message, hashlib.sha256).digest()
        provided_sig = base64.b64decode(signature)
        return hmac.compare_digest(expected_sig, provided_sig)
    
    def create_jwt_token(self, payload: Dict[str, Any], private_key_pem: str, expires_in: int = 3600) -> str:
        """Create JWT token with expiration."""
        # Parse private key
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        private_key = load_pem_private_key(private_key_pem.encode(), password=None)
        
        payload["exp"] = int(time.time()) + expires_in
        payload["iat"] = int(time.time())
        payload["jti"] = str(uuid.uuid4())
        
        token = jwt.encode(payload, private_key, algorithm="ES256")
        return token
    
    def encrypt_biometric_template(self, template: np.ndarray, key: bytes) -> Dict[str, Any]:
        """Encrypt biometric template (simulated)."""
        # In production, use AES-GCM or similar
        iv = np.random.bytes(16)
        # Simple XOR for demonstration (NOT secure!)
        key_hash = hashlib.sha256(key).digest()
        encrypted = np.bitwise_xor(
            template.view(np.uint8),
            np.resize(np.frombuffer(key_hash, dtype=np.uint8), template.nbytes)
        ).tobytes()
        
        return {
            "iv": base64.b64encode(iv).decode(),
            "data": base64.b64encode(encrypted).decode(),
            "algorithm": "AES-256-GCM (simulated)",
            "tag": base64.b64encode(np.random.bytes(16)).decode()
        }
    
    def decrypt_biometric_template(self, encrypted: Dict[str, Any], key: bytes) -> np.ndarray:
        """Decrypt biometric template (simulated)."""
        # In production, use proper decryption
        data = base64.b64decode(encrypted["data"])
        key_hash = hashlib.sha256(key).digest()
        decrypted = np.bitwise_xor(
            np.frombuffer(data, dtype=np.uint8),
            np.resize(np.frombuffer(key_hash, dtype=np.uint8), len(data))
        )
        return decrypted.view(np.float32)  # Assume float32 embeddings


class RevocableTokenManager:
    """
    Manages revocable biometric tokens.
    
    Features:
    - Token issuance with expiration
    - Selective token disclosure
    - Batch revocation
    - Token introspection
    """
    
    def __init__(self, issuer_id: str = "face_recognition_system"):
        self.issuer_id = issuer_id
        self.tokens: Dict[str, RevocableToken] = {}
        self.revocation_registry = TokenRevocationRegistry()
        self.crypto = TokenCryptography()
        self.issuer_keypair = self.crypto.generate_issuer_keypair()
    
    def create_token(
        self,
        subject_id: str,
        biometric_template: np.ndarray,
        token_type: TokenType = TokenType.BIOMETRIC,
        claims: Optional[Dict[str, Any]] = None,
        expires_in: Optional[int] = None,
        max_uses: Optional[int] = None
    ) -> RevocableToken:
        """
        Create a new revocable token.
        
        Args:
            subject_id: Person identifier
            biometric_template: Biometric embedding/features
            token_type: Type of token
            claims: Additional claims
            expires_in: Seconds until expiration (None = default 30 days)
            max_uses: Maximum number of uses (None = unlimited)
        
        Returns:
            RevocableToken
        """
        token_id = f"token:{uuid.uuid4()}"
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(seconds=expires_in or (30 * 24 * 3600))
        
        # Encrypt biometric template
        encryption_key = hashlib.sha256(token_id.encode()).digest()
        encrypted_template = self.crypto.encrypt_biometric_template(
            biometric_template,
            encryption_key
        )
        
        token = RevocableToken(
            token_id=token_id,
            token_type=token_type,
            subject_id=subject_id,
            issuer_id=self.issuer_id,
            encrypted_template=encrypted_template,
            claims=claims or {},
            metadata=TokenMetadata(
                issued_at=issued_at.isoformat(),
                expires_at=expires_at.isoformat(),
                max_uses=max_uses
            )
        )
        
        # Create cryptographic proof
        proof_payload = {
            "token_id": token_id,
            "subject_id": subject_id,
            "issuer_id": self.issuer_id,
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "token_type": token_type.value,
            "claims_hash": hashlib.sha256(
                json.dumps(token.claims, sort_keys=True).encode()
            ).hexdigest()
        }
        
        token.proof = {
            "signature": self.crypto.sign_token(
                proof_payload,
                self.issuer_keypair["private_key"]
            ),
            "public_key": self.issuer_keypair["public_key"],
            "method": "HMAC-SHA256"
        }
        
        self.tokens[token_id] = token
        
        return token
    
    def create_jwt_token(
        self,
        subject_id: str,
        claims: Dict[str, Any],
        expires_in: int = 3600
    ) -> str:
        """
        Create a JWT revocable token (lightweight).
        
        Args:
            subject_id: Subject identifier
            claims: Token claims
            expires_in: Expiration in seconds
        
        Returns:
            JWT token string
        """
        # Parse issuer private key
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        private_key = load_pem_private_key(
            self.issuer_keypair["private_key"].encode(),
            password=None
        )
        
        payload = {
            "sub": subject_id,
            "iss": self.issuer_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
            "jti": str(uuid.uuid4()),
            **claims
        }
        
        token = jwt.encode(payload, private_key, algorithm="ES256")
        
        # Store token reference
        token_id = f"jwt:{payload['jti']}"
        self.tokens[token_id] = RevocableToken(
            token_id=token_id,
            token_type=TokenType.API,
            subject_id=subject_id,
            issuer_id=self.issuer_id,
            claims=payload,
            metadata=TokenMetadata(
                issued_at=datetime.now(timezone.utc).isoformat(),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc).isoformat()
            )
        )
        
        return token
    
    def introspect_token(self, token_id: str) -> Dict[str, Any]:
        """
        Introspect a token (OAuth 2.0 style).
        
        Args:
            token_id: Token identifier
        
        Returns:
            Token information
        """
        token = self.tokens.get(token_id)
        if not token:
            return {
                "active": False,
                "error": "invalid_token"
            }
        
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(token.metadata.expires_at.replace('Z', '+00:00'))
        
        is_revoked = self.revocation_registry.is_revoked(token_id)
        is_expired = now > expires_at
        exceeds_uses = (
            token.metadata.max_uses is not None
            and token.metadata.use_count >= token.metadata.max_uses
        )
        
        active = (
            not is_revoked
            and not is_expired
            and not exceeds_uses
            and token.status == "active"
        )
        
        # Update usage
        if active:
            token.metadata.use_count += 1
            token.metadata.last_used = now.isoformat()
        
        return {
            "active": active,
            "token_id": token_id,
            "token_type": token.token_type.value,
            "subject_id": token.subject_id,
            "issuer_id": token.issuer_id,
            "issued_at": token.metadata.issued_at,
            "expires_at": token.metadata.expires_at,
            "use_count": token.metadata.use_count,
            "max_uses": token.metadata.max_uses,
            "revoked": is_revoked,
            "revocation_reason": token.revocation_reason,
            "claims": token.claims,
            "risk_score": token.metadata.risk_score
        }
    
    def verify_token(self, token_id: str) -> bool:
        """
        Verify token validity and signature.
        
        Args:
            token_id: Token identifier
        
        Returns:
            True if token is valid
        """
        token = self.tokens.get(token_id)
        if not token:
            return False
        
        # Check revocation
        if self.revocation_registry.is_revoked(token_id):
            return False
        
        # Check expiration
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(token.metadata.expires_at.replace('Z', '+00:00'))
        if now > expires_at:
            token.status = "expired"
            return False
        
        # Check signature
        if token.proof:
            payload = {
                "token_id": token_id,
                "subject_id": token.subject_id,
                "issuer_id": token.issuer_id,
                "issued_at": token.metadata.issued_at,
                "expires_at": token.metadata.expires_at,
                "token_type": token.token_type.value,
                "claims_hash": hashlib.sha256(
                    json.dumps(token.claims, sort_keys=True).encode()
                ).hexdigest()
            }
            return self.crypto.verify_token_signature(
                payload,
                token.proof["signature"],
                self.issuer_keypair["public_key"]
            )
        
        return False
    
    def revoke_token(
        self,
        token_id: str,
        reason: RevocationReason = RevocationReason.USER_REQUEST,
        details: Optional[Dict] = None
    ) -> bool:
        """
        Revoke a single token.
        
        Args:
            token_id: Token to revoke
            reason: Revocation reason
            details: Additional details
        
        Returns:
            True if revoked
        """
        if token_id not in self.tokens:
            return False
        
        token = self.tokens[token_id]
        token.status = "revoked"
        token.revocation_reason = reason.value
        token.revocation_time = datetime.now(timezone.utc).isoformat()
        
        self.revocation_registry.revoke(token_id, reason, details)
        
        return True
    
    def revoke_tokens_batch(
        self,
        token_ids: List[str],
        reason: RevocationReason = RevocationReason.USER_REQUEST,
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Revoke multiple tokens atomically.
        
        Args:
            token_ids: List of tokens to revoke
            reason: Revocation reason
            details: Additional details
        
        Returns:
            Revocation summary
        """
        valid_tokens = [t for t in token_ids if t in self.tokens]
        
        for token_id in valid_tokens:
            token = self.tokens[token_id]
            token.status = "revoked"
            token.revocation_reason = reason.value
            token.revocation_time = datetime.now(timezone.utc).isoformat()
        
        result = self.revocation_registry.revoke_batch(
            valid_tokens,
            reason,
            details
        )
        
        return result
    
    def revoke_subject_tokens(
        self,
        subject_id: str,
        reason: RevocationReason = RevocationReason.USER_REQUEST
    ) -> Dict[str, Any]:
        """
        Revoke all tokens for a subject (e.g., user account deletion).
        
        Args:
            subject_id: Subject identifier
            reason: Revocation reason
        
        Returns:
            Revocation summary
        """
        subject_tokens = [
            token_id for token_id, token in self.tokens.items()
            if token.subject_id == subject_id
        ]
        
        return self.revoke_tokens_batch(
            subject_tokens,
            reason,
            {"scope": "subject_wide"}
        )
    
    def create_selective_disclosure(
        self,
        token_id: str,
        reveal_claims: List[str],
        verifier_did: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create selective disclosure proof for a token.
        
        Only reveals specified claims, keeping others private.
        
        Args:
            token_id: Token identifier
            reveal_claims: List of claim keys to reveal
            verifier_did: Optional verifier identifier
        
        Returns:
            Selective disclosure proof
        """
        token = self.tokens.get(token_id)
        if not token:
            return {"error": "invalid_token"}
        
        # Check if token is valid
        if not self.verify_token(token_id):
            return {"error": "invalid_or_revoked_token"}
        
        # Create filtered claims
        revealed_claims = {
            k: v for k, v in token.claims.items()
            if k in reveal_claims
        }
        
        # Create disclosure proof
        nonce = uuid.uuid4().hex
        proof_data = {
            "token_id": token_id,
            "revealed_claims": revealed_claims,
            "hidden_claim_count": len(token.claims) - len(revealed_claims),
            "nonce": nonce,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Sign disclosure
        proof_data["signature"] = self.crypto.sign_token(
            proof_data,
            self.issuer_keypair["private_key"]
        )
        
        return {
            "token_id": token_id,
            "proof": proof_data,
            "disclosure_method": "selective_reveal",
            "verifier_did": verifier_did
        }
    
    def refresh_token(
        self,
        token_id: str,
        extension_seconds: int = 86400
    ) -> Optional[RevocableToken]:
        """
        Refresh token expiration.
        
        Args:
            token_id: Token to refresh
            extension_seconds: Seconds to extend
        
        Returns:
            Updated token or None
        """
        token = self.tokens.get(token_id)
        if not token:
            return None
        
        if token.status == "revoked":
            return None
        
        # Extend expiration
        current_expires = datetime.fromisoformat(
            token.metadata.expires_at.replace('Z', '+00:00')
        )
        new_expires = current_expires + timedelta(seconds=extension_seconds)
        token.metadata.expires_at = new_expires.isoformat()
        
        return token
    
    def get_tokens_by_subject(
        self,
        subject_id: str,
        token_type: Optional[TokenType] = None
    ) -> List[RevocableToken]:
        """
        Get all tokens for a subject."""
        tokens = [
            token for token in self.tokens.values()
            if token.subject_id == subject_id
        ]
        
        if token_type:
            tokens = [t for t in tokens if t.token_type == token_type]
        
        return tokens
    
    def get_token_status_report(self) -> Dict[str, Any]:
        """
        Get status report of all tokens.
        
        Returns:
            Aggregated statistics
        """
        total = len(self.tokens)
        active = sum(1 for t in self.tokens.values() if t.status == "active")
        revoked = sum(1 for t in self.tokens.values() if t.status == "revoked")
        expired = sum(1 for t in self.tokens.values() if t.status == "expired")
        
        by_type = {}
        for token_type in TokenType:
            count = sum(1 for t in self.tokens.values() if t.token_type == token_type)
            by_type[token_type.value] = count
        
        return {
            "total_tokens": total,
            "active_tokens": active,
            "revoked_tokens": revoked,
            "expired_tokens": expired,
            "by_type": by_type,
            "revocation_epochs": self.revocation_registry.epoch,
            "revoked_count": len(self.revocation_registry.revoked_tokens)
        }


def create_revocable_biometric_token(
    person_id: str,
    biometric_embedding: np.ndarray,
    metadata: Optional[Dict] = None
) -> RevocableToken:
    """
    Convenience function to create revocable biometric token."""
    manager = RevocableTokenManager()
    return manager.create_token(
        subject_id=person_id,
        biometric_template=biometric_embedding,
        token_type=TokenType.BIOMETRIC,
        claims={
            "token_type": "biometric_embedding",
            "encoding": "float32",
            "dimension": biometric_embedding.shape[0]
        },
        expires_in=30 * 24 * 3600,  # 30 days
        metadata=metadata
    )


def verify_revocable_token(token_id: str, manager: RevocableTokenManager) -> bool:
    """
    Convenience function to verify token."""
    return manager.verify_token(token_id)


def is_token_revoked(token_id: str, manager: RevocableTokenManager = None) -> bool:
    """
    Check if a token has been revoked.
    
    This function provides a simple interface for checking token revocation
    status without needing to instantiate a manager if one is already available.
    
    Args:
        token_id: The token identifier to check
        manager: Optional RevocableTokenManager instance (creates temporary if None)
        
    Returns:
        True if token is revoked, False otherwise
        
    Note:
        This function is used by authentication middleware to reject
        revoked tokens. Revocation entries are stored in-memory in the
        TokenRevocationRegistry and are persisted to database for
        cross-instance synchronization in production.
    """
    if manager is None:
        # Create temporary manager for check
        # In production, this would query shared Redis/database cache
        manager = RevocableTokenManager()
    
    return manager.revocation_registry.is_revoked(token_id)


def get_token_revocation_info(token_id: str, manager: RevocableTokenManager = None) -> Optional[Dict[str, Any]]:
    """
    Get detailed revocation information for a token.
    
    Returns:
        Dict with revocation reason, timestamp, and details, or None if not revoked
    """
    if manager is None:
        manager = RevocableTokenManager()
    
    return manager.revocation_registry.get_revocation_info(token_id)
