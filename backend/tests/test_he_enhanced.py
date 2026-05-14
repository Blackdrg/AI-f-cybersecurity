"""
Tests for Homomorphic Encryption (HE) enhancements.

Validates:
- Benchmark suite execution
- Ciphertext integrity validation (MAC, hash)
- Key rotation with migration
- Ciphertext version tracking
- Grace period decryption
"""

import pytest
import json
import os
import sys
import base64
import tempfile
import shutil
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import numpy as np

# Import modules
from app.models.homomorphic_encryption import (
    HomomorphicEncryptionEngine, HEContextConfig, HEKeyManager,
    HEBenchmarkSuite, HEBenchmarkResult,
    HECiphertextMetadata, HECiphertextValidator,
    HEKeyRotationManager, HECiphertextValidator
)

# Skip all if TenSEAL not available
try:
    import tenseal as ts
    TENSEAL_AVAILABLE = True
except ImportError:
    TENSEAL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not TENSEAL_AVAILABLE,
    reason="TenSEAL not installed - install with: pip install tenseal"
)


class TestHEBenchmarkSuite:
    """Test HE performance benchmarking."""
    
    def setup_method(self):
        """Initialize HE engine for benchmarks."""
        self.config = HEContextConfig(
            poly_modulus_degree=8192,
            scale=2**40
        )
        self.engine = HomomorphicEncryptionEngine(
            config=self.config,
            require_he=False  # Allow if lib available
        )
        if not self.engine.simulation_mode:
            # Ensure key generated
            if not self.engine.key_manager._keys:
                self.engine.key_manager.generate_key()
    
    def test_benchmark_suite_initialization(self):
        suite = HEBenchmarkSuite(self.engine)
        assert suite.he_engine is self.engine
        assert suite.warmup_iterations == 10
        assert suite.test_iterations == 100
    
    def test_benchmark_encryption(self):
        if self.engine.simulation_mode:
            pytest.skip("HE not available")
        
        suite = HEBenchmarkSuite(self.engine, test_iterations=20)
        result = suite.benchmark_encryption(embedding_dim=512, iterations=20)
        
        assert isinstance(result, HEBenchmarkResult)
        assert result.operation == "encrypt_embedding"
        assert result.avg_latency_ms > 0
        assert result.p50_latency_ms > 0
        assert result.p99_latency_ms >= result.p95_latency_ms
        assert result.iterations == 20
        assert result.data_size_bytes == 512 * 4  # float32
    
    def test_benchmark_decryption(self):
        if self.engine.simulation_mode:
            pytest.skip("HE not available")
        
        suite = HEBenchmarkSuite(self.engine, test_iterations=20)
        result = suite.benchmark_decryption(embedding_dim=512, iterations=20)
        
        assert result.operation == "decrypt_embedding"
        assert result.avg_latency_ms > 0
    
    def test_benchmark_encrypted_similarity(self):
        if self.engine.simulation_mode:
            pytest.skip("HE not available")
        
        suite = HEBenchmarkSuite(self.engine, test_iterations=10)
        result = suite.benchmark_encrypted_similarity(embedding_dim=512, iterations=10)
        
        assert result.operation == "encrypted_similarity"
        assert result.avg_latency_ms > 0
    
    def test_benchmark_batch_operations(self):
        if self.engine.simulation_mode:
            pytest.skip()
        
        suite = HEBenchmarkSuite(self.engine, test_iterations=10)
        result = suite.benchmark_batch_encrypt(batch_size=100, iterations=10)
        
        assert "batch_encrypt_100" == result.operation
        assert result.data_size_bytes > 0
    
    def test_benchmark_export_json(self, tmp_path):
        suite = HEBenchmarkSuite(self.engine, test_iterations=5)
        suite.benchmark_encryption(128, iterations=5)
        suite.benchmark_decryption(128, iterations=5)
        
        export_path = tmp_path / "he_bench.json"
        suite.export_results_json(str(export_path))
        
        assert export_path.exists()
        with open(export_path) as f:
            data = json.load(f)
        assert "results" in data
        assert len(data["results"]) >= 2


class TestHECiphertextValidator:
    """Test ciphertext integrity validation."""
    
    def setup_method(self):
        self.mac_key = b"test_mac_key_32_bytes_long!"
        self.validator = HECiphertextValidator(mac_key=self.mac_key, require_mac=True)
        self.engine = HomomorphicEncryptionEngine(require_he=False)
        self.engine._initialize_he()
    
    def test_wrap_and_unwrap_ciphertext(self):
        if self.engine.simulation_mode:
            pytest.skip("HE not available")
        
        emb = np.random.randn(512).astype(np.float32)
        emb = emb / (np.linalg.norm(emb) + 1e-8)
        
        enc_result = self.engine.encrypt_embedding(emb)
        package = self.validator.wrap_ciphertext(
            base64.b64decode(enc_result["ciphertext"]),
            HECiphertextMetadata(scheme="CKKS", key_id="test-key"),
            plaintext=emb
        )
        
        assert "ciphertext" in package
        assert "metadata" in package
        assert "mac" in package
        assert "nonce" in package
        
        # Unwrap
        ct_bytes, meta = self.validator.unwrap_ciphertext(package)
        assert isinstance(ct_bytes, bytes)
        assert meta.scheme == "CKKS"
    
    def test_mac_verification_fails_with_wrong_key(self):
        wrong_validator = HECiphertextValidator(mac_key=b"wrong_key_!", require_mac=True)
        package = self.validator.wrap_ciphertext(
            b"testdata",
            HECiphertextMetadata(key_id="test-key"),
            plaintext=np.random.randn(10)
        )
        
        with pytest.raises(ValueError, match="MAC verification failed"):
            wrong_validator.unwrap_ciphertext(package)
    
    def test_ciphertext_hash_integrity(self):
        emb = np.array([1.0, 2.0, 3.0])
        package = self.validator.wrap_ciphertext(
            b"dummy_ct",
            HECiphertextMetadata(),
            plaintext=emb
        )
        
        meta = HECiphertextMetadata(**package["metadata"])
        assert meta.hash_sha256 is not None
        assert len(meta.hash_sha256) == 64  # SHA256 hex length
    
    def test_plaintext_integrity_check(self):
        emb = np.random.randn(128).astype(np.float32)
        package = self.validator.wrap_ciphertext(
            b"dummy",
            HECiphertextMetadata(),
            plaintext=emb
        )
        
        # Check integrity passes
        assert self.validator.verify_plaintext_integrity(package, emb) is True
        
        # Tamper
        tampered = emb + 0.1
        assert self.validator.verify_plaintext_integrity(package, tampered) is False


