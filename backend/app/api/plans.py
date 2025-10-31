from fastapi import APIRouter, HTTPException
from typing import List
from ..schemas import PlanResponse
from ..db.db_client import get_db

router = APIRouter()

# Static plans data - in production, this would come from database
PLANS = [
    {
        "plan_id": "free",
        "name": "Free",
        "price": 0.0,
        "features": ["Basic face recognition", "Up to 100 recognitions/month"],
        "limits": {"recognitions": 100, "enrollments": 10}
    },
    {
        "plan_id": "pro",
        "name": "Pro",
        "price": 29.99,
        "features": ["Advanced face recognition", "Unlimited recognitions", "Emotion detection", "Age/Gender estimation"],
        # -1 means unlimited
        "limits": {"recognitions": -1, "enrollments": 1000}
    },
    {
        "plan_id": "enterprise",
        "name": "Enterprise",
        "price": 99.99,
        "features": ["All Pro features", "Multi-modal recognition", "Custom models", "Priority support"],
        "limits": {"recognitions": -1, "enrollments": -1}
    }
]


@router.get("/plans", response_model=List[PlanResponse])
async def get_plans():
    """Get all available subscription plans."""
    return [PlanResponse(**plan) for plan in PLANS]


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    """Get a specific plan by ID."""
    for plan in PLANS:
        if plan["plan_id"] == plan_id:
            return PlanResponse(**plan)
    raise HTTPException(status_code=404, detail="Plan not found")
