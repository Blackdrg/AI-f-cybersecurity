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

    @task(1)
    def stress_test(self):
        """Push the system until failure to measure degradation curve."""
        # Rapid fire requests
        for _ in range(10):
            self.client.get("/api/recognize_v2?org_id=stress_test")

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    if exception:
        print(f"Request {name} failed: {exception}")
    else:
        # Log latency breakdown (mocking different stages)
        if name == "multi_cam_recognize":
            stages = {
                "detection": response_time * 0.3,
                "embedding": response_time * 0.4,
                "search": response_time * 0.2,
                "decision": response_time * 0.1
            }
            # This would normally be pushed to Prometheus

@events.test_start.add_listener
def on_test_start(environment):
    print("Starting enterprise load test (1000+ streams target)...")

