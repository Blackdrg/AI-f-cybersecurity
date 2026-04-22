import cv2
import threading
from collections import deque
from typing import Dict, Optional, List
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class RTSPStream:
    def __init__(self, camera_id: str, rtsp_url: str, max_buffer: int = 300):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.max_buffer = max_buffer
        self.buffer = deque(maxlen=max_buffer)
        self.cap = None
        self.thread = None
        self.running = False
        self.last_frame_time = 0
        self.reconnect_attempts = 0
        self.max_reconnects = 10
        self.reconnect_delay = 5.0  # Start with 5s
        
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started RTSP stream for {self.camera_id}")
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        logger.info(f"Stopped RTSP stream for {self.camera_id}")
    
    def _capture_loop(self):
        while self.running:
            try:
                if self.cap is None or not self.cap.isOpened():
                    self._connect()
                
                if self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret:
                        self.buffer.append(frame)
                        self.last_frame_time = time.time()
                        self.reconnect_attempts = 0  # Reset
                    else:
                        logger.warning(f"Failed to read frame from {self.camera_id}")
                        self.reconnect_delay = min(self.reconnect_delay * 1.5, 30.0)
                        time.sleep(0.1)
                else:
                    time.sleep(1.0)
                    
            except Exception as e:
                logger.error(f"Capture error {self.camera_id}: {e}")
                self.reconnect_delay = min(self.reconnect_delay * 1.5, 30.0)
                time.sleep(self.reconnect_delay)
    
    def _connect(self):
        self.cap = cv2.VideoCapture(self.rtsp_url)
        if self.cap.isOpened():
            # Optimize for RTSP (Hikvision/CP Plus)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, 15)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            logger.info(f"Connected to {self.camera_id}: {self.rtsp_url}")
            self.reconnect_attempts = 0
            self.reconnect_delay = 5.0
        else:
            self.reconnect_attempts += 1
            logger.warning(f"Connection failed {self.camera_id} (attempt {self.reconnect_attempts}/{self.max_reconnects})")
            if self.reconnect_attempts > self.max_reconnects:
                logger.error(f"Max reconnects exceeded for {self.camera_id}")
                self.reconnect_delay = 30.0
    
    def get_frame(self) -> Optional[bytes]:
        if self.buffer:
            frame = self.buffer[-1].copy()  # Latest frame
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return buffer.tobytes()
        return None
    
    def get_buffer_stats(self) -> Dict:
        return {
            'camera_id': self.camera_id,
            'buffer_size': len(self.buffer),
            'max_buffer': self.max_buffer,
            'fps_estimate': 1.0 / max((time.time() - self.last_frame_time), 0.01),
            'status': 'connected' if self.cap and self.cap.isOpened() else 'disconnected'
        }

class RTSPManager:
    def __init__(self):
        self.streams: Dict[str, RTSPStream] = {}
        self.lock = threading.Lock()
    
    def add_camera(self, camera_id: str, rtsp_url: str):
        with self.lock:
            if camera_id in self.streams:
                return
            stream = RTSPStream(camera_id, rtsp_url)
            self.streams[camera_id] = stream
            stream.start()
    
    def remove_camera(self, camera_id: str):
        with self.lock:
            if camera_id in self.streams:
                self.streams[camera_id].stop()
                del self.streams[camera_id]
    
    def get_frame(self, camera_id: str) -> Optional[bytes]:
        with self.lock:
            stream = self.streams.get(camera_id)
            return stream.get_frame() if stream else None
    
    def get_status(self, camera_id: Optional[str] = None) -> List[Dict]:
        with self.lock:
            if camera_id:
                stream = self.streams.get(camera_id)
                return [stream.get_buffer_stats()] if stream else []
            return [stream.get_buffer_stats() for stream in self.streams.values()]
    
    def supports_multi_camera(self) -> bool:
        return len(self.streams) >= 3  # At least 3 cams
    
# Global singleton
rtsp_manager = RTSPManager()
