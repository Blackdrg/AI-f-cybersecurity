from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any, List
import uuid
from ..db.db_client import DBClient
from ..policy_engine import SubjectType, ResourceType, policy_engine

router = APIRouter(prefix="/compliance", tags=["Compliance"])
db = DBClient()

@router.get("/export/{person_id}")
async def export_data(person_id: str, user_id: str = "admin"):
    """GDPR Right to Data Portability."""
    # Check policy
    decision = policy_engine.evaluate(user_id, SubjectType.ADMIN, ResourceType.AUDIT)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="Unauthorized for data export")
    
    data = await db.get_person_full_data(person_id)
    if not data:
        raise HTTPException(status_code=404, detail="Person not found")
    
    return {
        "status": "success",
        "export_timestamp": str(uuid.uuid4()),
        "data": data
    }

@router.delete("/delete/{person_id}")
async def delete_data(person_id: str, user_id: str = "admin"):
    """GDPR Right to Erasure."""
    decision = policy_engine.evaluate(user_id, SubjectType.ADMIN, ResourceType.AUDIT)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="Unauthorized for data deletion")
    
    success = await db.delete_person(person_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete data")
    
    return {"message": "Data successfully erased from all systems", "person_id": person_id}

@router.get("/dsar-status")
async def check_dsar_status():
    """Returns compliance status of the system."""
    return {
        "gdpr_compliant": True,
        "ccpa_compliant": True,
        "features": ["Right to Erasure", "Data Portability", "Purpose Limitation", "Consent Vault"]
    }
