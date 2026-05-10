import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from unittest.mock import patch, MagicMock

from app.security.pqc import (
    PQCScheme, QuantumResistantCrypto, HybridCrypto,
    get_pqc_keypair, pqc_encrypt, pqc_decrypt,
    pqc_sign, pqc_verify, is_pqc_available
)

class TestPQCScheme:
    def test_scheme_values(self):
        assert PQCScheme.KYBER512.value == "kyber512"
        assert PQCScheme.KYBER768.value == "kyber768"
        assert PQCScheme.KYBER1024.value == "kyber1024"
        assert PQCScheme.DILITHIUM2.value == "dilithium2"
        assert PQCScheme.DILITHIUM3.value == "dilithium3"
        assert PQCScheme.DILITHIUM5.value == "dilithium5"


class TestQuantumResistantCrypto:
    def test_init(self):
        crypto = QuantumResistantCrypto(scheme=PQCScheme.KYBER768)
        assert crypto.scheme == PQCScheme.KYBER768

    def test_check_pqc_unavailable_kyber(self):
        with patch("app.security.pqc.KYBER_AVAILABLE", False):
            crypto = QuantumResistantCrypto(scheme=PQCScheme.KYBER768)
            with pytest.raises(RuntimeError, match="Kyber not available"):
                crypto._check_pqc_available()

    def test_check_pqc_unavailable_dilithium(self):
        with patch("app.security.pqc.DILITHIUM_AVAILABLE", False):
            crypto = QuantumResistantCrypto(scheme=PQCScheme.DILITHIUM3)
            with pytest.raises(RuntimeError, match="Dilithium not available"):
                crypto._check_pqc_available()

    def test_generate_keypair_unavailable(self):
        with patch("app.security.pqc.KYBER_AVAILABLE", False):
            crypto = QuantumResistantCrypto(scheme=PQCScheme.KYBER768)
            with pytest.raises(RuntimeError):
                crypto.generate_keypair()

    def test_encapsulate_unavailable(self):
        crypto = QuantumResistantCrypto(scheme=PQCScheme.KYBER768)
        with patch("app.security.pqc.KYBER_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Kyber not available"):
                crypto.encapsulate(b"fake_public_key")

    def test_decapsulate_unavailable(self):
        crypto = QuantumResistantCrypto(scheme=PQCScheme.KYBER768)
        with patch("app.security.pqc.KYBER_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Kyber not available"):
                crypto.decapsulate(b"fake_secret_key", b"fake_ciphertext")

    def test_sign_unavailable(self):
        crypto = QuantumResistantCrypto(scheme=PQCScheme.DILITHIUM3)
        with patch("app.security.pqc.DILITHIUM_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Dilithium not available"):
                crypto.sign(b"secret_key", b"message")

    def test_verify_unavailable(self):
        crypto = QuantumResistantCrypto(scheme=PQCScheme.DILITHIUM3)
        with patch("app.security.pqc.DILITHIUM_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="Dilithium not available"):
                crypto.verify(b"public_key", b"message", b"signature")

    def test_unknown_scheme(self):
        crypto = QuantumResistantCrypto(scheme=PQCScheme.KYBER768)
        with patch("app.security.pqc.KYBER_AVAILABLE", False):
            with patch("app.security.pqc.DILITHIUM_AVAILABLE", False):
                with pytest.raises(RuntimeError):
                    crypto.generate_keypair()


class TestHybridCrypto:
    def test_init(self):
        hc = HybridCrypto()
        assert hc.pqc_scheme == PQCScheme.KYBER768

    def test_init_custom_scheme(self):
        hc = HybridCrypto(pqc_scheme=PQCScheme.KYBER1024)
        assert hc.pqc_scheme == PQCScheme.KYBER1024

    def test_generate_hybrid_keypair(self):
        with patch("app.security.pqc.KYBER_AVAILABLE", False):
            hc = HybridCrypto()
            with pytest.raises(RuntimeError):
                hc.generate_hybrid_keypair()


class TestConvenienceFunctions:
    def test_get_pqc_keypair_unavailable(self):
        with patch("app.security.pqc.KYBER_AVAILABLE", False):
            with pytest.raises(RuntimeError):
                get_pqc_keypair()

    def test_pqc_encrypt_unavailable(self):
        with patch("app.security.pqc.KYBER_AVAILABLE", False):
            with pytest.raises(RuntimeError):
                pqc_encrypt(b"message", b"public_key")

    def test_pqc_decrypt_unavailable(self):
        with patch("app.security.pqc.KYBER_AVAILABLE", False):
            with pytest.raises(RuntimeError):
                pqc_decrypt(b"ciphertext", b"secret_key")

    def test_pqc_sign_unavailable(self):
        with patch("app.security.pqc.DILITHIUM_AVAILABLE", False):
            with pytest.raises(RuntimeError):
                pqc_sign(b"message", b"secret_key")

    def test_pqc_verify_unavailable(self):
        with patch("app.security.pqc.DILITHIUM_AVAILABLE", False):
            with pytest.raises(RuntimeError):
                pqc_verify(b"message", b"signature", b"public_key")

    def test_is_pqc_available_no_libs(self):
        with patch("app.security.pqc.KYBER_AVAILABLE", False):
            with patch("app.security.pqc.DILITHIUM_AVAILABLE", False):
                assert is_pqc_available() is False

    def test_is_pqc_available_kyber(self):
        with patch("app.security.pqc.KYBER_AVAILABLE", True):
            assert is_pqc_available(PQCScheme.KYBER768) is True

    def test_is_pqc_available_dilithium(self):
        with patch("app.security.pqc.DILITHIUM_AVAILABLE", True):
            assert is_pqc_available(PQCScheme.DILITHIUM3) is True

    def test_is_pqc_available_any(self):
        with patch("app.security.pqc.KYBER_AVAILABLE", True):
            assert is_pqc_available() is True


class TestPQCWithMocks:
    """Test PQC with mocked library responses."""

    def test_pqc_roundtrip_mocked(self):
        fake_pk = b"fake_public_key_12345"
        fake_sk = b"fake_secret_key_67890"
        fake_ct = b"fake_ciphertext"
        fake_ss = b"fake_shared_secret"

        import app.security.pqc as pqc_module
        with patch.object(pqc_module, "kyber", create=True) as mock_kyber:
            mock_kyber.keypair.return_value = (fake_pk, fake_sk)
            mock_kyber.encap.return_value = (fake_ct, fake_ss)
            mock_kyber.decap.return_value = fake_ss

            with patch("app.security.pqc.KYBER_AVAILABLE", True):
                crypto = QuantumResistantCrypto(PQCScheme.KYBER768)
                pk, sk = crypto.generate_keypair()
                assert pk == fake_pk
                assert sk == fake_sk

                ct, ss = crypto.encapsulate(pk)
                assert ct == fake_ct
                assert ss == fake_ss

                recovered = crypto.decapsulate(sk, ct)
                assert recovered == fake_ss

    def test_dilithium_roundtrip_mocked(self):
        fake_pk = b"fake_dilithium_public_key"
        fake_sk = b"fake_dilithium_secret_key"
        fake_sig = b"fake_signature"
        message = b"test message"

        import app.security.pqc as pqc_module
        with patch.object(pqc_module, "dilithium", create=True) as mock_dilithium:
            mock_dilithium.keypair.return_value = (fake_pk, fake_sk)
            mock_dilithium.sign.return_value = fake_sig
            mock_dilithium.verify.return_value = True

            with patch("app.security.pqc.DILITHIUM_AVAILABLE", True):
                crypto = QuantumResistantCrypto(PQCScheme.DILITHIUM3)
                pk, sk = crypto.generate_keypair()

                sig = crypto.sign(sk, message)
                assert sig == fake_sig

                assert crypto.verify(pk, message, sig) is True