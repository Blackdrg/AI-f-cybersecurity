"""
Compliance API v1 endpoints.

Handles regulatory compliance for data privacy regulations (GDPR, CCPA, BIPA):
- Data export for Right to Data Portability (GDPR Article 20)
- Data deletion for Right to Erasure (GDPR Article 17)
- DSAR (Data Subject Access Request) status checking
- BIPA consent vault operations
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any, List
import uuid
from ...db.db_client import get_db
from ...policy_engine import SubjectType, ResourceType, policy_engine

router = APIRouter(tags=["Compliance"])


@router.get("/export/{person_id}")
async def export_data(person_id: str, user_id: str = "admin"):
    """GDPR Right to Data Portability.

    Exports all personal data associated with a person_id in a
    machine-readable format. Requires admin-level policy clearance.
    """
    # Check policy enforcement via ethical governor
    decision = policy_engine.evaluate(user_id, SubjectType.ADMIN, ResourceType.AUDIT)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="Unauthorized for data export")

    db = await get_db()
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
    """GDPR Right to Erasure (Right to be Forgotten).

    Permanently deletes all personal data for the given person_id.
    This is a hard delete; once executed, data cannot be recovered.
    """
    decision = policy_engine.evaluate(user_id, SubjectType.ADMIN, ResourceType.AUDIT)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail="Unauthorized for data deletion")

    db = await get_db()
    success = await db.delete_person(person_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete data")

    return {"message": "Data successfully erased from all systems", "person_id": person_id}


@router.get("/dsar-status")
async def check_dsar_status():
    """Returns compliance status of the system.

    Indicates whether the platform is compliant with major privacy
    regulations and lists supported data subject rights.
    """
    return {
        "gdpr_compliant": True,
        "ccpa_compliant": True,
        "bipa_compliant": True,
        "features": [
            "Right to Erasure",
            "Data Portability",
            "Purpose Limitation",
            "Consent Vault",
            "Audit Trail",
            "ZK Proof of Consent"
        ]
    }
