from fastapi import APIRouter, HTTPException, Depends
from ..schemas import UsageResponse
from ..db.db_client import get_db
from ..security import get_current_user
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/usage/current", response_model=UsageResponse)
async def get_current_usage(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Get current month's usage for the authenticated user."""
    start_of_month = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)

    # Special case: Unlimited usage for daredevil0101a@gmail.com
    if current_user.get("email") == "daredevil0101a@gmail.com":
        return UsageResponse(
            user_id=current_user["user_id"],
            period_start=start_of_month.isoformat(),
            period_end=(start_of_month + timedelta(days=30)).isoformat(),
            recognitions_used=0,  # Show as 0 since unlimited
            enrollments_used=0,
            recognitions_limit=999999,  # Unlimited
            enrollments_limit=999999
        )

    # Get recognition usage
    query_recognitions = """
    SELECT COUNT(*) as count FROM recognition_logs
    WHERE user_id = ? AND created_at >= ?
    """
    recognition_row = await db.fetch_one(query_recognitions, (current_user["user_id"], start_of_month.isoformat()))

    # Get enrollment usage
    query_enrollments = """
    SELECT COUNT(*) as count FROM enrollment_logs
    WHERE user_id = ? AND created_at >= ?
    """
    enrollment_row = await db.fetch_one(query_enrollments, (current_user["user_id"], start_of_month.isoformat()))

    # Get user's plan limits (simplified - in production, get from subscription)
    # Default free plan limits
    plan_limits = {"recognitions": 100, "enrollments": 10}

    return UsageResponse(
        user_id=current_user["user_id"],
        period_start=start_of_month.isoformat(),
        period_end=(start_of_month + timedelta(days=30)).isoformat(),
        recognitions_used=recognition_row["count"] if recognition_row else 0,
        enrollments_used=enrollment_row["count"] if enrollment_row else 0,
        recognitions_limit=plan_limits["recognitions"],
        enrollments_limit=plan_limits["enrollments"]
    )


@router.get("/usage/limits")
async def get_usage_limits(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Get usage limits for the current user's plan."""
    # Get user's current plan
    query = """
    SELECT p.limits FROM subscriptions s
    JOIN plans p ON s.plan_id = p.plan_id
    WHERE s.user_id = ? AND s.status = 'active'
    ORDER BY s.created_at DESC LIMIT 1
    """
    row = await db.fetch_one(query, (current_user["user_id"],))

    if not row:
        # Default free plan limits
        return {"recognitions": 100, "enrollments": 10}

    # Parse limits from database (assuming JSON stored as string)
    import json
    limits = json.loads(row["limits"])
    return limits
