"""
SAML 2.0 Service Provider (SP) Integration.

Handles enterprise SSO flows with Identity Providers (IdP).
"""
import os
import logging
from typing import Dict, Any, Optional
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

class SAMLServiceProvider:
    """Manages SAML 2.0 authentication."""
    
    def __init__(self, settings_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize SAML SP with settings.
        
        If settings_dict is None, it will try to load from environment or default files.
        """
        self.settings_dict = settings_dict or self._load_default_settings()
    
    def _load_default_settings(self) -> Dict[str, Any]:
        """Load default SAML settings from environment variables."""
        base_url = os.getenv("APP_URL", "http://localhost:8000")
        
        return {
            "strict": os.getenv("SAML_STRICT", "True").lower() == "true",
            "debug": os.getenv("SAML_DEBUG", "False").lower() == "true",
            "sp": {
                "entityId": f"{base_url}/api/auth/saml/metadata",
                "assertionConsumerService": {
                    "url": f"{base_url}/api/auth/saml/callback",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": f"{base_url}/api/auth/saml/logout",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "x509cert": os.getenv("SAML_SP_CERT", ""),
                "privateKey": os.getenv("SAML_SP_KEY", ""),
            },
            "idp": {
                "entityId": os.getenv("SAML_IDP_ENTITY_ID", ""),
                "singleSignOnService": {
                    "url": os.getenv("SAML_IDP_SSO_URL", ""),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "singleLogoutService": {
                    "url": os.getenv("SAML_IDP_SLO_URL", ""),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": os.getenv("SAML_IDP_CERT", ""),
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": False,
                "logoutRequestSigned": False,
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantMessagesSigned": False,
                "wantAssertionsSigned": False,
                "wantAssertionsEncrypted": False,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
                "requestedAuthnContext": True,
                "requestedAuthnContextComparison": "exact",
                "metadataValidUntil": "",
                "metadataCacheDuration": "",
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256"
            }
        }

    async def prepare_saml_request(self, request: Request) -> Dict[str, Any]:
        """Prepare the request data structure required by python3-saml."""
        form_data = await request.form()
        
        return {
            "https": "on" if request.url.scheme == "https" else "off",
            "http_host": request.url.netloc,
            "script_name": request.url.path,
            "server_port": request.url.port or (443 if request.url.scheme == "https" else 80),
            "get_data": dict(request.query_params),
            "post_data": dict(form_data),
            "query_string": request.url.query
        }

    def init_auth(self, saml_req: Dict[str, Any]) -> OneLogin_Saml2_Auth:
        """Initialize OneLogin Saml2 Auth object."""
        return OneLogin_Saml2_Auth(saml_req, self.settings_dict)

    def get_metadata(self) -> str:
        """Generate SP metadata XML."""
        settings = OneLogin_Saml2_Settings(self.settings_dict)
        metadata = settings.get_sp_metadata()
        errors = settings.validate_metadata(metadata)
        
        if len(errors) == 0:
            return metadata
        else:
            raise HTTPException(status_code=500, detail=f"SAML Metadata error: {', '.join(errors)}")

saml_sp = SAMLServiceProvider()
