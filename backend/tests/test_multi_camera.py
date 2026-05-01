from app.schemas import MultiCameraRequest
import pytest
import numpy as np

def test_process_multi_camera():
    """Process multi-camera request with mocked dependencies."""
    from app.api.stream_recognize import process_multi_camera
    from unittest.mock import MagicMock, AsyncMock, patch

    request = MultiCameraRequest(
        camera_ids=["cam1", "cam2"],
        sync_timestamps=["2023-01-01T00:00:00", "2023-01-01T00:00:01"],  # ISO format strings
        streams=["ZmFrZV9iYXNlNjRfaW1hZ2Ux", "ZmFrZV9iYXNlNjRfaW1hZ2Uy"]
    )

    # Create mock detector/embedder as regular mocks
    mock_detector = MagicMock()
    mock_detector.detect_faces.return_value = [
        {'bbox': [10, 10, 50, 50], 'landmarks': np.array([[15, 15], [35, 15], [25, 35]])}
    ]
    mock_detector.align_face.return_value = np.zeros((112, 112, 3), dtype=np.uint8)
    
    mock_embedder = MagicMock()
    mock_embedder.get_embedding.return_value = np.array([0.1] * 512, dtype=np.float32)

    # Mock DB
    mock_db = MagicMock()
    mock_db.recognize_faces = AsyncMock(return_value=[])

    # Patch the module-level globals
    with patch('app.api.stream_recognize.detector', mock_detector):
        with patch('app.api.stream_recognize.embedder', mock_embedder):
            # Run async function
            import asyncio
            result = asyncio.run(process_multi_camera(request, mock_db))
            assert isinstance(result, list)

def test_websocket_multi_camera_message():
    """Test WebSocket multi-camera message handling."""
    assert True  # Placeholder for WebSocket test"
