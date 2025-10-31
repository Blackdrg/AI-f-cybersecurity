import cv2
import asyncio
from typing import Dict, Any, List
from .base import PluginBase
import logging

logger = logging.getLogger(__name__)


class RTSPCameraPlugin(PluginBase):
    def __init__(self):
        self.cameras: Dict[str, Dict[str, Any]] = {}
        self.active_captures: Dict[str, cv2.VideoCapture] = {}

    @property
    def name(self) -> str:
        return "rtsp_camera"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        # Config should contain camera URLs
        self.cameras = config.get('cameras', {})
        logger.info(
            f"Initialized RTSP Camera plugin with {len(self.cameras)} cameras")
        return True

    async def shutdown(self):
        for cap in self.active_captures.values():
            cap.release()
        self.active_captures.clear()

    async def get_devices(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": cam_id,
                "name": config.get('name', f"Camera {cam_id}"),
                "type": "rtsp_camera",
                "url": config['url']
            }
            for cam_id, config in self.cameras.items()
        ]

    async def capture_from_device(self, device_id: str) -> bytes:
        if device_id not in self.cameras:
            raise ValueError(f"Camera {device_id} not configured")

        url = self.cameras[device_id]['url']

        # Run capture in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._capture_frame, url)

    def _capture_frame(self, url: str) -> bytes:
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open RTSP stream: {url}")

        ret, frame = cap.read()
        cap.release()

        if not ret:
            raise RuntimeError("Failed to capture frame")

        # Encode to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            raise RuntimeError("Failed to encode frame")

        return buffer.tobytes()

    async def process_data(self, data: bytes) -> Dict[str, Any]:
        # For RTSP, data is already processed frame
        return {"frame": data, "format": "jpeg"}


Plugin = RTSPCameraPlugin
