try:
    import nacl.signing
    import nacl.encoding
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False
    nacl = None

import hashlib
import numpy as np
from typing import Tuple, Dict, Any


class CryptoAttestation:
    """
    Cryptographic attestation service for embedding ownership verification.

    Uses Ed25519 digital signatures to provide proof of possession.
    Note: This is NOT a Zero-Knowledge Proof system. It provides
    cryptographic assurance that the holder possesses the private key
    corresponding to a registered public key.
    """
    def __init__(self):
        # For POC, uses Ed25519 signatures; production should use hardware-backed keys (HSM, TPM)
        pass

    def sign_embedding(self, embedding: np.ndarray, signing_key: bytes) -> Dict[str, Any]:
        """
        Generate digital signature for an embedding hash.

        Args:
            embedding: The biometric embedding to attest.
            signing_key: Raw private key bytes (32 bytes for Ed25519).

        Returns:
            Dict with 'signature', 'public_key' (hex), 'challenge' (embedding hash hex).
        """
        if not NACL_AVAILABLE:
            # Fallback: SHA256-based HMAC-like construction (not as secure)
            emb_hash = hashlib.sha256(embedding.tobytes()).digest()
            signature = hashlib.sha256(signing_key + emb_hash).hexdigest()
            public_key = hashlib.sha256(signing_key).hexdigest()
            return {
                'signature': signature,
                'public_key': public_key,
                'challenge': emb_hash.hex()
            }

        emb_hash = hashlib.sha256(embedding.tobytes()).digest()
        signing_key_obj = nacl.signing.SigningKey(signing_key)
        signed = signing_key_obj.sign(emb_hash)
        return {
            'signature': signed,
            'public_key': signing_key_obj.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode(),
            'challenge': emb_hash.hex()
        }

    def verify_attestation(self, attestation: Dict[str, Any], embedding: np.ndarray) -> bool:
        """
        Verify a cryptographic attestation against an embedding hash.

        Args:
            attestation: Dict with 'signature', 'public_key' (hex), 'challenge' (hex).
            embedding: The stored embedding to verify.

        Returns:
            True if signature valid and challenge matches.
        """
        if not NACL_AVAILABLE:
            emb_hash = hashlib.sha256(embedding.tobytes()).digest()
            expected = hashlib.sha256(bytes.fromhex(attestation['public_key']) + emb_hash).hexdigest()
            return attestation['signature'] == expected and attestation['challenge'] == emb_hash.hex()

        try:
            emb_hash = hashlib.sha256(embedding.tobytes()).digest()
            verify_key = nacl.signing.VerifyKey(
                attestation['public_key'], encoder=nacl.encoding.HexEncoder)
            verify_key.verify(attestation['signature'])
            return attestation['challenge'] == emb_hash.hex()
        except Exception:
            return False

    def authenticate(self, attestation: Dict[str, Any], stored_embedding: np.ndarray) -> bool:
        """Authenticate using cryptographic attestation."""
        return self.verify_attestation(attestation, stored_embedding)
