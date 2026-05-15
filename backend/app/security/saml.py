import os
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from fastapi import Request, HTTPException
import logging

logger = logging.getLogger(__name__)

class SAMLManager:
    def __init__(self):
        self.saml_path = os.path.join(os.getcwd(), 'certs', 'saml')
        
    def _prepare_saml_request(self, request: Request):
        url_data = {
            'https': 'on' if request.url.scheme == 'https' else 'off',
            'http_host': request.headers.get('host'),
            'script_name': request.url.path,
            'get_data': dict(request.query_params),
            'post_data': {} # Will be filled in the calling method if needed
        }
        return url_data

    def get_auth(self, request: Request, custom_settings=None):
        req = self._prepare_saml_request(request)
        # In a real enterprise app, settings would be fetched per-org from DB
        settings = custom_settings or self._load_settings()
        return OneLogin_Saml2_Auth(req, settings)

    def _load_settings(self):
        """Load default SAML settings (usually for the app's own metadata)."""
        # This is a placeholder for real settings logic
        return {
            "strict": True,
            "debug": True,
            "sp": {
                "entityId": os.getenv("SAML_SP_ENTITY_ID", "https://ai-f.com/metadata"),
                "assertionConsumerService": {
                    "url": os.getenv("SAML_SP_ACS_URL", "https://ai-f.com/api/auth/saml/acs"),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": os.getenv("SAML_SP_SLS_URL", "https://ai-f.com/api/auth/saml/sls"),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": os.getenv("SAML_SP_CERT", ""),
                "privateKey": os.getenv("SAML_SP_KEY", "")
            },
            "idp": {
                "entityId": os.getenv("SAML_IDP_ENTITY_ID", ""),
                "singleSignOnService": {
                    "url": os.getenv("SAML_IDP_SSO_URL", ""),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "singleLogoutService": {
                    "url": os.getenv("SAML_IDP_SLS_URL", ""),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": os.getenv("SAML_IDP_CERT", "")
            }
        }

saml_manager = SAMLManager()
