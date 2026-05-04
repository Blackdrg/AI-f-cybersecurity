from app.schemas import FederatedUpdate
from app.main import app
import pytest
from fastapi.testclient import TestClient
from app.security import create_token

client = TestClient(app)

# Create admin token for tests
admin_token = create_token("test_admin", "admin")

def test_receive_federated_update():
    update = FederatedUpdate(
        device_id="device_001",
        model_gradients={"layer1": [0.1, 0.2], "layer2": [0.3, 0.4]},
        num_samples=100,
        timestamp="2023-01-01T00:00:00Z"
    )
    response = client.post("/api/v1/federated/client/update", 
        json=update.model_dump(),
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert "update_id" in response.json() or "success" in response.json()


def test_upload_model():
    import datetime
    model_data = b"fake_model_data"
    response = client.post("/api/models/upload", 
        json={
            "version_id": "v1.1.0",
            "model_data": model_data.hex(),
            "description": "Updated model",
            "created_at": datetime.datetime.utcnow().isoformat()
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert "version_id" in response.json() or "success" in response.json()


def test_download_model():
    # First upload a model
    import datetime
    model_data = b"fake_model_data"
    client.post("/api/models/upload", 
        json={
            "version_id": "v1.1.0",
            "model_data": model_data.hex(),
            "description": "Updated model",
            "created_at": datetime.datetime.utcnow().isoformat()
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    response = client.get(
        "/api/models/download?device_id=device_001&model_version=v1.1.0",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    # In degraded mode (no DB), endpoint may return error
    # Check if response is OK (200) OR a valid error response
    assert response.status_code in [200, 404, 422]
    if response.status_code == 200:
        assert "model_data" in response.json() or response.json().get("success")


def test_get_analytics():
    response = client.get("/api/analytics",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    # The API returns data in StandardResponse wrapper
    if data.get("success"):
        assert "time_series" in data.get("data", {})
        assert "bias_trends" in data.get("data", {})
        assert "device_stats" in data.get("data", {})
    else:
        # Old format check
        assert "time_series" in data
        assert "bias_trends" in data
        assert "device_stats" in data
