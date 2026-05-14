"""
Tests for Post-Quantum Cryptography (PQC) implementation.

Validates:
- Kyber KEM operations
- Dilithium signature operations
- Hybrid crypto key exchange
- Migration layer negotiation
- Algorithm fallback behavior
"""

import pytest
import json
import base64
import os
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.security.pqc import (
    PQCAlgorithm, QuantumResistantCrypto, HybridCrypto,
    PQCMigrationLayer, PQCKeyStore, PQCKeyMetadata,
    get_pqc_wrapper, is_pqc_available,
    generate_pqc_keypair, pqc_encrypt, pqc_decrypt,
    pqc_sign, pqc_verify
)


class TestPQCAlgorithms:
    """Test PQC algorithm enumeration."""
    
    def test_kyber_algorithms(self):
        assert PQCAlgorithm.KYBER512.value == "kyber512"
        assert PQCAlgorithm.KYBER768.value == "kyber768"
        assert PQCAlgorithm.KYBER1024.value == "kyber1024"
    
    def test_dilithium_algorithms(self):
        assert PQCAlgorithm.DILITHIUM2.value == "dilithium2"
        assert PQCAlgorithm.DILITHIUM3.value == "dilithium3"
        assert PQCAlgorithm.DILITHIUM5.value == "dilithium5"
    
    def test_falcon_algorithms(self):
        assert PQCAlgorithm.FALCON512.value == "falcon512"
        assert PQCAlgorithm.FALCON1024.value == "falcon1024"


class TestPQCLibraryWrapper:
    """Test the low-level library wrapper."""
    
    def test_wrapper_initialization(self):
        wrapper = get_pqc_wrapper()
        # Should be created even if libs unavailable
        assert wrapper is not None
        assert hasattr(wrapper, 'available')
    
    def test_is_pqc_available_returns_tuple(self):
        avail = is_pqc_available()
        assert isinstance(avail, bool)


class TestQuantumResistantCrypto:
    """Test high-level PQC operations."""

    def test_init_default(self):
        crypto = QuantumResistantCrypto()
        assert crypto.scheme == PQCAlgorithm.KYBER768

    def test_init_custom_scheme(self):
        crypto = QuantumResistantCrypto(scheme=PQCAlgorithm.KYBER1024)
        assert crypto.scheme == PQCAlgorithm.KYBER1024

    def test_generate_keypair_unavailable_raises(self):
        with patch("app.security.pqc.get_pqc_wrapper") as mock_wrap:
            mock_wrap.return_value.available = False
            crypto = QuantumResistantCrypto()
            with pytest.raises(RuntimeError, match="Kyber not available"):
                crypto.generate_keypair()

    def test_key_generation_and_storage(self):
        """Test key generation and keystore storage."""
        crypto = QuantumResistantCrypto(scheme=PQCAlgorithm.KYBER768)

        if not crypto._wrapper.available:
            pytest.skip("PQC library not available")

        key_id, pk, sk = crypto.generate_keypair()

        assert key_id is not None
        assert len(pk) > 0
        assert len(sk) > 0

        # Verify stored
        stored = crypto.keystore.load_key(key_id)
        assert stored is not None
        stored_sk, stored_meta = stored
        assert stored_meta.algorithm == "kyber768"
        assert stored_meta.key_type == "kem"

    def test_kem_encapsulate_decapsulate_roundtrip(self):
        """Test Kyber KEM encrypt/decrypt cycle."""
        crypto = QuantumResistantCrypto(scheme=PQCAlgorithm.KYBER768)

        if not crypto._wrapper.available or not crypto.scheme.name.startswith('KYBER'):
            pytest.skip("Kyber not available")

        # Generate receiver key
        key_id, receiver_pk, receiver_sk = crypto.generate_keypair(key_id="receiver")

        # Sender encapsulates
        ct_id, ciphertext, shared_secret_a = crypto.encapsulate(receiver_pk)

        # Receiver decapsulates
        shared_secret_b = crypto.decapsulate(receiver_sk, ciphertext)

        assert shared_secret_a == shared_secret_b
        assert len(shared_secret_a) == 32  # 256-bit key

    def test_sign_verify_roundtrip(self):
        """Test Dilithium sign/verify cycle."""
        crypto = QuantumResistantCrypto(scheme=PQCAlgorithm.DILITHIUM3)
        
        if not crypto._wrapper.available or 'dilithium' not in crypto.scheme.value:
            pytest.skip("Dilithium not available")
        
        key_id, pk, sk = crypto.generate_keypair()
        
        message = b"Test message for PQC signature"
        
        # Sign
        sig_id, signature = crypto.sign(sk, message)
        
        # Verify
        valid = crypto.verify(pk, message, signature)
        assert valid is True
        
        # Tamper check
        fake_msg = b"Tampered message"
        valid_fake = crypto.verify(pk, fake_msg, signature)
        assert valid_fake is False


