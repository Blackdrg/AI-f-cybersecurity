from fastapi import APIRouter, HTTPException, Depends
from ..schemas import UsageResponse
from ..db.db_client import get_db
from ..security import get_current_user
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/usage/current", response_model=UsageResponse)
async def get_current_usage(current_user=Depends(get_current_user)):
    """Get current month's usage for the authenticated user."""
    db = await get_db()
    
    # Special case: Unlimited usage for enterprise
    if current_user.get("subscription_tier") == "enterprise":
        return UsageResponse(
            user_id=current_user["user_id"],
            period_start=datetime.utcnow().isoformat(),
            period_end=(datetime.utcnow() + timedelta(days=30)).isoformat(),
            recognitions_used=0,
            enrollments_used=0,
            recognitions_limit=-1,
            enrollments_limit=-1
        )

    usage = await db.get_usage(current_user["user_id"])

    return UsageResponse(
        user_id=current_user["user_id"],
        period_start=usage.get("period_start", datetime.utcnow().isoformat()),
        period_end=usage.get("period_end", (datetime.utcnow() + timedelta(days=30)).isoformat()),
        recognitions_used=usage.get("recognitions_used", 0),
        enrollments_used=usage.get("enrollments_used", 0),
        recognitions_limit=usage.get("recognitions_limit", 100),
        enrollments_limit=usage.get("enrollments_limit", 10)
    )


@router.get("/usage/limits")
async def get_usage_limits(current_user=Depends(get_current_user)):
    """Get usage limits for the current user's plan."""
    db = await get_db()
    usage = await db.get_usage(current_user["user_id"])
    
    return {
        "recognitions": usage.get("recognitions_limit", 100),
        "enrollments": usage.get("enrollments_limit", 10)
    }