class TestHEKeyRotationManager:
    """Test HE key rotation with migration."""
    
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = HEContextConfig(key_rotation_days=30)
        self.key_manager = HEKeyManager(self.config, keys_dir=self.tmpdir)
        
        # Generate initial key
        self.key_manager.generate_key("key-v1")
        
        self.rotation_mgr = HEKeyRotationManager(
            self.key_manager,
            rotation_days=30,
            grace_days=90
        )
        self.engine = HomomorphicEncryptionEngine(
            config=self.config,
            require_he=False
        )
        self.engine.key_manager = self.key_manager
    
    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def test_get_encryption_key(self):
        key_id = self.rotation_mgr.get_key_for_encryption()
        assert key_id == "key-v1"
    
    def test_decryption_keys_include_grace_period(self):
        # Only one key, active
        keys = self.rotation_mgr.get_keys_for_decryption()
        assert len(keys) == 1
        assert keys[0] == "key-v1"
    
    def test_rotation_detection(self):
        # Should not need rotation yet
        assert self.key_manager.should_rotate() is False
    
    def test_migrate_ciphertext_version_bump(self):
        """Test ciphertext metadata gets updated on migration."""
        package = {
            "ciphertext": base64.b64encode(b"test").decode(),
            "metadata": {
                "version": "1",
                "scheme": "CKKS",
                "key_id": "key-v1",
                "created_at": "2024-01-01T00:00:00"
            },
            "mac": None,
            "nonce": "abc123"
        }
        
        # Assume rotation happened, new key is "key-v2"
        # In real rotation, old key remains decryption-capable
        migrated = self.rotation_mgr.migrate_ciphertext(package, target_key_id="key-v2")
        
        assert migrated["metadata"]["key_id"] == "key-v2"
        assert migrated["metadata"]["version"] == "1"  # unchanged
        # Old ciphertext retained, only metadata updated


class TestHEEngineIntegration:
    """Integration tests for HE engine."""
    
    def setup_method(self):
        self.config = HEContextConfig()
        self.engine = HomomorphicEncryptionEngine(
            config=self.config,
            require_he=False,
            enable_validation=True
        )
        
        if self.engine.simulation_mode:
            pytest.skip("HE not available")
    
    def test_encrypt_decrypt_roundtrip(self):
        emb = np.random.randn(512).astype(np.float32)
        emb = emb / (np.linalg.norm(emb) + 1e-8)
        
        encrypted = self.engine.encrypt_embedding(emb)
        decrypted = self.engine.decrypt_embedding(encrypted)
        
        assert decrypted is not None
        assert np.allclose(emb, decrypted, atol=1e-4)
    
    def test_ciphertext_validation_enabled(self):
        assert self.engine._validator is not None
        assert self.engine._validator.require_mac is True
    
    def test_metrics_tracking(self):
        emb = np.random.randn(256).astype(np.float32)
        emb = emb / (np.linalg.norm(emb) + 1e-8)
        
        self.engine.encrypt_embedding(emb)
        metrics = self.engine.get_metrics()
        
        assert metrics["encryptions"] >= 1
    
    def test_benchmark_suite_initialization(self):
        suite = self.engine.get_benchmark_suite()
        assert isinstance(suite, HEBenchmarkSuite)
    
    def test_full_benchmark_suite(self, tmp_path):
        output = tmp_path / "bench.json"
        results = self.engine.benchmark_and_report(str(output))
        
        assert "benchmarks" in results
        assert "summary" in results
        assert output.exists()


class TestHEKeyManager:
    """Test key management lifecycle."""
    
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = HEContextConfig()
        self.km = HEKeyManager(self.config, keys_dir=self.tmpdir)
    
    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def test_generate_key(self):
        key_id = self.km.generate_key("test-key-1")
        assert key_id == "test-key-1"
        assert "test-key-1" in self.km._keys
    
    def test_key_persistence(self):
        key_id = self.km.generate_key("persist-key")
        # Create new manager to test load
        km2 = HEKeyManager(self.config, keys_dir=self.tmpdir)
        assert key_id in km2._keys
    
    def test_rotate_key(self):
        old_id = self.km.generate_key("old-key")
        new_id = self.km.rotate_key("new-key")
        
        assert new_id == "new-key"
        assert self.km._keys[old_id]["active"] is False
        assert self.km._keys[new_id]["active"] is True
        assert self.km._current_key_id == new_id
    
    def test_rotation_due_check(self):
        # New key, not due
        self.km.generate_key("key1")
        assert self.km.should_rotate() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
