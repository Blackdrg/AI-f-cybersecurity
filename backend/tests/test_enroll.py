import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.security import create_token
import io
import cv2
import numpy as np

client = TestClient(app)


def create_test_image():
    # Create a simple test image with a face-like rectangle
    img = np.zeros((112, 112, 3), dtype=np.uint8)
    img[40:80, 40:80] = [255, 255, 255]  # White rectangle as "face"
    _, buffer = cv2.imencode('.jpg', img)
    return io.BytesIO(buffer.tobytes())


@pytest.mark.asyncio
async def test_enroll_success():
    # Create a test token for authentication
    token = create_token("test_user", "user")

    img_data = create_test_image()
    response = client.post(
        "/api/enroll",
        files={"images": ("test.jpg", img_data, "image/jpeg")},
        data={"name": "Test Person", "metadata": "{}", "consent": "true"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "person_id" in data
    assert data["num_embeddings"] > 0


@pytest.mark.asyncio
async def test_enroll_no_consent():
    # Create a test token for authentication
    token = create_token("test_user", "user")

    img_data = create_test_image()
    response = client.post(
        "/api/enroll",
        files={"images": ("test.jpg", img_data, "image/jpeg")},
        data={"consent": "false"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
