import os
import logging
from typing import Optional
import json

logger = logging.getLogger(__name__)

class SecretsManager:
    """
    Enterprise-grade secrets manager supporting multiple backends.
    Supports HashiCorp Vault, AWS Secrets Manager, and Environment Variables.
    """
    def __init__(self, backend: str = "env"):
        self.backend = os.getenv("SECRETS_BACKEND", backend)
        self.vault_url = os.getenv("VAULT_URL")
        self.vault_token = os.getenv("VAULT_TOKEN")
        
        if self.backend == "vault" and not self.vault_url:
            logger.warning("Vault backend selected but VAULT_URL not set. Falling back to env.")
            self.backend = "env"

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if self.backend == "vault":
            return self._get_vault_secret(key, default)
        elif self.backend == "aws":
            return self._get_aws_secret(key, default)
        else:
            return os.getenv(key, default)

    def _get_vault_secret(self, key: str, default: Optional[str]) -> Optional[str]:
        # Implementation for HashiCorp Vault
        try:
            import hvac
            client = hvac.Client(url=self.vault_url, token=self.vault_token)
            read_response = client.secrets.kv.v2.read_secret_version(path='ai-f-secrets')
            return read_response['data']['data'].get(key, default)
        except ImportError:
            logger.error("hvac not installed. Fallback to env.")
            return os.getenv(key, default)
        except Exception as e:
            logger.error(f"Error fetching from Vault: {e}")
            return os.getenv(key, default)

    def _get_aws_secret(self, key: str, default: Optional[str]) -> Optional[str]:
        # Implementation for AWS Secrets Manager
        try:
            import boto3
            client = boto3.client('secretsmanager')
            response = client.get_secret_value(SecretId='ai-f/production')
            secrets = json.loads(response['SecretString'])
            return secrets.get(key, default)
        except ImportError:
            logger.error("boto3 not installed. Fallback to env.")
            return os.getenv(key, default)
        except Exception as e:
            logger.error(f"Error fetching from AWS Secrets Manager: {e}")
            return os.getenv(key, default)

secrets_manager = SecretsManager()
