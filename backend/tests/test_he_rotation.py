"""
Tests for HE Key Rotation with Graceful Migration.

Validates:
- Key rotation scheduling and execution
- Grace period decryption with old keys
- Ciphertext metadata version tracking
- Migration of ciphertexts to new key (re-encryption)
- Cross-version compatibility
"""

import pytest
import os
import sys
import base64
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import numpy as np
from app.models.homomorphic_encryption import (
    HomomorphicEncryptionEngine, HEContextConfig,
    HEKeyManager, HEKeyRotationManager, HECiphertextMetadata
)

# Conditional on TenSEAL
try:
    import tenseal as ts
    TENSEAL = True
except ImportError:
    TENSEAL = False

pytestmark = pytest.mark.skipif(not TENSEAL, reason="TenSEAL required")


class TestHEKeyRotation:
    """Test key rotation lifecycle."""
    
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = HEContextConfig(key_rotation_days=1)  # Short for tests
        self.key_manager = HEKeyManager(self.config, keys_dir=self.tmpdir)
        self.km = self.key_manager
    
    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def test_initial_key_not_due(self):
        self.km.generate_key("key1")
        assert self.km.should_rotate() is False
    
    def test_rotation_due_after_threshold(self):
        self.km.generate_key("key1")
        # Artificially age the key
        self.km._keys["key1"]["created_at"] = (
            datetime.utcnow() - timedelta(days=2)
        ).isoformat()
        assert self.km.should_rotate() is True
    
    def test_rotate_creates_new_key_and_deactivates_old(self):
        old_id = self.km.generate_key("key1")
        new_id = self.km.rotate_key("key2")
        
        assert new_id == "key2"
        assert self.km._current_key_id == new_id
        assert self.km._keys[old_id]["active"] is False
        assert self.km._keys[new_id]["active"] is True
    
    def test_rotation_manager_grace_period(self):
        # Create rotator
        rot_mgr = HEKeyRotationManager(self.km, rotation_days=1, grace_days=3)
        
        # No old keys
        valid_keys = rot_mgr.get_keys_for_decryption()
        assert len(valid_keys) == 0
        
        # Generate key and age it
        k1 = self.km.generate_key("key1")
        self.km._keys[k1]["created_at"] = (datetime.utcnow() - timedelta(days=2)).isoformat()
        
        valid = rot_mgr.get_keys_for_decryption()
        assert len(valid) == 1  # Still in grace period
        
        # Expire grace
        self.km._keys[k1]["created_at"] = (datetime.utcnow() - timedelta(days=5)).isoformat()
        valid = rot_mgr.get_keys_for_decryption()
        assert len(valid) == 0  # Archived


class TestCiphertextMigration:
    """Test migrating ciphertexts between key versions."""
    
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = HEContextConfig()
        self.key_manager = HEKeyManager(self.config, keys_dir=self.tmpdir)
        self.engine = HomomorphicEncryptionEngine(
            config=self.config,
            require_he=False,
            enable_validation=False
        )
        self.engine.key_manager = self.key_manager
        
        # Init keys
        self.key_manager.generate_key("key-v1")
        self.engine._initialize_he()
    
    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def test_ciphertext_metadata_versioning(self):
        emb = np.random.randn(128).astype(np.float32)
        emb = emb / (np.linalg.norm(emb) + 1e-8)
        
        enc = self.engine.encrypt_embedding(emb)
        
        assert "metadata" in enc
        meta = enc["metadata"]
        assert meta["key_id"] == "key-v1"
        assert meta["version"] == "1"
    
    def test_migrate_metadata_updates_key_id(self):
        package = {
            "ciphertext": base64.b64encode(b"dummy").decode(),
            "metadata": {
                "version": "1",
                "scheme": "CKKS",
                "key_id": "key-v1",
                "created_at": datetime.utcnow().isoformat()
            },
            "mac": None,
            "nonce": "abc"
        }
        
        # Simulate rotation
        self.key_manager.rotate_key("key-v2")
        self.engine._active_key_id = "key-v2"
        
        migrated = self.engine._rotation_mgr.migrate_ciphertext(package)
        
        assert migrated["metadata"]["key_id"] == "key-v2"
        assert migrated["metadata"]["version"] == "1"  # Unchanged


class TestHEEngineWithRotation:
    """Integration: HE engine with automatic key rotation."""
    
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = HEContextConfig(key_rotation_days=1)
        self.engine = HomomorphicEncryptionEngine(
            config=self.config,
            require_he=False,
            enable_validation=False
        )
        self.engine.key_manager = HEKeyManager(self.config, keys_dir=self.tmpdir)
        self.engine._rotation_mgr = HEKeyRotationManager(
            self.engine.key_manager,
            rotation_days=1,
            grace_days=2
        )
        
        # Init
        self.engine.key_manager.generate_key("initial")
        self.engine._active_key_id = "initial"
    
    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def test_encryption_uses_active_key(self):
        if self.engine.simulation_mode:
            pytest.skip()
        
        emb = np.random.randn(256).astype(np.float32)
        enc = self.engine.encrypt_embedding(emb)
        meta = enc.get("metadata", {})
        assert meta.get("key_id") == "initial"
    
    def test_decryption_with_rotated_key(self):
        """Decrypting ciphertext encrypted with old key after rotation."""
        if self.engine.simulation_mode:
            pytest.skip()
        
        emb = np.random.randn(256).astype(np.float32)
        emb = emb / (np.linalg.norm(emb) + 1e-8)
        
        # Encrypt with initial key
        enc = self.engine.encrypt_embedding(emb)
        old_key_id = enc["metadata"]["key_id"]
        assert old_key_id == "initial"
        
        # Rotate
        new_id = self.engine.key_manager.rotate_key("rotated")
        self.engine._active_key_id = new_id
        
        # Decrypt with new engine should still work (uses old key behind scenes)
        decrypted = self.engine.decrypt_embedding(enc)
        assert decrypted is not None
        assert np.allclose(emb, decrypted, atol=1e-3)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
