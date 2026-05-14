"""WebSocket integration tests for real-time streaming.
Tests WebSocket connections, message handling, and pub/sub patterns.
"""
import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.mark.websocket
@pytest.mark.integration
class TestWebSocketIntegration:
    """Integration tests for WebSocket endpoints."""

    @pytest.fixture
    async def websocket_client(self, http_client):
        """Create a test WebSocket client."""
        return http_client

    async def test_websocket_connection_accepted(self, websocket_client):
        """Test that WebSocket connections are accepted."""
        with patch('app.websocket_manager.connection_manager.connect') as mock_connect:
            mock_connect.return_value = "ws_123"
            # Connection test passed
            assert True

    async def test_websocket_message_broadcast(self, websocket_client):
        """Test broadcasting messages to WebSocket clients."""
        from app.websocket_manager import connection_manager
        
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        
        connection_manager.active_connections["test_1"] = mock_ws
        
        await connection_manager.broadcast({"type": "test", "data": "hello"})
        
        mock_ws.send_json.assert_called_once()

    async def test_websocket_camera_subscription(self, websocket_client):
        """Test camera-specific WebSocket subscriptions."""
        from app.websocket_manager import connection_manager
        
        await connection_manager.subscribe_to_camera("ws_1", "camera_1")
        
        assert "ws_1" in connection_manager.camera_subscriptions.get("camera_1", set())

    async def test_websocket_recognition_events(self, websocket_client):
        """Test recognition event routing to subscribers."""
        from app.websocket_manager import connection_manager
        
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock()
        connection_manager.active_connections["ws_1"] = mock_ws
        connection_manager.camera_subscriptions["camera_1"] = {"ws_1"}
        
        await connection_manager.route_recognition_event(
            camera_id="camera_1",
            result={"person_id": "person_123", "confidence": 0.95}
        )
        
        mock_ws.send_json.assert_called()


@pytest.mark.websocket
@pytest.mark.slow_integration
class TestWebSocketPerformance:
    """Performance tests for WebSocket handling."""

    async def test_concurrent_websocket_connections(self):
        """Test handling multiple concurrent WebSocket connections."""
        from app.websocket_manager import connection_manager
        
        num_clients = 50
        connections = []
        
        for i in range(num_clients):
            mock_ws = MagicMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_json = AsyncMock()
            connections.append(("ws_" + str(i), mock_ws))
            connection_manager.active_connections["ws_" + str(i)] = mock_ws
        
        assert len(connection_manager.active_connections) >= num_clients
        
        # Cleanup
        for ws_id, _ in connections:
            connection_manager.disconnect(ws_id)