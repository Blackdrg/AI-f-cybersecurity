"""
WebAuthn (FIDO2) Authentication Service.

Supports hardware MFA (YubiKey, Titan) and Passkeys.
"""
import os
import base64
import logging
from typing import Dict, Any, Optional, List
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
    base64url_to_bytes,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    AuthenticatorAttachment,
    UserVerificationRequirement,
    RegistrationCredential,
    AuthenticationCredential,
)
from ..db.db_client import get_db

logger = logging.getLogger(__name__)

class WebAuthnService:
    """Manages WebAuthn registration and authentication."""
    
    def __init__(self):
        self.rp_id = os.getenv("WEBAUTHN_RP_ID", "localhost")
        self.rp_name = os.getenv("WEBAUTHN_RP_NAME", "AI-f Platform")
        self.origin = os.getenv("WEBAUTHN_ORIGIN", "http://localhost:3000")
    
    def get_registration_options(self, user_id: str, user_name: str, 
                                 existing_credentials: List[Dict[str, Any]] = None) -> str:
        """Generate options for registering a new hardware key."""
        exclude_credentials = []
        if existing_credentials:
            for cred in existing_credentials:
                exclude_credentials.append({
                    "id": base64url_to_bytes(cred["credential_id"]),
                    "type": "public-key"
                })
        
        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=user_id,
            user_name=user_name,
            attestation=AttestationConveyancePreference.DIRECT,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            exclude_credentials=exclude_credentials,
        )
        return options_to_json(options)

    async def verify_registration(self, user_id: str, challenge: str, response_json: Any) -> Dict[str, Any]:
        """Verify the registration response from the browser."""
        registration_verification = verify_registration_response(
            credential=RegistrationCredential.parse_raw(response_json),
            expected_challenge=base64url_to_bytes(challenge),
            expected_origin=self.origin,
            expected_rp_id=self.rp_id,
        )
        
        # Extract data for storage
        credential_id = base64.urlsafe_b64encode(registration_verification.credential_id).decode().replace("=", "")
        public_key = base64.urlsafe_b64encode(registration_verification.credential_public_key).decode().replace("=", "")
        
        # Store in DB
        db = get_db()
        await db.execute("""
            INSERT INTO user_credentials (user_id, credential_id, public_key, sign_count, created_at)
            VALUES ($1, $2, $3, $4, NOW())
        """, user_id, credential_id, public_key, registration_verification.sign_count)
        
        return {
            "credential_id": credential_id,
            "success": True
        }

    def get_authentication_options(self, existing_credentials: List[Dict[str, Any]]) -> str:
        """Generate options for authenticating with a hardware key."""
        allow_credentials = []
        for cred in existing_credentials:
            allow_credentials.append({
                "id": base64url_to_bytes(cred["credential_id"]),
                "type": "public-key"
            })
            
        options = generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        return options_to_json(options)

    async def verify_authentication(self, challenge: str, response_json: Any, 
                                   credential_data: Dict[str, Any]) -> bool:
        """Verify the authentication response from the browser."""
        authentication_verification = verify_authentication_response(
            credential=AuthenticationCredential.parse_raw(response_json),
            expected_challenge=base64url_to_bytes(challenge),
            expected_origin=self.origin,
            expected_rp_id=self.rp_id,
            credential_public_key=base64url_to_bytes(credential_data["public_key"]),
            credential_current_sign_count=credential_data["sign_count"],
        )
        
        # Update sign count in DB
        db = get_db()
        await db.execute("""
            UPDATE user_credentials SET sign_count = $1, last_used_at = NOW()
            WHERE credential_id = $2
        """, authentication_verification.new_sign_count, credential_data["credential_id"])
        
        return True

webauthn_service = WebAuthnService()
