from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import SubscriptionResponse, SubscriptionCreate
from ..db.db_client import get_db
from ..security import get_current_user
import uuid
from datetime import datetime, timedelta

router = APIRouter()


@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(subscription: SubscriptionCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Create a new subscription for the current user."""
    subscription_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=30)  # 30-day subscription

    # Insert subscription into database
    query = """
    INSERT INTO subscriptions (subscription_id, user_id, plan_id, status, created_at, expires_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    await db.execute(query, (
        subscription_id,
        current_user["user_id"],
        subscription.plan_id,
        "active",
        created_at.isoformat(),
        expires_at.isoformat()
    ))

    return SubscriptionResponse(
        subscription_id=subscription_id,
        user_id=current_user["user_id"],
        plan_id=subscription.plan_id,
        status="active",
        created_at=created_at.isoformat(),
        expires_at=expires_at.isoformat()
    )


@router.get("/subscriptions/me", response_model=SubscriptionResponse)
async def get_current_subscription(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Get current user's active subscription."""
    query = "SELECT * FROM subscriptions WHERE user_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1"
    row = await db.fetch_one(query, (current_user["user_id"],))

    if not row:
        raise HTTPException(
            status_code=404, detail="No active subscription found")

    return SubscriptionResponse(
        subscription_id=row["subscription_id"],
        user_id=row["user_id"],
        plan_id=row["plan_id"],
        status=row["status"],
        created_at=row["created_at"],
        expires_at=row["expires_at"]
    )


@router.put("/subscriptions/me/cancel")
async def cancel_subscription(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Cancel current user's subscription."""
    query = "UPDATE subscriptions SET status = 'cancelled' WHERE user_id = ? AND status = 'active'"
    await db.execute(query, (current_user["user_id"],))
    return {"message": "Subscription cancelled successfully"}


@router.get("/subscriptions/history", response_model=List[SubscriptionResponse])
async def get_subscription_history(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Get subscription history for current user."""
    query = "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC"
    rows = await db.fetch_all(query, (current_user["user_id"],))

    return [
        SubscriptionResponse(
            subscription_id=row["subscription_id"],
            user_id=row["user_id"],
            plan_id=row["plan_id"],
            status=row["status"],
            created_at=row["created_at"],
            expires_at=row["expires_at"]
        ) for row in rows
    ]
