from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from ..schemas import OrganizationCreate, OrganizationResponse, OrgMemberAdd
from ..db.db_client import get_db
from ..security import get_current_user, require_org_admin
import uuid

router = APIRouter()

@router.post("/organizations", response_model=OrganizationResponse)
async def create_organization(org: OrganizationCreate, current_user=Depends(get_current_user)):
    """Create a new organization and add the creator as admin."""
    db = await get_db()
    org_id = await db.create_organization(org.name, org.billing_email)
    await db.add_org_member(org_id, current_user["user_id"], "admin")
    
    return OrganizationResponse(
        org_id=org_id,
        name=org.name,
        billing_email=org.billing_email,
        subscription_tier="free",
        created_at=None # DB will set it
    )

@router.get("/organizations", response_model=List[OrganizationResponse])
async def get_user_organizations(current_user=Depends(get_current_user)):
    """Get all organizations the current user belongs to."""
    db = await get_db()
    orgs = await db.get_user_orgs(current_user["user_id"])
    return [OrganizationResponse(**org) for org in orgs]

@router.post("/organizations/{org_id}/members")
async def add_member(org_id: str, member: OrgMemberAdd, current_user=Depends(require_org_admin)):
    """Add a member to an organization (Org Admin only)."""
    db = await get_db()
    await db.add_org_member(org_id, member.user_id, member.role)
    return {"message": "Member added successfully"}

@router.post("/organizations/{org_id}/api-keys")
async def generate_api_key(org_id: str, name: str, current_user=Depends(require_org_admin)):
    """Generate a new API key for the organization."""
    db = await get_db()
    api_key = await db.create_api_key(org_id, name, ["full_access"])
    return {"api_key": api_key}
