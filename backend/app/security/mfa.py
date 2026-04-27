"""
MFA Service
TOTP-based multi-factor authentication with backup codes
"""
import os
import base64
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import secrets
import hashlib
import hmac
import pyotp
from sqlalchemy import text
from ..db.db_client import get_db
from ..security import create_token
import logging

logger = logging.getLogger(__name__)

class MFAService:
    """Manages TOTP-based MFA enrollment, verification, and backup codes"""
    
    def __init__(self):
        self.totp_issuer = os.getenv("MFA_ISSUER", "AI-f Platform")
    
    async def enable_mfa_for_user(self, user_id: str) -> Tuple[str, List[str]]:
        """
        Generate MFA secret and backup codes for a user.
        
        Returns:
            (totp_secret, backup_codes)
        """
        # Generate TOTP secret
        totp_secret = pyotp.random_base32()
        
        # Generate 10 backup codes (each 12 chars, stored hashed)
        backup_codes = []
        hashed_codes = []
        for _ in range(10):
            code = secrets.token_urlsafe(9)[:12]
            backup_codes.append(code)
            hashed_codes.append(self._hash_backup_code(code))
        
        db = await get_db()
        async with db.pool.acquire() as conn:
            # Store secret and hashed backup codes
            await conn.execute("""
                INSERT INTO mfa_secrets 
                (user_id, secret, backup_codes_hash, enabled, created_at)
                VALUES ($1, $2, $3, false, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    secret = EXCLUDED.secret,
                    backup_codes_hash = EXCLUDED.backup_codes_hash,
                    enabled = false,
                    updated_at = NOW()
            """, user_id, totp_secret, json.dumps(hashed_codes))
        
        return totp_secret, backup_codes
    
    def generate_totp_qr_code_data(self, secret: str, user_id: str, user_email: str = None) -> str:
        """Generate otpauth URI for QR code"""
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_id,
            issuer_name=self.totp_issuer
        )
        return provisioning_uri
    
    async def verify_totp_code(self, user_id: str, code: str) -> bool:
        """Verify a TOTP code against stored secret"""
        db = await get_db()
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT secret FROM mfa_secrets WHERE user_id = $1 AND enabled = true",
                user_id
            )
            if not row:
                return False
            
            secret = row['secret']
            totp = pyotp.TOTP(secret)
            
            # Check current and previous window (for clock skew)
            valid = totp.verify(code, valid_window=1)
            if valid:
                # Update last_used timestamp
                await conn.execute(
                    "UPDATE mfa_secrets SET last_used_at = NOW() WHERE user_id = $1",
                    user_id
                )
            return valid
    
    async def verify_backup_code(self, user_id: str, code: str) -> Tuple[bool, str]:
        """
        Verify a backup code and consume it.
        
        Returns:
            (is_valid, message)
        """
        if not code or len(code) < 8:
            return False, "Invalid backup code format"
        
        code_hash = self._hash_backup_code(code)
        
        db = await get_db()
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT backup_codes_hash, backup_codes_used FROM mfa_secrets WHERE user_id = $1 AND enabled = true",
                user_id
            )
            if not row:
                return False, "MFA not enabled for this user"
            
            stored_hashes = row['backup_codes_hash']
            used_codes = row['backup_codes_used'] or []
            
            # Check if this code was already used
            if code in used_codes:
                return False, "Backup code already used"
            
            # Verify code matches a hash
            hashes_list = json.loads(stored_hashes) if stored_hashes else []
            for idx, hashed in enumerate(hashes_list):
                if self._verify_backup_code_hash(code, hashed):
                    # Mark code as used
                    used_codes.append(code)
                    await conn.execute(
                        "UPDATE mfa_secrets SET backup_codes_used = $1 WHERE user_id = $2",
                        json.dumps(used_codes), user_id
                    )
                    return True, "Backup code accepted"
            
            return False, "Invalid backup code"
    
    async def enable_mfa_after_verification(self, user_id: str) -> bool:
        """Mark MFA as enabled after initial TOTP verification"""
        db = await get_db()
        async with db.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE mfa_secrets SET enabled = true, enabled_at = NOW() WHERE user_id = $1",
                user_id
            )
        return result == "UPDATE 1"
    
    async def disable_mfa(self, user_id: str, password: str) -> bool:
        """Disable MFA (requires password confirmation)"""
        db = await get_db()
        async with db.pool.acquire() as conn:
            # Verify password
            user = await conn.fetchrow(
                "SELECT hashed_password FROM users WHERE user_id = $1",
                user_id
            )
            if not user or not self._verify_password(password, user['hashed_password']):
                return False
            
            # Disable MFA
            await conn.execute(
                "UPDATE mfa_secrets SET enabled = false WHERE user_id = $1",
                user_id
            )
            return True
    
    async def is_mfa_enabled(self, user_id: str) -> bool:
        """Check if user has MFA enabled"""
        db = await get_db()
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT enabled FROM mfa_secrets WHERE user_id = $1 AND enabled = true",
                user_id
            )
            return row is not None
    
    async def get_backup_codes_count(self, user_id: str) -> int:
        """Get count of remaining unused backup codes"""
        db = await get_db()
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT backup_codes_used FROM mfa_secrets WHERE user_id = $1",
                user_id
            )
            if not row:
                return 0
            used = row['backup_codes_used'] or []
            return 10 - len(used)
    
    def _hash_backup_code(self, code: str) -> str:
        """Hash backup code for storage (SHA-256 with server-side salt)"""
        salt = os.getenv("BACKUP_CODE_SALT", "default-salt-change-me")
        return hashlib.sha256(f"{code}{salt}".encode()).hexdigest()
    
    def _verify_backup_code_hash(self, code: str, hashed: str) -> bool:
        """Verify a backup code against its hash"""
        return self._hash_backup_code(code) == hashed
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify bcrypt password"""
        import bcrypt
        return bcrypt.checkpw(password.encode(), hashed.encode())


# Global service
mfa_service = MFAService()
