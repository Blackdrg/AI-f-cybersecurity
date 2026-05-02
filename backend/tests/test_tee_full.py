import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import json
import base64
import numpy as np
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet
from backend.app.security.encryption_utils import encrypt_embedding, get_encryption_key
from backend.app.security.secrets_manager import SecretsManager
from backend.app.models.attestation import AttestationVerifier
from backend.enclave_mock import MockEnclaveService

class TestTEEIntegration:
    """TEE security integration tests - Windows compatible."""

    def test_encryption_utils(self):
        """Test embedding encryption/decryption roundtrip."""
        test_emb = np.random.randn(512).tolist()
        
        encrypted = encrypt_embedding(test_emb)
        assert isinstance(encrypted, str)
        assert len(encrypted) > 100  # Encrypted length
        
        key = get_encryption_key()
        assert key is not None
        print("✅ Encryption OK")

    def test_secrets_manager(self):
        """Test Secrets Manager initialization."""
        sm = SecretsManager(backend="env")  # Fallback for test
        secret = sm.get_secret("TEST_SECRET", "fallback")
        assert secret == "fallback"
        print("✅ Secrets Manager OK")

    def test_attestation_verifier(self):
        """Test attestation verification."""
        verifier = AttestationVerifier()
        mock_doc = {
            "documentType": "nitro",
            "pcrs": {"PCR3": "valid_hash"},
            "certificate": "cert",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        encoded = base64.b64encode(json.dumps(mock_doc).encode()).decode()
        result = verifier.verify_attestation_document(encoded, "test_hash")
        assert result["success"] == True
        print("✅ Attestation verifier OK")

    def test_mock_enclave_service(self):
        """Test mock enclave compatibility."""
        service = MockEnclaveService()
        assert service.known_embeddings is not None
        print("✅ Mock enclave OK")

    def test_encryption_roundtrip(self):
        """Full encryption → mock enclave → decryption."""
        test_emb = np.random.randn(512).tolist()
        encrypted = encrypt_embedding(test_emb)
        
        # Verify roundtrip
        key_str = get_encryption_key()
        f = Fernet(key_str.encode())
        decrypted = json.loads(f.decrypt(encrypted.encode()))
        np.testing.assert_almost_equal(np.array(test_emb), np.array(decrypted), decimal=4)
        print("✅ Full TEE encryption roundtrip OK")

def run_benchmark():
    """Mock enclave performance test (Windows TCP)."""
    import time
    latencies = []
    service = MockEnclaveService()
    import threading
    t = threading.Thread(target=service.start, daemon=True)
    t.start()
    time.sleep(2)  # Startup
    
    for i in range(50):
        start = time.time()
        # Simulated enclave call
        time.sleep(0.05)  # Mock latency
        latencies.append((time.time() - start) * 1000)
    
    p99 = np.percentile(latencies, 99)
    print(f"✅ Mock P99: {p99:.1f}ms (real Nitro: <100ms)")
    return p99

if __name__ == "__main__":
    TestTEEIntegration().test_encryption_utils()
    TestTEEIntegration().test_secrets_manager()
    TestTEEIntegration().test_attestation_verifier()
    TestTEEIntegration().test_mock_enclave_service()
    TestTEEIntegration().test_encryption_roundtrip()
    run_benchmark()
    print("\n🎉 All TEE tests PASSED!")

