from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import CameraCreate, CameraResponse
from ..db.db_client import get_db
from ..camera.rtsp_manager import rtsp_manager
from ..security import require_org_operator, require_org_admin
from typing import Dict, Any

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

@router.post("/cameras/test-connection")
async def test_camera_connection(data: Dict[str, str]):
    """Validate an RTSP URL without saving it."""
    rtsp_url = data.get("rtsp_url")
    if not rtsp_url:
        raise HTTPException(400, "rtsp_url is required")
        
    # Attempt to open the stream
    import cv2
    cap = cv2.VideoCapture(rtsp_url)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            return {"status": "success", "message": "Stream connection verified"}
    
    raise HTTPException(400, "Could not connect to RTSP stream")

@router.get("/{org_id}/cameras", response_model=List[CameraResponse])
async def list_cameras(org_id: str, current_user=Depends(require_org_operator)):
    """List all cameras in the organization."""
    db = await get_db()
    cameras = await db.get_org_cameras(org_id)
    return [CameraResponse(**c) for c in cameras]

@router.post("/{org_id}/cameras/{camera_id}/start", status_code=204)
async def start_camera_stream(org_id: str, camera_id: str, current_user=Depends(require_org_admin)):
    """Start RTSP stream for camera."""
    db = await get_db()
    cameras = await db.get_org_cameras(org_id)
    camera = next((c for c in cameras if c['camera_id'] == camera_id), None)
    if not camera or not camera.get('rtsp_url'):
        raise HTTPException(404, "Camera not found or no RTSP URL")
    
    rtsp_manager.add_camera(camera_id, camera['rtsp_url'])
    return

@router.get("/{org_id}/cameras/{camera_id}/status", response_model=Dict[str, Any])
async def get_camera_status(org_id: str, camera_id: str, current_user=Depends(require_org_operator)):
    """Get RTSP stream status."""
    status = rtsp_manager.get_status(camera_id)
    if not status:
        raise HTTPException(404, "Camera stream not found")
    return status[0]

@router.get("/{org_id}/cameras/status", response_model=List[Dict[str, Any]])
async def get_all_cameras_status(org_id: str, current_user=Depends(require_org_operator)):
    """Get status for all organization cameras."""
    return rtsp_manager.get_status()
