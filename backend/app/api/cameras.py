from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import CameraCreate, CameraResponse
from ..db.db_client import get_db
from ..security import require_org_operator, require_org_admin

router = APIRouter()

@router.post("/{org_id}/cameras", response_model=CameraResponse)
async def add_camera(org_id: str, camera: CameraCreate, current_user=Depends(require_org_admin)):
    """Add a new camera to the organization."""
    db = await get_db()
    camera_id = await db.add_camera(org_id, camera.name, camera.rtsp_url, camera.location)
    return CameraResponse(
        camera_id=camera_id,
        org_id=org_id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        location=camera.location,
        status="offline",
        created_at=None
    )

@router.get("/{org_id}/cameras", response_model=List[CameraResponse])
async def list_cameras(org_id: str, current_user=Depends(require_org_operator)):
    """List all cameras in the organization."""
    db = await get_db()
    cameras = await db.get_org_cameras(org_id)
    return [CameraResponse(**c) for c in cameras]
