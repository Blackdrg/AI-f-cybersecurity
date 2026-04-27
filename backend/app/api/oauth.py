"""
OAuth2 Authentication Routes
Handles SSO login flows for Azure AD, Google, etc.
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from typing import Optional
from ..security.oauth import get_oauth_provider
from ..security import create_token
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/auth/oauth/login/{provider}")
async def oauth_login(provider: str, redirect_uri: str = None):
    """
    Initiate OAuth2 login flow.
    
    Redirects user to provider's authorization page.
    """
    try:
        oauth = get_oauth_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Determine redirect URI for callback
    if not redirect_uri:
        redirect_uri = os.getenv("FRONTEND_URL", "http://localhost:3000") + f"/auth/{provider}/callback"
    
    # Generate state (CSRF protection)
    import secrets
    state = secrets.token_urlsafe(16)
    
    # Store state in session/cookie (simplified here via query param)
    auth_url, _ = oauth.get_authorization_url(redirect_uri, state=state)
    
    return RedirectResponse(auth_url)


@router.get("/auth/oauth/callback/{provider}")
async def oauth_callback(provider: str, request: Request):
    """
    OAuth2 callback endpoint.
    Provider redirects here with authorization code.
    """
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")
    
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    try:
        oauth = get_oauth_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Exchange code for tokens
    redirect_uri = os.getenv("FRONTEND_URL", "http://localhost:3000") + f"/auth/{provider}/callback"
    tokens = await oauth.exchange_code_for_tokens(code, redirect_uri)
    
    # Validate ID token
    id_token = tokens.get('id_token')
    if not id_token:
        raise HTTPException(status_code=401, detail="No ID token returned")
    
    user_info = await oauth.validate_id_token(id_token)
    
    # Extract user info
    if provider == "azure_ad":
        user_id = user_info.get('oid') or user_info.get('sub')
        email = user_info.get('email') or user_info.get('preferred_username')
        name = user_info.get('name')
    elif provider == "google":
        user_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name')
    else:
        user_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name')
    
    if not user_id or not email:
        raise HTTPException(status_code=400, detail="Insufficient user info from OAuth provider")
    
    # Find or create user in our system
    from ..db.db_client import get_db
    db = await get_db()
    user = await db.get_user_by_email(email)
    
    if not user:
        # Create new user via internal method
        user_id = await db.create_user(
            user_id=f"oauth_{provider}_{user_id}",
            email=email,
            name=name or email.split('@')[0],
            auth_provider=provider
        )
    else:
        user_id = user['user_id']
    
    # Issue our platform's JWT token
    token = create_token(user_id=user_id, role='user')
    
    # Redirect to frontend with token
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend_url}/auth/success?token={token}")
