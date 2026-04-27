"""
WebSocket Manager with Redis Pub/Sub Integration
Real-time event broadcasting to connected WebSocket clients
"""
import asyncio
import json
import logging
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections and Redis pub/sub event routing.
    Supports per-camera subscriptions and global event streams.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ConnectionManager()
        return cls._instance
    
    def __init__(self):
        # Active WebSocket connections: {websocket_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Subscriptions: {camera_id: Set[websocket_id]}
        self.camera_subscriptions: Dict[str, Set[str]] = {}
        # Connection metadata: {websocket_id: {user_id, org_id, subscriptions}}
        self.connection_meta: Dict[str, Dict] = {}
        self.pubsub_task = None
        self.running = False
    
    async def initialize(self):
        """Start the Redis Pub/Sub listener"""
        self.running = True
        from app.pubsub import pubsub_manager
        
        # Subscribe to internal event channels
        await pubsub_manager.subscribe("recognition_events", self._handle_recognition_event)
        await pubsub_manager.subscribe("alerts", self._handle_alert_event)
        await pubsub_manager.subscribe("system_health", self._handle_health_event)
        await pubsub_manager.subscribe("federated", self._handle_federated_event)
        
        logger.info("WebSocket ConnectionManager initialized with Redis pub/sub")
    
    async def connect(self, websocket: WebSocket, user_id: str = None, org_id: str = None):
        """Accept new WebSocket connection"""
        await websocket.accept()
        ws_id = str(id(websocket))
        self.active_connections[ws_id] = websocket
        self.connection_meta[ws_id] = {
            "user_id": user_id,
            "org_id": org_id,
            "connected_at": datetime.utcnow().isoformat(),
            "subscriptions": set(['global'])
        }
        logger.info(f"WebSocket connected: {ws_id} (user={user_id})")
        return ws_id
    
    def disconnect(self, websocket_id: str):
        """Clean up disconnected WebSocket"""
        if websocket_id in self.active_connections:
            del self.active_connections[websocket_id]
        if websocket_id in self.connection_meta:
            meta = self.connection_meta[websocket_id]
            # Unsubscribe from all camera channels
            for camera_id in meta.get('subscriptions', set()):
                if camera_id in self.camera_subscriptions:
                    self.camera_subscriptions[camera_id].discard(websocket_id)
            del self.connection_meta[websocket_id]
        logger.info(f"WebSocket disconnected: {websocket_id}")
    
    async def subscribe_to_camera(self, websocket_id: str, camera_id: str):
        """Subscribe a connection to a specific camera's events"""
        if websocket_id not in self.connection_meta:
            return
        
        meta = self.connection_meta[websocket_id]
        if camera_id not in meta['subscriptions']:
            meta['subscriptions'].add(camera_id)
        
        if camera_id not in self.camera_subscriptions:
            self.camera_subscriptions[camera_id] = set()
        self.camera_subscriptions[camera_id].add(websocket_id)
        
        logger.info(f"WebSocket {websocket_id} subscribed to camera {camera_id}")
    
    async def unsubscribe_from_camera(self, websocket_id: str, camera_id: str):
        """Unsubscribe from camera events"""
        if websocket_id in self.connection_meta:
            meta = self.connection_meta[websocket_id]
            meta['subscriptions'].discard(camera_id)
        if camera_id in self.camera_subscriptions:
            self.camera_subscriptions[camera_id].discard(websocket_id)
        logger.info(f"WebSocket {websocket_id} unsubscribed from camera {camera_id}")
    
    async def broadcast_to_camera_subscribers(self, camera_id: str, event: Dict):
        """Send event to all WebSockets subscribed to a camera"""
        if camera_id not in self.camera_subscriptions:
            return
        
        disconnected = []
        for ws_id in self.camera_subscriptions[camera_id]:
            if ws_id in self.active_connections:
                try:
                    await self.active_connections[ws_id].send_json(event)
                except Exception as e:
                    logger.error(f"Send to {ws_id} failed: {e}")
                    disconnected.append(ws_id)
        
        for ws_id in disconnected:
            self.disconnect(ws_id)
    
    async def broadcast_global(self, event: Dict):
        """Broadcast to all connected WebSocket clients"""
        disconnected = []
        for ws_id, ws in self.active_connections.items():
            try:
                await ws.send_json(event)
            except Exception as e:
                logger.error(f"Global broadcast to {ws_id} failed: {e}")
                disconnected.append(ws_id)
        
        for ws_id in disconnected:
            self.disconnect(ws_id)
    
    # Internal Redis event handlers
    async def _handle_recognition_event(self, event: Dict):
        """Route recognition events to WebSocket subscribers"""
        camera_id = event.get('camera_id')
        if camera_id:
            await self.broadcast_to_camera_subscribers(camera_id, event)
        # Also broadcast globally if needed
        # await self.broadcast_global(event)
    
    async def _handle_alert_event(self, event: Dict):
        """Route alert events (spoof, policy violations)"""
        org_id = event.get('org_id')
        if org_id:
            await self.broadcast_to_org_subscribers(org_id, event)
    
    async def _handle_health_event(self, event: Dict):
        """Route health metrics"""
        await self.broadcast_global(event)
    
    async def _handle_federated_event(self, event: Dict):
        """Route federated learning events"""
        await self.broadcast_global(event)
    
    async def broadcast_to_org_subscribers(self, org_id: str, event: Dict):
        """Broadcast to all connections for a specific organization"""
        for ws_id, meta in self.connection_meta.items():
            if meta.get('org_id') == org_id:
                if ws_id in self.active_connections:
                    try:
                        await self.active_connections[ws_id].send_json(event)
                    except:
                        self.disconnect(ws_id)
    
    async def get_connection_stats(self) -> Dict:
        """Return stats for monitoring dashboard"""
        return {
            "total_connections": len(self.active_connections),
            "organizations": len(set(m.get('org_id') for m in self.connection_meta.values())),
            "camera_subscriptions": {cam: len(clients) for cam, clients in self.camera_subscriptions.items()}
        }
    
    def get_active_connections_count(self) -> int:
        return len(self.active_connections)


# Global manager instance
connection_manager = ConnectionManager.get_instance()
