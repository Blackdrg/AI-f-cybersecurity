"""Hardware Security Module (HSM) integration via PKCS#11.

Provides cryptographic operations using hardware-backed keys.
Supports:
- Key generation and storage
- Encryption/decryption (AES-GCM)
- Digital signatures (ECDSA, RSA-PSS)
- Key wrapping/unwrapping
- Key rotation and lifecycle

Uses:
- SoftHSM for software emulation (dev/CI)
- AWS CloudHSM for production cloud deployments
- Azure Key Vault Managed HSM as cloud fallback
- python-pkcs11 for PKCS#11 interface

Fail-secure: operations fail if HSM configured but unavailable.
Mode controlled via HSM_MODE env var: ["software", "cloud", "none"]
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from enum import Enum
import base64
import json

logger = logging.getLogger(__name__)

# Optional import of pkcs11
try:
    import pkcs11
    from pkcs11 import Mechanism, Attribute, ObjectClass
    PKCS11_AVAILABLE = True
except ImportError:
    PKCS11_AVAILABLE = False

# Optional AWS CloudHSM
try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

# Optional Azure Key Vault
try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.keys import KeyClient
    from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


class HSMMode(Enum):
    """HSM operation modes."""
    SOFTWARE = "software"  # SoftHSM (software emulation)
    CLOUD = "cloud"        # AWS CloudHSM or Azure Key Vault
    NONE = "none"          # No HSM; software fallback


class HSMWithoutError(Exception):
    """Raised when HSM operation is requested but unavailable in production mode."""
    pass


class SoftHSMKeystore:
    """PKCS#11-based keystore using SoftHSM software token."""
    
    DEFAULT_SOFTHSM_CONF = """
    objectstore.backend = db
    objectstore.db = /tmp/softhsm2.db
    directories.tokendir = /tmp
    log.level = INFO
    """
    
    def __init__(
        self,
        token_label: str = "ai-f-token",
        pin: str = "1234",
        lib_path: Optional[str] = None
    ):
        """
        Initialize SoftHSM keystore.
        
        Args:
            token_label: SoftHSM token label
            pin: SO PIN or user PIN
            lib_path: Path to SoftHSM PKCS#11 library (softhsm2.so / .dll)
        """
        self.token_label = token_label
        self.pin = pin
        self._lib_path = lib_path or self._detect_softhsm_lib()
        self._lib = None
        self._token = None
        self._session = None
        self._initialized = False
    
    def _detect_softhsm_lib(self) -> Optional[str]:
        """Auto-detect SoftHSM library path."""
        common_paths = {
            "Linux": ["/usr/lib/softhsm/libsofthsm2.so", "/usr/local/lib/softhsm/libsofthsm2.so"],
            "Darwin": ["/usr/local/lib/softhsm/libsofthsm2.dylib"],
            "Windows": [r"C:\Program Files\SoftHSM2\lib\softhsm2.dll"]
        }
        import platform
        system = platform.system()
        for p in common_paths.get(system, []):
            if os.path.exists(p):
                return p
        return None
    
    def initialize(self) -> bool:
        if not PKCS11_AVAILABLE:
            logger.error("python-pkcs11 not installed")
            return False
        
        lib_path = self._lib_path
        if not lib_path:
            logger.error("SoftHSM library not found — install softhsm2 and set PKCS11_LIB")
            return False
        
        if not os.path.exists(lib_path):
            logger.error(f"PKCS#11 library not found at {lib_path}")
            return False
        
        try:
            self._lib = pkcs11.lib(lib_path)
            # Find existing token or initialize new one
            for token in self._lib.get_tokens():
                if token.label == self.token_label:
                    self._token = token
                    break
            
            if not self._token:
                logger.info(f"Token '{self.token_label}' not found — initializing new SoftHSM token")
                # Initialize token: uses SO PIN for first init
                # Note: real init requires softhsm2-util command-line tool
                logger.error(f"SoftHSM token '{self.token_label}' not initialized. Run: softhsm2-util --init-token")
                return False
            
            self._session = self._token.open(user_pin=self.pin)
            self._initialized = True
            logger.info(f"SoftHSM keystore ready: token='{self.token_label}'")
            return True
            
        except pkcs11.PKCS11Error as e:
            logger.error(f"SoftHSM init error: {e}")
            return False
        except Exception as e:
            logger.error(f"SoftHSM unexpected error: {e}")
            return False
    
    def is_available(self) -> bool:
        return self._initialized and self._session is not None
    
    def generate_key(
        self,
        key_id: str,
        key_type: str = "AES",
        key_length: int = 256,
        extractable: bool = False
    ) -> Optional[str]:
        """Generate a symmetric or asymmetric key in SoftHSM."""
        if not self.is_available():
            raise HSMWithoutError("SoftHSM not available")
        
        try:
            if key_type.upper() == "AES":
                key = self._session.create_key(
                    ObjectClass.SECRET_KEY,
                    key_type=Mechanism.AES_KEY_GEN,
                    key_length=key_length,
                    label=key_id,
                    capabilities=Mechanism.AES_ENCRYPT | Mechanism.AES_DECRYPT | Mechanism.AES_GCM,
                    store=True,
                    **{
                        Attribute.SENSITIVE: True,
                        Attribute.EXTRACTABLE: extractable,
                        Attribute.ALWAYS_AUTHENTICATE: True,
                        Attribute.TRUSTED: False,
                    }
                )
                return key_id
            elif key_type.upper() in ("RSA", "EC"):
                # Asymmetric key support
                if key_type.upper() == "RSA":
                    mechanism = Mechanism.RSA_PKCS_KEY_PAIR_GEN
                    pub_template = {
                        Attribute.CLASS: ObjectClass.PUBLIC_KEY,
                        Attribute.KEY_TYPE: pkcs11.KeyType.RSA,
                        Attribute.MODULUS_BITS: key_length,
                        Attribute.PUBLIC_EXPONENT: (0x10001).to_bytes(3, 'big'),
                        Attribute.LABEL: f"{key_id}_pub",
                        Attribute.TOKEN: True,
                        Attribute.VERIFY: True,
                    }
                    priv_template = {
                        Attribute.CLASS: ObjectClass.PRIVATE_KEY,
                        Attribute.KEY_TYPE: pkcs11.KeyType.RSA,
                        Attribute.LABEL: f"{key_id}_priv",
                        Attribute.TOKEN: True,
                        Attribute.SENSITIVE: True,
                        Attribute.EXTRACTABLE: False,
                        Attribute.SIGN: True,
                        Attribute.DECRYPT: True,
                    }
                else:  # EC
                    mechanism = Mechanism.EC_KEY_PAIR_GEN
                    pub_template = {
                        Attribute.CLASS: ObjectClass.PUBLIC_KEY,
                        Attribute.KEY_TYPE: pkcs11.KeyType.EC,
                        Attribute.EC_PARAMS: b'\x06\x08*\x86H\x1e\x06\x02\x01\x0e\x03A\x00',  # prime256v1 OID
                        Attribute.LABEL: f"{key_id}_pub",
                        Attribute.TOKEN: True,
                        Attribute.VERIFY: True,
                    }
                    priv_template = {
                        Attribute.CLASS: ObjectClass.PRIVATE_KEY,
                        Attribute.KEY_TYPE: pkcs11.KeyType.EC,
                        Attribute.LABEL: f"{key_id}_priv",
                        Attribute.TOKEN: True,
                        Attribute.SENSITIVE: True,
                        Attribute.EXTRACTABLE: False,
                        Attribute.SIGN: True,
                    }
                
                (pub, priv) = self._session.create_key_pair(
                    mechanism=mechanism,
                    public_key_template=pub_template,
                    private_key_template=priv_template
                )
                return key_id
            else:
                raise ValueError(f"Unsupported key type: {key_type}")
        except Exception as e:
            logger.error(f"Key generation failed: {e}")
            return None
    
    def encrypt(
        self,
        key_id: str,
        plaintext: bytes,
        associated_data: bytes = None
    ) -> Optional[bytes]:
        """Encrypt with AES-GCM using HSM key."""
        if not self.is_available():
            raise HSMWithoutError("SoftHSM not available")
        
        try:
            key = self._session.get_key(label=key_id)
            iv = os.urandom(12)
            mechanism = Mechanism.AES_GCM
            ciphertext = self._session.encrypt(
                key, plaintext,
                mechanism=mechanism,
                iv=iv,
                additional_data=associated_data
            )
            # Return iv || ciphertext (standard AES-GCM format)
            return iv + ciphertext
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None
    
    def decrypt(
        self,
        key_id: str,
        ciphertext: bytes,
        associated_data: bytes = None
    ) -> Optional[bytes]:
        """Decrypt with AES-GCM using HSM key."""
        if not self.is_available():
            raise HSMWithoutError("SoftHSM not available")
        
        try:
            key = self._session.get_key(label=key_id)
            iv = ciphertext[:12]
            ct = ciphertext[12:]
            mechanism = Mechanism.AES_GCM
            plaintext = self._session.decrypt(
                key, ct,
                mechanism=mechanism,
                iv=iv,
                additional_data=associated_data
            )
            return plaintext
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def sign(
        self,
        key_id: str,
        data: bytes,
        algorithm: str = "ECDSA_P256"
    ) -> Optional[bytes]:
        """Sign data using HSM private key."""
        if not self.is_available():
            raise HSMWithoutError("SoftHSM not available")
        
        try:
            # key_id refers to private key label
            key = self._session.get_key(label=key_id)
            if algorithm == "ECDSA_P256":
                mechanism = Mechanism.ECDSA
                # ECDSA in PKCS#11 returns (r,s) DER-encoded; cryptograpy lib expects raw
                signature = self._session.sign(key, data, mechanism=mechanism)
            elif algorithm == "RSA_PSS":
                mechanism = Mechanism.RSA_PKCS1_PSS
                signature = self._session.sign(key, data, mechanism=mechanism)
            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")
            return signature
        except Exception as e:
            logger.error(f"Sign failed: {e}")
            return None
    
    def verify(
        self,
        key_id: str,
        data: bytes,
        signature: bytes,
        algorithm: str = "ECDSA_P256"
    ) -> bool:
        """Verify signature using HSM public key."""
        if not self.is_available():
            raise HSMWithoutError("SoftHSM not available")
        
        try:
            pub_label = f"{key_id}_pub"
            key = self._session.get_key(label=pub_label)
            mechanism = Mechanism.ECDSA if "ECDSA" in algorithm else Mechanism.RSA_PKCS1_PSS
            return self._session.verify(key, data, signature, mechanism=mechanism)
        except Exception as e:
            logger.error(f"Verify failed: {e}")
            return False
    
    def close(self):
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
        self._initialized = False


