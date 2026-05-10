import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.security.hsm import (
    HSMKeystore, HSMMode, HSMWithoutError, SoftHSMKeystore, CloudHSMKeystore, get_hsm_keystore
)


class TestHSMMode:
    def test_hsm_mode_values(self):
        assert HSMMode.SOFTWARE.value == "software"
        assert HSMMode.CLOUD.value == "cloud"
        assert HSMMode.NONE.value == "none"

    def test_hsm_without_error(self):
        err = HSMWithoutError("test error")
        assert str(err) == "test error"


class TestSoftHSMKeystore:
    def test_init(self):
        keystore = SoftHSMKeystore(token_label="test-token", pin="5678")
        assert keystore.token_label == "test-token"
        assert keystore.pin == "5678"
        assert keystore._initialized is False

    def test_detect_softhsm_lib_none(self):
        keystore = SoftHSMKeystore()
        result = keystore._detect_softhsm_lib()
        assert result is None or isinstance(result, str)

    def test_is_available_uninitialized(self):
        keystore = SoftHSMKeystore()
        assert keystore.is_available() is False

    def test_initialize_without_pkcs11(self):
        with patch("app.security.hsm.PKCS11_AVAILABLE", False):
            keystore = SoftHSMKeystore()
            result = keystore.initialize()
            assert result is False

    def test_initialize_without_lib(self):
        keystore = SoftHSMKeystore(lib_path=None)
        result = keystore.initialize()
        assert result is False


class TestCloudHSMKeystore:
    def test_init_aws_missing_boto3(self):
        with patch("app.security.hsm.AWS_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="boto3 required"):
                CloudHSMKeystore(provider="aws")

    def test_init_azure_missing_lib(self):
        with patch("app.security.hsm.AZURE_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="azure-keyvault-keys required"):
                CloudHSMKeystore(provider="azure")

    def test_is_available_initialized(self):
        with patch("app.security.hsm.AWS_AVAILABLE", True):
            with patch("app.security.hsm.boto3.session.Session") as mock_session:
                mock_client = MagicMock()
                mock_session.return_value.client.return_value = mock_client
                keystore = CloudHSMKeystore(provider="aws", key_id="test-key")
                assert keystore.is_available() is True


class TestHSMKeystore:
    def test_init_default_mode(self):
        with patch.dict(os.environ, {"HSM_MODE": "none"}):
            keystore = HSMKeystore()
            assert keystore.mode == HSMMode.NONE
            assert keystore.is_available() is False

    def test_init_software_mode(self):
        with patch.dict(os.environ, {"HSM_MODE": "software"}):
            keystore = HSMKeystore()
            assert keystore.mode == HSMMode.SOFTWARE

    def test_initialize_software_success(self):
        keystore = HSMKeystore()
        keystore.mode = HSMMode.SOFTWARE
        keystore._software = SoftHSMKeystore()
        keystore._software._initialized = True

        with patch.object(keystore._software, "initialize", return_value=True):
            result = keystore.initialize()
            assert result is True
            assert keystore._initialized is True

    def test_initialize_none_mode(self):
        with patch.dict(os.environ, {"HSM_MODE": "none"}):
            keystore = HSMKeystore()
            result = keystore.initialize()
            assert result is True

    def test_encrypt_without_initialization(self):
        keystore = HSMKeystore()
        keystore.mode = HSMMode.SOFTWARE

        with pytest.raises(HSMWithoutError, match="HSM not initialized"):
            keystore.encrypt("key1", b"data")

    def test_generate_key_cloud_not_implemented(self):
        keystore = HSMKeystore()
        keystore.mode = HSMMode.CLOUD
        keystore._initialized = True
        result = keystore.generate_key("test-key")
        assert result is None

    def test_rotate_key_software(self):
        keystore = HSMKeystore()
        keystore.mode = HSMMode.SOFTWARE
        keystore._software = SoftHSMKeystore()

        with patch.object(keystore._software, "generate_key", return_value="test-key"):
            result = keystore.rotate_key("old-key", "new-key")
            assert result is True

    def test_get_status(self):
        with patch.dict(os.environ, {"HSM_MODE": "none"}):
            keystore = HSMKeystore()
            keystore._initialized = True
            status = keystore.get_status()
            assert status["mode"] == "none"
            assert status["initialized"] is True
            assert status["available"] is False

    def test_close(self):
        keystore = HSMKeystore()
        keystore._software = SoftHSMKeystore()
        keystore._initialized = True
        keystore.close()
        assert keystore._initialized is False


class TestGetHSMKeystore:
    def test_singleton(self):
        ks1 = get_hsm_keystore()
        ks2 = get_hsm_keystore()
        assert ks1 is ks2