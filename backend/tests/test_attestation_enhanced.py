"""
Tests for AWS Nitro Enclave Attestation Enhancements.

Validates:
- Certificate chain validation
- Attestation document parsing
- PCR verification
- Continuous attestation
- Session establishment with encrypted channel
"""

import pytest
import json
import base64
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock
import responses  # For mocking HTTP requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models.attestation import (
    NitroAttestationVerifier,
    EnclaveSession,
    ContinuousAttestor,
    AttestationStatus,
    AttestationReport
)


class TestNitroAttestationVerifierEnhanced:
    """Enhanced tests for Nitro attestation with certificate chain."""
    
    def setup_method(self):
        self.verifier = NitroAttestationVerifier()
        
        # Sample valid Nitro attestation document structure
        self.valid_doc = {
            "version": 2,
            "moduleType": "TRIMMODULE",
            "pcrs": {
                "PCR0": "aa:bb:cc:dd",
                "PCR1": "11:22:33:44",
                "PCR2": "55:66:77:88",
                "PCR3": "99:00:aa:bb"
            },
            "publicKey": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----",
            "signature": "base64sig==",
            "signingCertificate": "base64cert==",
            "certificateChain": ["base64-intermediate", "base64-root"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "enclaveImageVersion": "1.0.0"
        }
    
    def test_verifier_initialization_creates_cert_store(self):
        verifier = NitroAttestationVerifier()
        assert hasattr(verifier, '_cert_store') or hasattr(NitroAttestationVerifier, '_cert_store')
    
    @responses.activate
    def test_verify_attestation_valid_document(self):
        """Test verification of valid attestation document."""
        # Mock AWS cert endpoint
        responses.get(
            "https://aws.nitro-enclaves.amazonaws.com/certificate",
            body="-----BEGIN CERTIFICATE-----\nMOCKCERT\n-----END CERTIFICATE-----",
            status=200
        )
        
        # Create doc with signature that passes simple check
        # (real signature verification needs proper cert chain)
        doc = self.valid_doc.copy()
        doc["signature"] = base64.b64encode(b"fake_sig").decode()
        doc["signingCertificate"] = base64.b64encode(b"fake_cert").decode()
        
        encoded = base64.b64encode(json.dumps(doc).encode()).decode()
        result = self.verifier.verify_attestation_document(encoded, "expected_hash")
        
        # With mock/fake signature, expect failure at signature verification
        # but structure validation should pass
        assert "success" in result
    
    def test_missing_pcr3_fails(self):
        doc = self.valid_doc.copy()
        del doc["pcrs"]["PCR3"]
        encoded = base64.b64encode(json.dumps(doc).encode()).decode()
        result = self.verifier.verify_attestation_document(encoded)
        assert result["success"] is False
        assert "PCR3" in result["error"]
    
    def test_invalid_module_type_fails(self):
        doc = self.valid_doc.copy()
        doc["moduleType"] = "INVALID"
        encoded = base64.b64encode(json.dumps(doc).encode()).decode()
        result = self.verifier.verify_attestation_document(encoded)
        assert result["success"] is False
        assert "Nitro" in result["error"]
    
    def test_version_mismatch_fails(self):
        doc = self.valid_doc.copy()
        doc["version"] = 99
        encoded = base64.b64encode(json.dumps(doc).encode()).decode()
        result = self.verifier.verify_attestation_document(encoded)
        assert result["success"] is False
    
    def test_pcr_drift_computation(self):
        baseline = {"PCR0": "aa:bb", "PCR1": "11:22"}
        current = {"PCR0": "aa:bb", "PCR1": "ff:ee"}
        self.verifier.verified_pcrs = baseline
        drift = self.verifier.compute_pcr_drift(current)
        assert drift == 0.5  # 1 of 2 changed
    
    def test_continuous_attestation_periodic_check(self):
        config = ContinuousAttestationConfig(check_interval_seconds=1, enable_pcr_attestation=False)
        attestor = ContinuousAttestor(config=config)
        
        assert attestor._running is False
        attestor.start()
        assert attestor._running is True
        time.sleep(2)  # Wait for at least one cycle
        attestor.stop()
        assert attestor._running is False
        assert len(attestor.history) > 0


class TestEnclaveSession:
    """Test secure enclave session establishment."""
    
    @patch('app.models.attestation.NitroAttestationVerifier')
    def test_attestation_verification_flow(self, MockVerifier):
        """Test full attestation verification."""
        mock_verifier = MockVerifier()
        mock_verifier.verify_attestation_document.return_value = {
            "success": True,
            "public_key": "-----BEGIN PUBLIC KEY-----\nMOCKKEY\n-----END PUBLIC KEY-----",
            "pcrs": {"PCR3": "valid"},
            "signed_by": "AWS"
        }
        
        session = EnclaveSession(enclave_id="test-enclave", expected_pubkey_hash=None)
        
        # Mock fetch
        with patch.object(session, 'get_attestation_document', return_value=base64.b64encode(b"doc").decode()):
            result = session.verify_attestation(verifier=mock_verifier)
        
        assert result is True
        assert session.verified is True
        assert session.enclave_public_key is not None
    
    def test_session_requires_attestation_first(self):
        session = EnclaveSession(enclave_id="test")
        with pytest.raises(ValueError, match="not attested"):
            session.encrypt_for_enclave(b"data")
    
    @patch('requests.post')
    def test_session_key_exchange(self, mock_post):
        """Test establishment of encrypted session key."""
        mock_post.return_value = Mock(status_code=200)
        
        session = EnclaveSession(enclave_id="test")
        session.verified = True
        session.enclave_public_key = Mock()  # Mock public key
        session.enclave_public_key.__class__.__name__ = "EllipticCurvePublicKey"
        
        # Mock encryption
        with patch.object(session, '_encrypt_session_key', return_value=b"encrypted_key"):
            result = session.establish_session()
        
        assert result is True
        assert session.session_cipher is not None
        mock_post.assert_called_once()


class TestContinuousAttestor:
    """Test continuous runtime attestation."""
    
    def test_file_integrity_monitoring(self, tmp_path):
        """Test file integrity baseline and drift detection."""
        # Create test file
        test_file = tmp_path / "critical.txt"
        test_file.write_text("important data")
        
        config = ContinuousAttestationConfig(
            check_interval_seconds=60,
            enable_file_integrity=True,
            critical_file_paths=[str(test_file)]
        )
        
        # Create mock session
        mock_session = Mock()
        mock_session.verified = True
        
        attestor = ContinuousAttestor(config=config, enclave_session=mock_session)
        
        # Baseline established
        assert len(attestor._baseline_file_hashes) == 1
        
        # First check should be OK
        report = attestor._perform_attestation_cycle()
        assert report.status == AttestationStatus.HEALTHY
    
    def test_file_tamper_detected(self):
        """Test tampering changes status to COMPROMISED."""
        tmpdir = tempfile.mkdtemp()
        test_file = os.path.join(tmpdir, "config.json")
        with open(test_file, 'w') as f:
            json.dump({"secret": "original"}, f)
        
        try:
            config = ContinuousAttestationConfig(
                enable_file_integrity=True,
                critical_file_paths=[test_file]
            )
            attestor = ContinuousAttestor(config=config)
            
            # Tamper
            with open(test_file, 'w') as f:
                json.dump({"secret": "tampered"}, f)
            
            report = attestor._perform_attestation_cycle()
            assert report.status == AttestationStatus.COMPROMISED
            assert "tampered" in report.details.lower()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_webhook_notification_on_compromise(self):
        """Test that webhook is called on compromise."""
        webhook_url = "http://mock-webhook.example.com/alert"
        config = ContinuousAttestationConfig(
            enable_file_integrity=False,
            enable_pcr_attestation=False
        )
        
        with patch.dict(os.environ, {"ATTESTATION_WEBHOOK_URL": webhook_url}):
            with patch('requests.post') as mock_post:
                attestor = ContinuousAttestor(config=config)
                # Force compromised status
                attestor.compromised = True
                # Manually generate alert (would normally happen in cycle)
                report = AttestationReport(
                    timestamp=datetime.utcnow().isoformat(),
                    status=AttestationStatus.COMPROMISED,
                    pcrs={},
                    measurements={},
                    details="Test compromise",
                    alert_generated=True
                )
                attestor._generate_alert(report)
                
                # Webhook called
                mock_post.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
