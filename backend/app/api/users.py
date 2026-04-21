from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import UserCreate, UserResponse
from ..db.db_client import get_db
from ..security import get_current_user, create_token
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Create a new user account."""
    db = await get_db()
    user_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    # Special case: Make daredevil0101a@gmail.com have unlimited enterprise access
    subscription_tier = "enterprise" if user.email == "daredevil0101a@gmail.com" else user.subscription_tier

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


@router.post("/auth/login")
async def login(email: str, password: str = ""):
    """Login and get JWT token."""
    db = await get_db()
    user = await db.get_user_by_email(email)
    
    if not user:
        # Auto-create user on first login (simplified auth)
        user_id = str(uuid.uuid4())
        await db.create_user(user_id, email, email.split('@')[0], "free")
        user = {"user_id": user_id, "email": email, "name": email.split('@')[0], "subscription_tier": "free"}
    
    # Create JWT token (password check skipped for demo)
    token = create_token(user["user_id"], user.get("role", "user"))
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            name=user["name"],
            subscription_tier=user["subscription_tier"],
            created_at=datetime.utcnow().isoformat()
        )
    }
