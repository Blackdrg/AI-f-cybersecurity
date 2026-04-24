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


class SignatureAuthenticator:
    """
    Ed25519 digital signature-based authentication for embedding ownership.
    
    Note: This provides cryptographic proof of possession of a signing key,
    but is NOT a Zero-Knowledge Proof. The verifier must have the corresponding
    public key to verify signatures.
    """
    def __init__(self):
        # For POC, uses Ed25519 signatures; in production, use hardware-backed keys
        pass

    def sign_embedding(self, embedding: np.ndarray, signing_key: bytes) -> Dict[str, Any]:
        """
        Generate digital signature for an embedding hash.
        """
        if not NACL_AVAILABLE:
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
            'public_key': signing_key_obj.verify_key.encode(),
            'challenge': emb_hash.hex()
        }

    def verify_signature(self, signature_data: Dict[str, Any], embedding: np.ndarray) -> bool:
        """
        Verify a digital signature against an embedding hash.
        """
        if not NACL_AVAILABLE:
            emb_hash = hashlib.sha256(embedding.tobytes()).digest()
            expected = hashlib.sha256(bytes.fromhex(signature_data['public_key']) + emb_hash).hexdigest()
            return signature_data['signature'] == expected and signature_data['challenge'] == emb_hash.hex()

        try:
            emb_hash = hashlib.sha256(embedding.tobytes()).digest()
            verify_key = nacl.signing.VerifyKey(
                signature_data['public_key'], encoder=nacl.encoding.HexEncoder)
            verify_key.verify(signature_data['signature'])
            return signature_data['challenge'] == emb_hash.hex()
        except Exception:
            return False

    def authenticate(self, signature_data: Dict[str, Any], stored_embedding: np.ndarray) -> bool:
        """Authenticate using digital signature."""
        return self.verify_signature(signature_data, stored_embedding)
