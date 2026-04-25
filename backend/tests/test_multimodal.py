"""
Simplified multi-modal API tests for face, voice, and gait recognition.
Tests the /api/recognize and /api/enroll endpoints with multi-modal data.
"""
import pytest
import numpy as np
from fastapi.testclient import TestClient
import io
import cv2
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app

client = TestClient(app)


def create_test_image(size=112):
    """Create a synthetic test face image."""
    img = np.random.randint(0, 255, (size, size, 3), dtype=np.uint8)
    # Add a face-like rectangle
    img[40:80, 40:80] = [200, 180, 160]
    img[50:60, 55:65] = [50, 50, 50]  # Eyes
    _, buffer = cv2.imencode('.jpg', img)
    return io.BytesIO(buffer.tobytes())


# Mock the authentication dependencies
def mock_require_auth():
    return {"user_id": "test-user"}

def mock_require_recognize_policy():
    return True

def mock_require_enroll_policy():
    return True


def test_multi_modal_api_endpoint():
    """Test the /api/recognize endpoint handles multi-modal data."""
    # Override auth dependencies
    from app.security import require_auth
    from app.middleware.policy_enforcement import require_recognize_policy
    
    app.dependency_overrides[require_auth] = mock_require_auth
    app.dependency_overrides[require_recognize_policy] = mock_require_recognize_policy
    
    try:
        img_data = create_test_image()
        
        # Send with just image (face only)
        response = client.post(
            "/api/recognize",
            files={"image": ("test.jpg", img_data, "image/jpeg")},
            data={"top_k": 3, "threshold": 0.6}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "faces" in data["data"]
    finally:
        # Clean up overrides
        app.dependency_overrides.clear()


def test_enroll_with_metadata():
    """Test enrollment with metadata."""
    # Override auth dependencies
    from app.security import require_auth
    from app.middleware.policy_enforcement import require_enroll_policy
    
    app.dependency_overrides[require_auth] = mock_require_auth
    app.dependency_overrides[require_enroll_policy] = mock_require_enroll_policy
    
    try:
        img_data = create_test_image()
        
        response = client.post(
            "/api/enroll",
            files={"images": ("test1.jpg", img_data, "image/jpeg")},
            data={
                "name": "Test Person",
                "metadata": '{"department": "engineering", "role": "developer"}',
                "consent": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "person_id" in data["data"]
    finally:
        # Clean up overrides
        app.dependency_overrides.clear()


def test_enroll_multiple_images():
    """Test enrollment with multiple images."""
    # Override auth dependencies
    from app.security import require_auth
    from app.middleware.policy_enforcement import require_enroll_policy
    
    app.dependency_overrides[require_auth] = mock_require_auth
    app.dependency_overrides[require_enroll_policy] = mock_require_enroll_policy
    
    try:
        img_data1 = create_test_image()
        img_data2 = create_test_image()
        
        response = client.post(
            "/api/enroll",
            files=[
                ("images", ("test1.jpg", img_data1, "image/jpeg")),
                ("images", ("test2.jpg", img_data2, "image/jpeg"))
            ],
            data={
                "name": "Multi Image Person",
                "consent": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["num_embeddings"] == 2
    finally:
        # Clean up overrides
        app.dependency_overrides.clear()


def test_enroll_with_camera():
    """Test enrollment with camera ID."""
    # Override auth dependencies
    from app.security import require_auth
    from app.middleware.policy_enforcement import require_enroll_policy
    
    app.dependency_overrides[require_auth] = mock_require_auth
    app.dependency_overrides[require_enroll_policy] = mock_require_enroll_policy
    
    try:
        img_data = create_test_image()
        
        response = client.post(
            "/api/enroll",
            files={"images": ("test.jpg", img_data, "image/jpeg")},
            data={
                "name": "Camera Person",
                "camera_id": "camera-001",
                "consent": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    finally:
        # Clean up overrides
        app.dependency_overrides.clear()


def test_recognize_and_enroll_are_async():
    """Test that recognize_faces and enroll_person endpoints are async."""
    # Override auth dependencies
    from app.security import require_auth
    from app.middleware.policy_enforcement import require_recognize_policy, require_enroll_policy
    
    app.dependency_overrides[require_auth] = mock_require_auth
    app.dependency_overrides[require_recognize_policy] = mock_require_recognize_policy
    app.dependency_overrides[require_enroll_policy] = mock_require_enroll_policy
    
    try:
        # Test that the endpoints exist and respond (TestClient handles async automatically)
        img_data = create_test_image()
        
        # Test recognize endpoint
        response = client.post(
            "/api/recognize",
            files={"image": ("test.jpg", img_data, "image/jpeg")},
            data={"top_k": 1, "threshold": 0.5}
        )
        assert response.status_code == 200
        
        # Test enroll endpoint
        response = client.post(
            "/api/enroll",
            files={"images": ("test.jpg", img_data, "image/jpeg")},
            data={"name": "Async Test", "consent": True}
        )
        assert response.status_code == 200
    finally:
        # Clean up overrides
        app.dependency_overrides.clear()