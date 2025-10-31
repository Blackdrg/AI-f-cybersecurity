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

@pytest.mark.asyncio
async def test_recognize_unknown():
    img_data = create_test_image()
    response = client.post(
        "/api/recognize",
        files={"image": ("test.jpg", img_data, "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    # Assuming no enrolled faces, should return empty matches
    for face in data["faces"]:
        assert len(face["matches"]) == 0
