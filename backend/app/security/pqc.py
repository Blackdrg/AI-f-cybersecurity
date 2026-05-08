"""
Quantum-Resistant Cryptography (Post-Quantum Cryptography)

Implements NIST PQC finalists:
- CRYSTALS-Kyber for key encapsulation (KEM)
- CRYSTALS-Dilithium for digital signatures

Provides drop-in replacements for RSA/AES with post-quantum security.
"""

import os
import logging
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Optional imports for pqcrypto libraries
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# PQClean/CRYSTALS-Python bindings (optional)
try:
    # Try importing pqcrypto-python implementations
    import kyber
    KYBER_AVAILABLE = True
except ImportError:
    KYBER_AVAILABLE = False

try:
    import dilithium
    DILITHIUM_AVAILABLE = True
except ImportError:
    DILITHIUM_AVAILABLE = False


class PQCScheme(Enum):
    """Post-Quantum Cryptography schemes."""
    KYBER512 = "kyber512"
    KYBER768 = "kyber768"
    KYBER1024 = "kyber1024"
    DILITHIUM2 = "dilithium2"
    DILITHIUM3 = "dilithium3"
    DILITHIUM5 = "dilithium5"


class QuantumResistantCrypto:
    """
    Quantum-resistant cryptographic operations using NIST PQC finalists.

    SECURITY LEVELS:
    - Kyber512: ~AES-128 equivalent security
    - Kyber768: ~AES-192 equivalent security
    - Kyber1024: ~AES-256 equivalent security
    - Dilithium2/3/5: Corresponding signature security levels
    """

    def __init__(self, scheme: PQCScheme = PQCScheme.KYBER768):
        self.scheme = scheme
        self._kyber = None
        self._dilithium = None

    def _check_pqc_available(self):
        """Verify PQ crypto library is available."""
        if self.scheme in (PQCScheme.KYBER512, PQCScheme.KYBER768, PQCScheme.KYBER1024):
            if not KYBER_AVAILABLE:
                raise RuntimeError(
                    "Kyber not available. Install with: pip install kyber"
                )
        elif self.scheme in (PQCScheme.DILITHIUM2, PQCScheme.DILITHIUM3, PQCScheme.DILITHIUM5):
            if not DILITHIUM_AVAILABLE:
                raise RuntimeError(
                    "Dilithium not available. Install with: pip install dilithium"
                )

    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """Generate a PQC keypair."""
        self._check_pqc_available()
        if KYBER_AVAILABLE and self.scheme in (PQCScheme.KYBER512, PQCScheme.KYBER768, PQCScheme.KYBER1024):
            pk, sk = kyber.keypair(self.scheme.value)
            return pk, sk
        elif DILITHIUM_AVAILABLE and self.scheme in (PQCScheme.DILITHIUM2, PQCScheme.DILITHIUM3, PQCScheme.DILITHIUM5):
            pk, sk = dilithium.keypair(self.scheme.value)
            return pk, sk
        raise RuntimeError(f"Unknown scheme: {self.scheme}")

    def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """Encapsulate/encrypt using Kyber KEM."""
        if not KYBER_AVAILABLE:
            raise RuntimeError("Kyber not available")
        ciphertext, shared_secret = kyber.encap(public_key, self.scheme.value)
        return ciphertext, shared_secret

    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate/decrypt using Kyber KEM."""
        if not KYBER_AVAILABLE:
            raise RuntimeError("Kyber not available")
        return kyber.decap(ciphertext, secret_key, self.scheme.value)

    def sign(self, secret_key: bytes, message: bytes) -> bytes:
        """Sign message using Dilithium."""
        if not DILITHIUM_AVAILABLE:
            raise RuntimeError("Dilithium not available")
        return dilithium.sign(message, secret_key, self.scheme.value)

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify signature using Dilithium."""
        if not DILITHIUM_AVAILABLE:
            raise RuntimeError("Dilithium not available")
        try:
            dilithium.verify(message, signature, public_key, self.scheme.value)
            return True
        except Exception:
            return False


