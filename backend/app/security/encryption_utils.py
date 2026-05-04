import base64
from cryptography.fernet import Fernet
from .secrets_manager import secrets_manager
from typing import Optional

def get_encryption_key() -> Optional[str]:
    """Get current encryption key from secrets manager."""
    key = secrets_manager.get_secret("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("Encryption key not available")
    return key

def encrypt_embedding(embedding: list, key: Optional[str] = None) -> str:
    """Encrypt embedding for enclave transmission."""
    key_str = key or get_encryption_key()
    f = Fernet(key_str.encode())
    emb_bytes = str(embedding).encode()
    encrypted = f.encrypt(emb_bytes)
    return base64.b64encode(encrypted).decode()

def decrypt_embedding(encrypted_b64: str, key: Optional[str] = None) -> list:
    """Decrypt embedding from enclave."""
    key_str = key or get_encryption_key()
    f = Fernet(key_str.encode())
    encrypted = base64.b64decode(encrypted_b64)
    decrypted = f.decrypt(encrypted)
    # Parse back to list (simple eval for demo; use safe JSON in prod)
    return eval(decrypted.decode())

def encrypt_request(request_dict: dict, field: str = 'embedding') -> dict:
    """Encrypt embedding field in enclave request."""
    if field in request_dict:
        request_dict[field] = encrypt_embedding(request_dict[field])
    return request_dict

def decrypt_response(response: dict, field: str = 'result') -> dict:
    """Decrypt result field from enclave response."""
    if field in response and isinstance(response[field], dict):
        for k, v in response[field].items():
            if isinstance(v, str):
                try:
                    response[field][k] = decrypt_embedding(v)
                except:
                    pass  # Not encrypted
    return response

