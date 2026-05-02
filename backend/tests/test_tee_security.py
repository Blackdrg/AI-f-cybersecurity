import pytest
import json
import base64
from unittest.mock import Mock, patch
from backend.app.models.attestation import AttestationVerifier, EnclaveSession
from backend.app.models.crypto_attestation import CryptoAttestation

class TestAttestationVerifier:
    def test_valid_document(self):
        verifier = AttestationVerifier()
        doc = {'documentType':'NitroEnclave','pcrs':{'PCR3':'a'},'certificate':'c','timestamp':'t'}
        encoded = base64.b64encode(json.dumps(doc).encode()).decode()
        result = verifier.verify_attestation_document(encoded, 'hash')
        assert result['success'] == True

    def test_missing_pcr3(self):
        verifier = AttestationVerifier()
        doc = {'documentType':'N','pcrs':{'PCR0':'a'},'certificate':'c','timestamp':'t'}
        encoded = base64.b64encode(json.dumps(doc).encode()).decode()
        result = verifier.verify_attestation_document(encoded, 'hash')
        assert result['success'] == False
        assert 'PCR3' in result['error']

    def test_nonce(self):
        verifier = AttestationVerifier()
        n1 = verifier.generate_nonce()
        n2 = verifier.generate_nonce()
        assert n1 != n2

class TestEnclaveSession:
    def test_verify(self):
        with patch('backend.app.models.attestation.AttestationVerifier') as MV:
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
