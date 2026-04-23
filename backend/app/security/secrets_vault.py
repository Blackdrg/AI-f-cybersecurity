import os
import json
import logging
from typing import Optional
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

logger = logging.getLogger("secrets-vault")

class SecretsVault:
    """
    Unified interface for enterprise secrets management.
    Supports AWS Secrets Manager, HashiCorp Vault (stubs), and local .env fallback.
    """
    def __init__(self):
        self.provider = os.getenv("SECRETS_PROVIDER", "env") # 'aws', 'vault', 'env'
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self._client = None
        
        if self.provider == "aws" and BOTO3_AVAILABLE:
            self._client = boto3.client("secretsmanager", region_name=self.region)

    def get_secret(self, secret_name: str) -> Optional[str]:
        """Retrieves a secret by name from the configured provider."""
        if self.provider == "env":
            return os.getenv(secret_name)
            
        if self.provider == "aws" and self._client:
            try:
                response = self._client.get_secret_value(SecretId=secret_name)
                if 'SecretString' in response:
                    return response['SecretString']
                return response['SecretBinary']
            except Exception as e:
                logger.error(f"Failed to fetch AWS secret {secret_name}: {e}")
                return os.getenv(secret_name) # Fallback to ENV
                
        return os.getenv(secret_name)

    def get_encryption_key(self) -> str:
        """Helper for biometric encryption key."""
        return self.get_secret("ENCRYPTION_KEY") or "fallback-poc-key-32-bytes-long!!!"

# Global singleton
vault = SecretsVault()
