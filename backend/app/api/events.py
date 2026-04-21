from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from ..schemas import RecognitionEventResponse
from ..db.db_client import get_db
from ..security import require_org_operator

router = APIRouter()

@router.get("/{org_id}/events", response_model=List[RecognitionEventResponse])
async def list_events(org_id: str, limit: int = 100, current_user=Depends(require_org_operator)):
    """List recent recognition events for the organization."""
    db = await get_db()
    events = await db.get_org_events(org_id, limit)
    return [RecognitionEventResponse(**e) for e in events]

@router.get("/{org_id}/persons/{person_id}/timeline", response_model=List[RecognitionEventResponse])
async def get_person_timeline(org_id: str, person_id: str, limit: int = 50, current_user=Depends(require_org_operator)):
    """Get the recognition timeline for a specific person."""
    db = await get_db()
    events = await db.get_person_timeline(person_id, limit)
    return [RecognitionEventResponse(**e) for e in events]
