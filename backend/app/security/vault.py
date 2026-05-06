"""HashiCorp Vault / AWS KMS Integration for Secrets."""
import os
import hvac
import boto3
from typing import Optional
from cryptography.fernet import Fernet
import hashlib
import base64
import logging

logger = logging.getLogger(__name__)

class VaultSecretsManager:
    def __init__(self):
        self.vault_url = os.getenv("VAULT_ADDR", "http://vault:8200")
        self.kms_region = os.getenv("AWS_REGION", "us-east-1")
        self.kms_key_id = os.getenv("KMS_KEY_ID", "alias/ai-f-master-key")
        self.client = None
        self.kms = boto3.client("kms", region_name=self.kms_region)
        self.encryption_key = self._get_encryption_key()
    
    def _get_encryption_key(self) -> bytes:
        """Fetch master encryption key from KMS/Vault."""
        try:
            # AWS KMS
            response = self.kms.generate_data_key(
                KeyId=self.kms_key_id,
                KeySpec="AES_256"
            )
            return response["Plaintext"]
        except:
            # Fallback env - use valid Fernet key (32 url-safe base64-encoded bytes)
            return base64.urlsafe_b64encode(
                hashlib.sha256(os.getenv("ENCRYPTION_KEY", "fallback-key-32bytes-for-dev!!!").encode()).digest()
            )[:43] + b'='  # Pad to 44 chars for Fernet
    
    def get_secret(self, path: str, field: str = "data") -> Optional[str]:
        """Retrieve secret from Vault."""
        try:
            if not self.client:
                self.client = hvac.Client(url=self.vault_url, token=os.getenv("VAULT_TOKEN"))
            
            secret = self.client.secrets.kv.v2.read_secret_version(path=path)
            return secret["data"][field]["value"]
        except Exception as e:
            logger.error(f"Vault secret {path} error: {e}")
            return None
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt with master key."""
        f = Fernet(self.encryption_key)
        return f.encrypt(data)
    
    def decrypt_data(self, encrypted: bytes) -> bytes:
        """Decrypt with master key."""
        f = Fernet(self.encryption_key)
        return f.decrypt(encrypted)

# Global instance
vault_manager = VaultSecretsManager()

# Usage
# stripe_key = vault_manager.get_secret("secret/ai-f/stripe", "key")
# encrypted_emb = vault_manager.encrypt_data(embedding.tobytes())