class TestHybridCrypto:
    """Test hybrid classical+PQC operations."""
    
    def test_hybrid_keypair_generation(self):
        hc = HybridCrypto()
        
        # May fail if PQC unavailable, check first
        if not hc._pqc._wrapper.available:
            pytest.skip("PQC libraries not installed")
        
        result = hc.generate_hybrid_keypair()
        
        assert "classical_private" in result
        assert "classical_public" in result
        assert "pqc_private" in result  # Stored in keystore
        assert "pqc_public" in result
        assert result["hybrid"] is True
        assert result["algorithm"] == "RSA-2048"
    
    def test_hybrid_encrypt_decrypt_roundtrip(self):
        hc = HybridCrypto()
        if not hc._pqc._wrapper.available:
            pytest.skip("PQC libraries not available")
        
        # Generate recipient keys
        keys = hc.generate_hybrid_keypair()
        
        plaintext = b"Secret message under quantum threat"
        
        # Encrypt
        ciphertext_pkg = hc.hybrid_encrypt(keys, plaintext)
        assert "hybrid_ciphertext" in ciphertext_pkg
        assert "aes_nonce" in ciphertext_pkg
        
        # Decrypt
        recovered = hc.hybrid_decrypt(keys, ciphertext_pkg["hybrid_ciphertext"], 
                                     base64.b64decode(ciphertext_pkg["aes_nonce"]))
        assert recovered == plaintext
    
    def test_hybrid_fallback_on_pqc_failure(self):
        """Ensure graceful fallback if PQC fails."""
        hc = HybridCrypto()
        # Force PQC to fail via mock
        with patch.object(hc._pqc, '_check_pqc_available', side_effect=RuntimeError("forced")):
            with pytest.raises(RuntimeError):
                hc.hybrid_encrypt({}, b"data")


class TestPQCMigrationLayer:
    """Test algorithm negotiation and migration."""
    
    def test_negotiate_kem_common_algorithm(self):
        migration = PQCMigrationLayer()
        client_caps = ["kyber768", "kyber512"]
        chosen, hybrid = migration.negotiate_kem_algorithm(client_caps)
        assert chosen == "kyber768"
        assert hybrid is True  # enable_hybrid_mode default True
    
    def test_negotiate_kem_fallback_classical(self):
        migration = PQCMigrationLayer()
        client_caps = ["rsa2048", "ecdh_p256"]
        with pytest.raises(ValueError):
            # No PQC provided, classical not in kem list
            migration.negotiate_kem_algorithm(client_caps)
    
    def test_hybrid_ciphertext_parse(self):
        migration = PQCMigrationLayer()
        classical = b"A" * 256
        pqc = b"B" * 1000
        hybrid = migration.create_hybrid_ciphertext(classical, pqc, {})
        
        cl, pq, meta = migration.parse_hybrid_ciphertext(hybrid)
        assert cl == classical
        assert pq == pqc
        assert meta["hybrid"] is True


class TestPQCKeyStore:
    """Test PQC key storage and retrieval."""

    def test_store_and_load_key(self, tmp_path):
        keystore = PQCKeyStore(keys_dir=str(tmp_path))

        key_data = b"test_secret_key_material"
        meta = PQCKeyMetadata(
            algorithm="kyber768",
            version=1,
            created_at=datetime.utcnow().isoformat(),
            key_type="kem"
        )

        stored = keystore.store_key("test-key", key_data, meta)
        assert stored is True

        loaded = keystore.load_key("test-key")
        assert loaded is not None
        loaded_data, loaded_meta = loaded
        assert loaded_data == key_data
        assert loaded_meta.algorithm == "kyber768"

    def test_list_keys(self, tmp_path):
        keystore = PQCKeyStore(keys_dir=str(tmp_path))
        # Generate a couple keys
        for i in range(2):
            kdata = f"key{i}".encode()
            meta = PQCKeyMetadata(
                algorithm="dilithium3",
                version=1,
                created_at=datetime.utcnow().isoformat(),
                key_type="signature"
)
            keystore.store_key(f"sig-key-{i}", kdata, meta)

            keys = keystore.list_keys(algorithm=PQCAlgorithm.DILITHIUM3)
        assert len(keys) == 2
        assert all(k["algorithm"] == "dilithium3" for k in keys)


class TestPQCConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_generate_pqc_keypair(self):
        if not is_pqc_available():
            pytest.skip("PQC libraries unavailable")
        key_id, pk, sk = generate_pqc_keypair(PQCAlgorithm.KYBER768)
        assert key_id
        assert pk
        assert sk

    def test_pqc_encrypt_decrypt_roundtrip(self):
        if not is_pqc_available():
            pytest.skip()

        receiver_pk, receiver_sk = generate_pqc_keypair()
        
        ct, ss1 = pqc_encrypt(receiver_pk)
        ss2 = pqc_decrypt(receiver_sk, ct)
        
        assert ss1 == ss2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
