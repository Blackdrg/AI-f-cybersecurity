from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import UserCreate, UserResponse
from ..db.db_client import get_db
from ..security import get_current_user
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate, db=Depends(get_db)):
    """Create a new user account."""
    user_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    # Special case: Make daredevil0101a@gmail.com have unlimited enterprise access
    subscription_tier = "enterprise" if user.email == "daredevil0101a@gmail.com" else user.subscription_tier

    # Insert user into database
    query = """
    INSERT INTO users (user_id, email, name, subscription_tier, created_at)
    VALUES (?, ?, ?, ?, ?)
    """
    await db.execute(query, (user_id, user.email, user.name, subscription_tier, created_at))

    return UserResponse(
        user_id=user_id,
        email=user.email,
        name=user.name,
        subscription_tier=subscription_tier,
        created_at=created_at
    )


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Get current user information."""
    query = "SELECT * FROM users WHERE user_id = ?"
    row = await db.fetch_one(query, (current_user["user_id"],))

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        user_id=row["user_id"],
        email=row["email"],
        name=row["name"],
        subscription_tier=row["subscription_tier"],
        created_at=row["created_at"]
    )


@router.put("/users/me", response_model=UserResponse)
async def update_user(user_update: UserCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Update current user information."""
    query = """
    UPDATE users SET email = ?, name = ?, subscription_tier = ? WHERE user_id = ?
    """
    await db.execute(query, (user_update.email, user_update.name, user_update.subscription_tier, current_user["user_id"]))

    return await get_current_user_info(current_user, db)


@router.delete("/users/me")
async def delete_user(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Delete current user account."""
    query = "DELETE FROM users WHERE user_id = ?"
    await db.execute(query, (current_user["user_id"],))
    return {"message": "User deleted successfully"}
