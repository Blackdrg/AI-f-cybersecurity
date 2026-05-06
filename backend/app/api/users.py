from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import JSONResponse
from typing import List
from ..schemas import UserCreate, UserResponse
from ..db.db_client import get_db
from ..security import get_current_user, create_token, set_auth_cookie, clear_auth_cookie
import uuid
import os
from datetime import datetime

router = APIRouter()

# Production flag: Use httpOnly cookies for JWT (true XSS protection)
USE_HTTP_ONLY_COOKIE = os.getenv("USE_HTTP_ONLY_COOKIE", "false").lower() == "true"


@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Create a new user account."""
    db = await get_db()
    user_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    subscription_tier = user.subscription_tier

    await db.create_user(user_id, user.email, user.name, subscription_tier)

    return UserResponse(
        user_id=user_id,
        email=user.email,
        name=user.name,
        subscription_tier=subscription_tier,
        created_at=created_at
    )


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(current_user=Depends(get_current_user)):
    """Get current user information."""
    db = await get_db()
    user = await db.get_user_by_id(current_user["user_id"])

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user["name"],
        subscription_tier=user["subscription_tier"],
        created_at=user["created_at"].isoformat() if hasattr(user["created_at"], 'isoformat') else str(user["created_at"])
    )


@router.put("/users/me", response_model=UserResponse)
async def update_user(user_update: UserCreate, current_user=Depends(get_current_user)):
    """Update current user information."""
    db = await get_db()
    await db.update_user(current_user["user_id"], user_update.email, user_update.name, user_update.subscription_tier)

    return UserResponse(
        user_id=current_user["user_id"],
        email=user_update.email,
        name=user_update.name,
        subscription_tier=user_update.subscription_tier,
        created_at=datetime.utcnow().isoformat()
    )


@router.delete("/users/me")
async def delete_user(current_user=Depends(get_current_user)):
    """Delete current user account."""
    db = await get_db()
    await db.delete_user(current_user["user_id"])
    return {"message": "User deleted successfully"}


@router.post("/auth/logout")
async def logout(response: Response):
    """Logout and clear JWT cookie."""
    clear_auth_cookie(response)
    return {"message": "Successfully logged out"}


@router.post("/auth/login")
async def login(response: Response, email: str, password: str = ""):
    """Login and get JWT token.
    
    Production mode (USE_HTTP_ONLY_COOKIE=true):
        - Sets httpOnly cookie for true XSS protection
        - Token not accessible via JavaScript
    Development mode:
        - Returns token in response body for legacy clients
    """
    db = await get_db()
    user = await db.get_user_by_email(email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create JWT token
    token = create_token(user["user_id"], user.get("role", "viewer"))
    
    user_data = {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "subscription_tier": user["subscription_tier"],
        "created_at": datetime.utcnow().isoformat()
    }
    
    if USE_HTTP_ONLY_COOKIE:
        # Production: Set httpOnly cookie for true XSS protection
        # Cookie is HttpOnly (not accessible to JavaScript), Secure (HTTPS only), SameSite=strict
        set_auth_cookie(response, token, max_age=3600)
        
        # Return info that httpOnly cookie is being used
        return {
            "access_token": "",
            "token_type": "bearer",
            "use_http_only_cookie": True,
            "user": UserResponse(**user_data)
        }
    else:
        # Development/legacy: Return token in response body
        return {
            "access_token": token,
            "token_type": "bearer",
            "use_http_only_cookie": False,
            "user": UserResponse(**user_data)
        }
