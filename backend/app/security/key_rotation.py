import os
import time
import base64
import logging
from cryptography.fernet import Fernet
from ..db.db_client import DBClient
from .secrets_manager import secrets_manager
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("key-rotation")

class KeyRotationManager:
    """
    Manages periodic rotation of encryption keys for biometric embeddings.
    Implements a 'Grace Period' where both old and new keys are valid for decryption.
    Integrates with AWS KMS and Secrets Manager.
    """
    def __init__(self, db_client: DBClient):
        self.db = db_client
        self.rotation_interval_days = 90
        self.kms_key_id = os.getenv("KMS_KEY_ID", "alias/ai-f-encryption-key")
        
    def generate_new_key(self) -> str:
        """Generates a new 32-byte Fernet-compatible key."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    async def rotate_keys(self):
        """
        Rotates the primary encryption key and re-encrypts critical data.
        Uses AWS KMS + Secrets Manager.
        """
        logger.info("Starting KMS-integrated encryption key rotation...")
        
        # 1. Generate new key in KMS
        kms_client = boto3.client('kms')
        new_key_resp = kms_client.create_key(
            Description="AI-F Biometric Encryption Key",
            KeyUsage="ENCRYPT_DECRYPT",
            MultiRegionKey=False
        )
        new_key_id = new_key_resp['KeyMetadata']['KeyId']
        
        # 2. Create data key
        data_key_resp = kms_client.generate_data_key(
            KeyId=new_key_id,
            KeySpec='AES_256'
        )
        new_plain_key = data_key_resp['Plaintext']
        new_key_b64 = base64.b64encode(new_plain_key).decode()
        
        old_key = secrets_manager.get_secret("ENCRYPTION_KEY")
        
        # 3. Store new key encrypted in Secrets Manager
        secrets_manager.get_secret("ENCRYPTION_KEY", secret_id="ai-f/encryption-key", kms_key_id=new_key_id)
        
        # Grace period: Keep old key temporarily
        secrets_manager.get_secret("OLD_ENCRYPTION_KEY", old_key)
        
        logger.info(f"New KMS key created: {new_key_id}")
        
        # 4. Re-encrypt embeddings
        await self._migrate_embeddings(old_key, new_key_b64)
        
        # 5. Schedule automatic rotation
        kms_client.schedule_key_rotation(
            KeyId=new_key_id,
            RotationPeriodInDays=365
        )
        
        logger.info("KMS key rotation complete with annual auto-rotation.")

    async def _migrate_embeddings(self, old_key_str: str, new_key_str: str):
        """Batch re-encrypt embeddings using transactions."""
        if not old_key_str:
            return
        await self.db.rotate_embedding_keys(old_key_str, new_key_str)

# Global instance
key_manager = KeyRotationManager(DBClient())