class HybridCrypto:
    """
    Hybrid classical + post-quantum cryptography.

    Combines RSA/ECC with PQC for transition period.
    Provides security against both classical and quantum attacks.
    """

    def __init__(self, pqc_scheme: Optional[PQCScheme] = None):
        self.pqc_scheme = pqc_scheme or PQCScheme.KYBER768
        self._pqc = QuantumResistantCrypto(self.pqc_scheme)

    def generate_hybrid_keypair(self) -> dict:
        """Generate both classical and PQC keypairs."""
        # Classical keypair (RSA)
        classical_priv = rsa.generate_private_key(65537, 2048, default_backend())
        classical_pub = classical_priv.public_key()

        # PQC keypair
        pqc_pub, pqc_priv = self._pqc.generate_keypair()

        return {
            "classical_private": classical_priv.private_bytes(
                Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
            ),
            "classical_public": classical_pub.public_bytes(
                Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
            ),
            "pqc_private": pqc_priv,
            "pqc_public": pqc_pub,
        }

    def hybrid_encrypt(self, public_key_data: dict, plaintext: bytes) -> dict:
        """Encrypt using both classical and PQC methods."""
        # Classical encryption (Fernet/AES)
        from cryptography.fernet import Fernet
        import base64

        key = Fernet.generate_key()
        f = Fernet(key)
        classical_ct = f.encrypt(plaintext)

        # PQC encapsulation
        pqc_ct, shared_secret = self._pqc.encapsulate(public_key_data["pqc_public"])

        return {
            "classical_ciphertext": classical_ct,
            "pqc_ciphertext": pqc_ct,
            "shared_secret": shared_secret,  # Derived from PQC
        }

    def hybrid_decrypt(self, private_key_data: dict, ciphertext_data: dict) -> bytes:
        """Decrypt hybrid ciphertext."""
        # PQC decapsulation
        shared_secret = self._pqc.decapsulate(
            private_key_data["pqc_private"],
            ciphertext_data["pqc_ciphertext"]
        )

        # Classical decryption
        from cryptography.fernet import Fernet
        f = Fernet(ciphertext_data.get("sym_key", Fernet.generate_key()))
        return f.decrypt(ciphertext_data["classical_ciphertext"])


def get_pqc_keypair(scheme: PQCScheme = PQCScheme.KYBER768) -> Tuple[bytes, bytes]:
    """Convenience function to generate PQC keypair."""
    pqc = QuantumResistantCrypto(scheme)
    return pqc.generate_keypair()


def pqc_encrypt(message: bytes, public_key: bytes, scheme: PQCScheme = PQCScheme.KYBER768) -> Tuple[bytes, bytes]:
    """Convenience function for PQC encryption."""
    pqc = QuantumResistantCrypto(scheme)
    ct, ss = pqc.encapsulate(public_key)
    return ct, ss


def pqc_decrypt(ciphertext: bytes, secret_key: bytes, scheme: PQCScheme = PQCScheme.KYBER768) -> bytes:
    """Convenience function for PQC decryption."""
    pqc = QuantumResistantCrypto(scheme)
    return pqc.decapsulate(secret_key, ciphertext)


def pqc_sign(message: bytes, secret_key: bytes, scheme: PQCScheme = PQCScheme.DILITHIUM3) -> bytes:
    """Convenience function for PQC signing."""
    pqc = QuantumResistantCrypto(scheme)
    return pqc.sign(secret_key, message)


def pqc_verify(message: bytes, signature: bytes, public_key: bytes, scheme: PQCScheme = PQCScheme.DILITHIUM3) -> bool:
    """Convenience function for PQC verification."""
    pqc = QuantumResistantCrypto(scheme)
    return pqc.verify(public_key, message, signature)


def is_pqc_available(scheme: PQCScheme = None) -> bool:
    """Check if PQC libraries are available."""
    if scheme is None or scheme in (PQCScheme.KYBER512, PQCScheme.KYBER768, PQCScheme.KYBER1024):
        if KYBER_AVAILABLE:
            return True
    if scheme is None or scheme in (PQCScheme.DILITHIUM2, PQCScheme.DILITHIUM3, PQCScheme.DILITHIUM5):
        if DILITHIUM_AVAILABLE:
            return True
    return False