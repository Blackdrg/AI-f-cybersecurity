from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import SubscriptionResponse, SubscriptionCreate
from ..db.db_client import get_db
from ..security import get_current_user
import uuid
from datetime import datetime, timedelta

router = APIRouter()


@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(subscription: SubscriptionCreate, current_user=Depends(get_current_user)):
    """Create a new subscription for the current user."""
    db = await get_db()
    subscription_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=30)

    await db.create_subscription(subscription_id, current_user["user_id"], subscription.plan_id, "active", expires_at)

    return SubscriptionResponse(
        subscription_id=subscription_id,
        user_id=current_user["user_id"],
        plan_id=subscription.plan_id,
        status="active",
        created_at=created_at.isoformat(),
        expires_at=expires_at.isoformat()
    )


@router.get("/subscriptions/me", response_model=SubscriptionResponse)
async def get_current_subscription(current_user=Depends(get_current_user)):
    """Get current user's active subscription."""
    db = await get_db()
    sub = await db.get_subscription(current_user["user_id"])

    if not sub:
        # Return default free plan info
        return SubscriptionResponse(
            subscription_id="free",
            user_id=current_user["user_id"],
            plan_id="free",
            status="active",
            created_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(days=365)).isoformat()
        )

    return SubscriptionResponse(
        subscription_id=sub["subscription_id"],
        user_id=sub["user_id"],
        plan_id=sub["plan_id"],
        status=sub["status"],
        created_at=sub["created_at"].isoformat() if hasattr(sub["created_at"], 'isoformat') else str(sub["created_at"]),
        expires_at=sub["expires_at"].isoformat() if hasattr(sub["expires_at"], 'isoformat') else str(sub["expires_at"])
    )


@router.put("/subscriptions/me/cancel")
async def cancel_subscription(current_user=Depends(get_current_user)):
    """Cancel current user's subscription."""
    db = await get_db()
    sub = await db.get_subscription(current_user["user_id"])
    if sub:
        await db.cancel_subscription(sub["subscription_id"])
    return {"message": "Subscription cancelled successfully"}


@router.get("/subscriptions/history", response_model=List[SubscriptionResponse])
async def get_subscription_history(current_user=Depends(get_current_user)):
    """Get subscription history for current user."""
    db = await get_db()
    subs = await db.get_subscription_history(current_user["user_id"])

    if not subs:
        return []

    return [
        SubscriptionResponse(
            subscription_id=s["subscription_id"],
            user_id=s["user_id"],
            plan_id=s["plan_id"],
            status=s["status"],
            created_at=s["created_at"].isoformat() if hasattr(s["created_at"], 'isoformat') else str(s["created_at"]),
            expires_at=s["expires_at"].isoformat() if hasattr(s["expires_at"], 'isoformat') else str(s["expires_at"])
        ) for s in subs
    ]
