import os
try:
    import boto3
    BOTO3 = True
except:
    BOTO3 = False
try:
    from cryptography.hazmat.primitives import serialization
    CRYPTO = True
except:
    CRYPTO = False

# Re-export vault_manager from vault.py as 'vault' for backward compatibility
from .vault import vault_manager as vault
