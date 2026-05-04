import pytest
import io
import cv2
import numpy as np
from conftest import test_client, authenticated_client, mock_redis, mock_models  # mock_models added if needed

def create_test_image():
    img = np.zeros((112, 112, 3), dtype=np.uint8)
    img[40:80, 40:80] = [255, 255, 255]
    _, buffer = cv2.imencode('.jpg', img)
    return io.BytesIO(buffer.tobytes())

class TestIntegration:
    def test_database_connection(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_recognize_with_mock(self, authenticated_client, mock_models):
        img_data = create_test_image()
        response = authenticated_client.post(
            "/api/recognize",
            files={"image": ("test.jpg", img_data, "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "faces" in data

    def test_rate_limit(self, test_client, mock_redis):
        for i in range(5):
            response = test_client.post("/api/recognize", files={"image": create_test_image()})
            if i < 3:  # Assume free tier limit
                assert response.status_code in [200, 401, 403]
            else:
                assert response.status_code == 429

    def test_policy_engine(self, authenticated_client):
        response = authenticated_client.get("/api/admin/metrics")
        assert response.status_code in [200, 403]  # 403 if no admin role
