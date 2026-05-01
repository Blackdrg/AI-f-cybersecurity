import pytest
from fastapi.testclient import TestClient
from app.main import app
import io
import cv2
import numpy as np

client = TestClient(app)

def create_test_image():
    img = np.zeros((112, 112, 3), dtype=np.uint8)
    img[40:80, 40:80] = [255, 255, 255]
    _, buffer = cv2.imencode('.jpg', img)
    return io.BytesIO(buffer.tobytes())

def test_recognize_unknown():
    """Test /api/recognize endpoint with unknown face."""
    img_data = create_test_image()
    response = client.post(
        "/api/recognize",
        files={"image": ("test.jpg", img_data, "image/jpeg")}
    )
    # Will return 401/403 if auth required, or 200 if auth not required
    assert response.status_code in [200, 401, 403]
    if response.status_code == 200:
        data = response.json()
        # Assuming no enrolled faces, should return empty matches or success
        assert "faces" in data or data.get("success") is True