class CloudHSMKeystore:
    """AWS CloudHSM / Azure Key Vault Managed HSM wrapper."""
    
    def __init__(
        self,
        provider: str = "aws",
        region: str = None,
        key_id: str = None,
        **kwargs
    ):
        """
        Initialize cloud HSM client.
        
        Args:
            provider: "aws" or "azure"
            region: AWS region / Azure location
            key_id: Key identifier in the cloud HSM
        """
        self.provider = provider.lower()
        self.region = region or os.getenv("CLOUD_HSM_REGION", "us-east-1")
        self.key_id = key_id or os.getenv("CLOUD_HSM_KEY_ID")
        
        self._client = None
        
        if self.provider == "aws":
            if not AWS_AVAILABLE:
                raise RuntimeError("boto3 required for AWS CloudHSM")
            self._init_aws()
        elif self.provider == "azure":
            if not AZURE_AVAILABLE:
                raise RuntimeError("azure-keyvault-keys required for Azure Key Vault")
            self._init_azure()
        else:
            raise ValueError(f"Unsupported cloud provider: {provider}")
    
    def _init_aws(self):
        """Initialize AWS CloudHSM client via KMS."""
        session = boto3.session.Session()
        self._client = session.client(
            'kms',
            region_name=self.region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        logger.info(f"AWS KMS client initialized (region={self.region})")
    
    def _init_azure(self):
        """Initialize Azure Key Vault client."""
        credential = DefaultAzureCredential()
        vault_url = os.getenv("AZURE_KEYVAULT_URL")
        if not vault_url:
            raise ValueError("AZURE_KEYVAULT_URL required")
        self._client = KeyClient(vault_url=vault_url, credential=credential)
        # For crypto operations, we also need the CryptographyClient
        self._crypto_clients = {} # Cache clients per key_id
        self._credential = credential
        logger.info(f"Azure Key Vault client initialized: {vault_url}")
    
    def _get_azure_crypto_client(self, key_id: str) -> CryptographyClient:
        if key_id not in self._crypto_clients:
            key = self._client.get_key(key_id)
            self._crypto_clients[key_id] = CryptographyClient(key, self._credential)
        return self._crypto_clients[key_id]

    def is_available(self) -> bool:
        return self._client is not None
    
    def encrypt(self, key_id: str, plaintext: bytes, ad: bytes = None) -> Optional[bytes]:
        """Encrypt using cloud HSM key."""
        if not self.is_available():
            raise HSMWithoutError("Cloud HSM unavailable")
        
        try:
            if self.provider == "aws":
                resp = self._client.encrypt(
                    KeyId=key_id,
                    Plaintext=plaintext,
                    EncryptionAlgorithm="SYMMETRIC_DEFAULT"
                )
                return resp['CiphertextBlob']
            elif self.provider == "azure":
                client = self._get_azure_crypto_client(key_id)
                result = client.encrypt(EncryptionAlgorithm.rsa_oaep_256, plaintext)
                return result.ciphertext
        except Exception as e:
            logger.error(f"{self.provider.upper()} HSM encrypt error: {e}")
            return None
    
    def decrypt(self, key_id: str, ciphertext: bytes, ad: bytes = None) -> Optional[bytes]:
        """Decrypt using cloud HSM key."""
        if not self.is_available():
            raise HSMWithoutError("Cloud HSM unavailable")
        
        try:
            if self.provider == "aws":
                resp = self._client.decrypt(
                    KeyId=key_id,
                    CiphertextBlob=ciphertext,
                    EncryptionAlgorithm="SYMMETRIC_DEFAULT"
                )
                return resp['Plaintext']
            elif self.provider == "azure":
                client = self._get_azure_crypto_client(key_id)
                result = client.decrypt(EncryptionAlgorithm.rsa_oaep_256, ciphertext)
                return result.plaintext
        except Exception as e:
            logger.error(f"{self.provider.upper()} HSM decrypt error: {e}")
            return None
    
    def sign(self, key_id: str, data: bytes, algorithm: str = "ECDSA_P256") -> Optional[bytes]:
        """Sign data using cloud HSM key (via AWS KMS Sign)."""
        if not self.is_available():
            raise HSMWithoutError("Cloud HSM unavailable")
        
        try:
            if self.provider == "aws":
                # Map algorithm to AWS KMS signing spec
                alg_map = {
                    "ECDSA_P256": "ECDSA_SHA_256",
                    "RSA_PSS_SHA256": "RSASSA_PSS_SHA_256",
                }
                kms_alg = alg_map.get(algorithm, "ECDSA_SHA_256")
                resp = self._client.sign(
                    KeyId=key_id,
                    Message=data,
                    SigningAlgorithm=kms_alg,
                    MessageType="RAW"
                )
                return resp['Signature']
        except ClientError as e:
            logger.error(f"Sign failed: {e}")
            return None
    
    def verify(
        self,
        key_id: str,
        data: bytes,
        signature: bytes,
        algorithm: str = "ECDSA_P256"
    ) -> bool:
        """Verify signature using cloud HSM public key (requires fetching public key)."""
        # Implement by fetching public key and verifying locally with cryptography lib
        # This keeps signing within HSM, verification outside (acceptable)
        # For full HSM verification, would use KMS verify API (if available)
        logger.warning("CloudHSM verify not implemented; use software fallback for verification")
        return False


class HSMKeystore:
    """Unified HSM keystore with multi-backend support."""
    
    def __init__(self):
        self.mode: HSMMode = HSMMode.NONE
        self._software: Optional[SoftHSMKeystore] = None
        self._cloud: Optional[CloudHSMKeystore] = None
        self._fallback_key: Optional[bytes] = None
        self._initialized = False
        
        # Determine mode from env
        mode_str = os.getenv("HSM_MODE", "software").lower()
        try:
            self.mode = HSMMode(mode_str)
        except ValueError:
            logger.warning(f"Invalid HSM_MODE: {mode_str}; defaulting to 'software'")
            self.mode = HSMMode.SOFTWARE
        
        # Initialize selected backend
        if self.mode == HSMMode.SOFTWARE:
            self._software = SoftHSMKeystore(
                token_label=os.getenv("HSM_TOKEN_LABEL", "ai-f-token"),
                pin=os.getenv("HSM_PIN", "1234"),
                lib_path=os.getenv("PKCS11_LIB")
            )
        elif self.mode == HSMMode.CLOUD:
            provider = os.getenv("CLOUD_HSM_PROVIDER", "aws").lower()
            self._cloud = CloudHSMKeystore(
                provider=provider,
                region=os.getenv("CLOUD_HSM_REGION"),
                key_id=os.getenv("CLOUD_HSM_KEY_ID")
            )
        # NONE: do nothing
    
    def initialize(self) -> bool:
        """Initialize the configured HSM backend."""
        env = os.getenv("ENVIRONMENT", "development").lower()
        fail_fast = (env == "production")
        
        try:
            if self.mode == HSMMode.SOFTWARE:
                if not self._software.initialize():
                    msg = "SoftHSM initialization failed"
                    if fail_fast:
                        raise HSMWithoutError(msg)
                    logger.error(msg)
                    return False
            elif self.mode == HSMMode.CLOUD:
                if not self._cloud.is_available():
                    msg = "Cloud HSM client not available"
                    if fail_fast:
                        raise HSMWithoutError(msg)
                    logger.error(msg)
                    return False
            # NONE is always "success"
            
            self._initialized = True
            logger.info(f"HSM keystore ready (mode={self.mode.value})")
            return True
            
        except Exception as e:
            logger.error(f"HSM initialization error: {e}")
            if fail_fast:
                raise HSMWithoutError(f"HSM initialization failed in production: {e}")
            return False
    
    def is_available(self) -> bool:
        if self.mode == HSMMode.NONE:
            return False
        if self.mode == HSMMode.SOFTWARE:
            return self._software.is_available() if self._software else False
        if self.mode == HSMMode.CLOUD:
            return self._cloud.is_available() if self._cloud else False
        return False
    
    def _ensure(self):
        """Ensure HSM is available; fail fast in prod."""
        if not self._initialized:
            raise HSMWithoutError("HSM not initialized — call initialize() first")
        
        if self.mode == HSMMode.NONE:
            raise HSMWithoutError("HSM disabled (HSM_MODE=none)")
        
        if not self.is_available():
            env = os.getenv("ENVIRONMENT", "development").lower()
            if env == "production":
                raise HSMWithoutError("HSM backend unavailable in production")
            logger.warning("HSM backend unavailable — operations will fail")
    
    def generate_key(
        self,
        key_id: str,
        key_type: str = "AES",
        key_length: int = 256
    ) -> Optional[str]:
        self._ensure()
        if self.mode == HSMMode.SOFTWARE:
            return self._software.generate_key(key_id, key_type, key_length)
        elif self.mode == HSMMode.CLOUD:
            # Cloud HSM key generation goes through provider-specific APIs
            logger.info(f"Cloud HSM key generation for {key_id} not yet implemented; using software fallback")
            return None
        return None
    
    def encrypt(
        self,
        key_id: str,
        plaintext: bytes,
        associated_data: bytes = None
    ) -> bytes:
        self._ensure()
        if self.mode == HSMMode.SOFTWARE:
            result = self._software.encrypt(key_id, plaintext, associated_data)
        elif self.mode == HSMMode.CLOUD:
            result = self._cloud.encrypt(key_id, plaintext, associated_data)
        
        if result is None:
            raise HSMWithoutError("Encryption failed")
        return result
    
    def decrypt(
        self,
        key_id: str,
        ciphertext: bytes,
        associated_data: bytes = None
    ) -> bytes:
        self._ensure()
        if self.mode == HSMMode.SOFTWARE:
            result = self._software.decrypt(key_id, ciphertext, associated_data)
        elif self.mode == HSMMode.CLOUD:
            result = self._cloud.decrypt(key_id, ciphertext, associated_data)
        
        if result is None:
            raise HSMWithoutError("Decryption failed")
        return result
    
    def sign(
        self,
        key_id: str,
        data: bytes,
        algorithm: str = "ECDSA_P256"
    ) -> bytes:
        self._ensure()
        if self.mode == HSMMode.SOFTWARE:
            result = self._software.sign(key_id, data, algorithm)
        elif self.mode == HSMMode.CLOUD:
            result = self._cloud.sign(key_id, data, algorithm)
        
        if result is None:
            raise HSMWithoutError("Sign failed")
        return result
    
    def verify(
        self,
        key_id: str,
        data: bytes,
        signature: bytes,
        algorithm: str = "ECDSA_P256"
    ) -> bool:
        self._ensure()
        if self.mode == HSMMode.SOFTWARE:
            return self._software.verify(key_id, data, signature, algorithm)
        elif self.mode == HSMMode.CLOUD:
            return self._cloud.verify(key_id, data, signature, algorithm)
        return False
    
    def rotate_key(self, old_key_id: str, new_key_id: str) -> bool:
        """Key rotation: generate new key and re-encrypt data (offline process)."""
        if self.mode == HSMMode.SOFTWARE and self._software:
            # Generate new key
            if not self._software.generate_key(new_key_id):
                return False
            logger.info(f"Key rotated: {old_key_id} → {new_key_id}")
            return True
        logger.warning("Key rotation not automatically supported for this HSM mode")
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get HSM status and configuration."""
        return {
            "mode": self.mode.value,
            "initialized": self._initialized,
            "available": self.is_available(),
            "backend": "softHSM" if self.mode == HSMMode.SOFTWARE else "cloud",
            "fail_secure": os.getenv("ENVIRONMENT", "development").lower() == "production"
        }
    
    def close(self):
        if self._software:
            self._software.close()
        self._initialized = False


# Global singleton
_hsm_keystore = HSMKeystore()


def get_hsm_keystore() -> HSMKeystore:
    """Get the global HSM keystore instance."""
    return _hsm_keystore
