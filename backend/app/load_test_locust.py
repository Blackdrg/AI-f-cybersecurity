from locust import HttpUser, task, between, events
import time
import asyncio
import json

class FaceRecognitionUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def stream_recognize(self):
        """Simulate WS stream recognition."""
        # POST multi-cam stream
        payload = {
            "camera_ids": ["cam1", "cam2", "cam3", "cam4", "cam5"],
            "sync_timestamps": [str(time.time()) for _ in range(5)],
            "streams": ["base64frame" for _ in range(5)]  # Mock
        }
        self.client.post("/api/stream_recognize", json=payload, name="multi_cam_recognize")
    
    @task(2)
    def add_camera_rtsp(self):
        """Add RTSP cam."""
        cam = {
            "name": "Hikvision Cam",
            "rtsp_url": "rtsp://admin:pass@192.168.1.100:554/stream",
            "location": "Entrance"
        }
        self.client.post("/org123/cameras", json=cam)
    
    @task(1)
    def start_camera_stream(self):
        """Start RTSP stream."""
        self.client.post("/org123/cameras/cam123/start_stream")
    
    @task(1)
    def recognition_tune(self):
        """Tune threshold."""
        self.client.get("/api/tune_threshold")

@events.test_start.add_listener
def on_test_start(environment):
    print("Starting 100 user load test with 5 RTSP cams...")
    print("Targets: <300ms latency, FAR<1%, FRR<3%")

@events.test_stop.add_listener
def on_test_stop(environment):
    print("Load test complete - check Grafana/Prometheus")

