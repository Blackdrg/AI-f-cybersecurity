"""
OAuth2 / SSO Integration
"""
import os
import httpx
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
import logging
import json
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

import time
from .anomaly_detector import anomaly_detector
from ..db.db_client import get_db

logger = logging.getLogger(__name__)

class OAuthProviderBase:
    """Base class with anomaly detection and rotation support"""
    
    async def detect_anomaly(self, request: Request, user_id: str) -> bool:
        """Check for suspicious login activity."""
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "unknown")
        
        is_anomaly = await anomaly_detector.check_login_anomaly(
            user_id=user_id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        return is_anomaly

    async def rotate_tokens(self, user_id: str, old_refresh_token: str) -> Dict[str, Any]:
        """Implement automated token rotation for security."""
        # Invalidate old refresh token and issue new pair
        db = get_db()
        await db.execute(
            "UPDATE user_sessions SET is_revoked = true WHERE refresh_token = $1",
            old_refresh_token
        )
        # Token rotation logic (issuing new tokens) would follow
        return {"status": "rotated"}

class AzureADProvider(OAuthProviderBase):
    """Azure Active Directory OAuth2 provider"""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.token_url = f"{self.authority}/oauth2/v2.0/token"
        self.authorize_url = f"{self.authority}/oauth2/v2.0/authorize"
        self.jwks_uri = f"{self.authority}/discovery/v2.0/keys"
    
    def get_authorization_url(self, redirect_uri: str, state: str = None, 
                               scopes: list = None) -> tuple[str, str]:
        """Generate OAuth2 authorization URL"""
        from urllib.parse import urlencode
        scopes = scopes or ["openid", "profile", "email", "User.Read"]
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(scopes),
            "state": state or "",
        }
        url = f"{self.authorize_url}?{urlencode(params)}"
        return url, state
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access token and ID token"""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }
            response = await client.post(self.token_url, data=data)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code")
            return response.json()
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            response = await client.post(self.token_url, data=data)
            response.raise_for_status()
            return response.json()
    
    async def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        """Validate and decode ID token (JWT)"""
        import jwt
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        import json
        
        # Get JWKS
        async with httpx.AsyncClient() as client:
            jwks_response = await client.get(self.jwks_uri)
            jwks = jwks_response.json()
        
        # Decode header to get key ID
        header = jwt.get_unverified_header(id_token)
        kid = header.get('kid')
        
        # Find matching key
        key = next((k for k in jwks['keys'] if k['kid'] == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Unable to find matching key")
        
        # Convert JWK to PEM
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        
        # Verify token
        try:
            payload = jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"https://sts.windows.net/{self.tenant_id}/"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


class GoogleOAuthProvider(OAuthProviderBase):
    """Google OAuth2 provider"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.jwks_uri = "https://www.googleapis.com/oauth2/v3/certs"
    
    def get_authorization_url(self, redirect_uri: str, state: str = None,
                               scopes: list = None) -> tuple[str, str]:
        from urllib.parse import urlencode
        scopes = scopes or ["openid", "profile", "email"]
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "state": state or "",
        }
        url = f"{self.authorize_url}?{urlencode(params)}"
        return url, state
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }
            response = await client.post(self.token_url, data=data)
            response.raise_for_status()
            return response.json()
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            response = await client.post(self.token_url, data=data)
            response.raise_for_status()
            return response.json()
    
    async def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        import jwt
        async with httpx.AsyncClient() as client:
            jwks = (await client.get(self.jwks_uri)).json()
        
        header = jwt.get_unverified_header(id_token)
        key = next((k for k in jwks['keys'] if k['kid'] == header.get('kid')), None)
        if not key:
            raise HTTPException(status_code=401, detail="Key not found")
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        return jwt.decode(id_token, public_key, algorithms=["RS256"], audience=self.client_id)


def get_oauth_provider(provider: str) -> Any:
    """Factory to get OAuth provider by name"""
    if provider == "azure_ad":
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")
        if not all([tenant_id, client_id, client_secret]):
            raise ValueError("Azure AD credentials not configured")
        return AzureADProvider(tenant_id, client_id, client_secret)
    elif provider == "google":
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not all([client_id, client_secret]):
            raise ValueError("Google OAuth credentials not configured")
        return GoogleOAuthProvider(client_id, client_secret)
    else:
        raise ValueError(f"Unsupported OAuth provider: {provider}")
