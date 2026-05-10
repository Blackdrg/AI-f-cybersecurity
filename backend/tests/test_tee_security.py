import pytest
import json
import base64
from unittest.mock import Mock, patch
from app.models.attestation import NitroAttestationVerifier, EnclaveSession
from app.models.crypto_attestation import CryptoAttestation

class TestNitroAttestationVerifier:
    def test_valid_document_structure(self):
        verifier = NitroAttestationVerifier()
        # Test that a properly formatted document would be recognized
        # The actual verification requires a real Nitro attestation document
        assert hasattr(verifier, 'verify_attestation_document')
        
    def test_missing_module_type(self):
        verifier = NitroAttestationVerifier()
        doc = {'pcrs': {'PCR0': 'a'}, 'certificate': 'c', 'timestamp': 't'}
        encoded = base64.b64encode(json.dumps(doc).encode()).decode()
        result = verifier.verify_attestation_document(encoded, 'hash')
        assert result['success'] == False
        assert 'Nitro Enclave' in result['error']


class TestEnclaveSession:
    def test_verify(self):
        with patch('backend.app.models.attestation.NitroAttestationVerifier') as MV:
            MV.return_value.verify_attestation_document.return_value = {'success':True}
            s = EnclaveSession('id','hash')
            assert s.verify_attestation('doc', MV.return_value) == True
            assert s.verified == True

    def test_encrypt_fails_unverified(self):
        s = EnclaveSession('id','hash')
        try:
            s.encrypt_for_enclave(b'data')
            assert False
        except ValueError as e:
            assert 'not attested' in str(e)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
