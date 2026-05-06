import os
import json
import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class SecretsManager:
    def __init__(self, backend: str = "auto"):
        self.backend = backend
        self.kms_client = None
        
        # Auto-detect backend
        if backend == "auto":
            if 'AWS_ACCESS_KEY_ID' in os.environ or 'AWS_PROFILE' in os.environ:
                self.backend = "aws"
            else:
                self.backend = "env"
        
        if self.backend == "aws":
            try:
                self.kms_client = boto3.client('kms', region_name=os.getenv('AWS_REGION', 'us-east-1'))
                logger.info("AWS KMS client initialized")
            except NoCredentialsError:
                logger.warning("AWS credentials not found, falling back to env vars")
                self.backend = "env"

    def get_secret(self, key: str, secret_id: str = None, kms_key_id: str = None) -> Optional[str]:
        """
        Retrieve secret with KMS integration.
        
        Args:
            key: Secret key name (e.g. 'ENCRYPTION_KEY')
            secret_id: AWS Secrets Manager ARN/name (if using AWS backend)
            kms_key_id: KMS key for decryption (if encrypted)
        """
        # Strict mode for production: No defaults for sensitive keys
        is_production = os.getenv("ENV", "development") == "production"
        sensitive_keys = ["JWT_SECRET", "DB_PASSWORD", "ENCRYPTION_KEY"]
        
        # 1. AWS Secrets Manager + KMS (priority)
        if self.backend == "aws":
            try:
                secret_id = secret_id or f"ai-f/{key.lower()}"
                kms_key_id = kms_key_id or os.getenv("KMS_KEY_ID")
                
                # Fetch from Secrets Manager
                sm_client = boto3.client('secretsmanager')
                response = sm_client.get_secret_value(SecretId=secret_id)
                
                secret_value = response['SecretString']
                if kms_key_id and response.get('SecretBinary'):
                    # Decrypt binary secret with KMS
                    encrypted = base64.b64decode(response['SecretBinary'])
                    decrypt_resp = self.kms_client.decrypt(
                        CiphertextBlob=encrypted,
                        KeyId=kms_key_id
                    )
                    secret_value = decrypt_resp['Plaintext'].decode('utf-8')
                
                logger.info(f"Retrieved secret '{key}' from AWS Secrets Manager")
                return secret_value
            except ClientError as e:
                logger.error(f"AWS Secrets Manager error for {key}: {e}")
        
        # 2. Environment fallback
        val = os.getenv(key)
        if val is not None:
            return val
        
        # 3. Production safety check
        if is_production and key in sensitive_keys:
            raise RuntimeError(f"CRITICAL: Missing production secret: {key}")
        
        # 4. Fallback for development
        if key in sensitive_keys and not val:
            import hashlib, base64
            if key == "JWT_SECRET":
                return "dev-jwt-secret-key-change-in-production"
            if key == "ENCRYPTION_KEY":
                fallback = hashlib.sha256(b"ai-f-dev-encryption-key").digest()
                return base64.urlsafe_b64encode(fallback).decode()
            if key == "DB_PASSWORD":
                return "dev-password"
        
        logger.warning(f"Secret '{key}' not found")
        return None

    def rotate_kms_key(self, key_id: str, alias: str):
        """Rotate KMS key and update Secrets Manager."""
        try:
            # Schedule key rotation (annual)
            self.kms_client.schedule_key_rotation(KeyId=key_id, RotationPeriodInDays=365)
            
            # Update alias
            self.kms_client.update_alias(AliasName=alias, TargetKeyId=key_id)
            logger.info(f"KMS key rotation scheduled for {key_id}")
        except ClientError as e:
            logger.error(f"KMS rotation failed: {e}")

# Global instance
secrets_manager = SecretsManager(backend="auto")

