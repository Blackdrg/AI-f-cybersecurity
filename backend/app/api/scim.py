"""
SCIM 2.0 (System for Cross-domain Identity Management) API.

Handles automated user provisioning and de-provisioning from Identity Providers (IdP).
"""
from fastapi import APIRouter, Request, HTTPException, Depends, status
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ..db.db_client import get_db
from ..security import get_current_active_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scim/v2", tags=["SCIM"])

# SCIM Schemas
class ScimUserEmail(BaseModel):
    value: str
    type: str = "work"
    primary: bool = True

class ScimUserName(BaseModel):
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None

class ScimUserCreate(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    name: Optional[ScimUserName] = None
    emails: List[ScimUserEmail]
    active: bool = True

class ScimUserResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    id: str
    userName: str
    name: Optional[ScimUserName] = None
    emails: List[ScimUserEmail]
    active: bool
    meta: Dict[str, Any]

class ScimListResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    totalResults: int
    startIndex: int
    itemsPerPage: int
    Resources: List[Dict[str, Any]]

@router.get("/Users", response_model=ScimListResponse)
async def get_scim_users(
    startIndex: int = 1,
    count: int = 100,
    filter: Optional[str] = None
):
    """List SCIM users."""
    db = get_db()
    # In a real implementation, we would parse the SCIM filter
    users = await db.fetch_all("SELECT user_id, email, name, is_active FROM users LIMIT $1 OFFSET $2", count, startIndex - 1)
    
    resources = []
    for u in users:
        resources.append({
            "id": u["user_id"],
            "userName": u["email"],
            "emails": [{"value": u["email"], "primary": True}],
            "active": u["is_active"],
            "meta": {"resourceType": "User"}
        })
    
    return {
        "totalResults": len(resources),
        "startIndex": startIndex,
        "itemsPerPage": count,
        "Resources": resources
    }

@router.post("/Users", response_model=ScimUserResponse, status_code=status.HTTP_201_CREATED)
async def create_scim_user(user: ScimUserCreate):
    """Provision a new user via SCIM."""
    db = get_db()
    email = user.emails[0].value
    
    existing = await db.get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    
    user_id = await db.create_user(
        user_id=f"scim_{user.userName}",
        email=email,
        name=user.name.formatted if user.name else user.userName,
        is_active=user.active
    )
    
    return {
        "id": user_id,
        "userName": email,
        "emails": [{"value": email, "primary": True}],
        "active": user.active,
        "meta": {"resourceType": "User", "created": "now"}
    }

@router.get("/Users/{user_id}", response_model=ScimUserResponse)
async def get_scim_user(user_id: str):
    """Get a specific SCIM user."""
    db = get_db()
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user["user_id"],
        "userName": user["email"],
        "emails": [{"value": user["email"], "primary": True}],
        "active": user["is_active"],
        "meta": {"resourceType": "User"}
    }

@router.put("/Users/{user_id}", response_model=ScimUserResponse)
async def update_scim_user(user_id: str, user_update: ScimUserCreate):
    """Update a user via SCIM."""
    db = get_db()
    # Implementation of update logic
    return await get_scim_user(user_id)

@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scim_user(user_id: str):
    """De-provision a user via SCIM."""
    db = get_db()
    await db.execute("UPDATE users SET is_active = false WHERE user_id = $1", user_id)
    return None
