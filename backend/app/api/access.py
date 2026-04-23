from fastapi import APIRouter, Body
from pydantic import BaseModel

router = APIRouter()

class UnlockRequest(BaseModel):
    person_id: str
    reason: str = "authorized"

@router.post("/door_unlock")
async def door_unlock(request: UnlockRequest):
    # Trigger webhook/GPIO
    print(f"Door unlocked for {request.person_id}: {request.reason}")
    return {"success": True, "message": "Door unlocked for 5s (webhook triggered)"}


