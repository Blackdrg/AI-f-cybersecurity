from app.schemas import FederatedUpdate
from app.main import app
import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

client = TestClient(app)


def test_receive_federated_update():
    update = FederatedUpdate(
        device_id="device_001",
        model_gradients={"layer1": [0.1, 0.2], "layer2": [0.3, 0.4]},
        num_samples=100,
        timestamp="2023-01-01T00:00:00Z"
    )
    response = client.post("/api/federated/update", json=update.dict())
    assert response.status_code == 200
    assert "update_id" in response.json()


def test_upload_model():
    model_data = b"fake_model_data"
    response = client.post("/api/models/upload", json={
        "version_id": "v1.1.0",
        "model_data": model_data.hex(),
        "description": "Updated model"
    })
    assert response.status_code == 200
    assert "version_id" in response.json()


def test_download_model():
    # First upload a model
    model_data = b"fake_model_data"
    client.post("/api/models/upload", json={
        "version_id": "v1.1.0",
        "model_data": model_data.hex(),
        "description": "Updated model"
    })

    response = client.get(
        "/api/models/download?device_id=device_001&model_version=v1.1.0")
    assert response.status_code == 200
    assert "model_data" in response.json()


def test_get_analytics():
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "time_series" in data
    assert "bias_trends" in data
    assert "device_stats" in data
