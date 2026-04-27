"""
Redis Pub/Sub Event Bus
Real-time event distribution to WebSocket connections and other services
"""
import asyncio
import json
import redis.asyncio as redis
import logging
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class RedisPubSubManager:
    """
    Central event bus using Redis Pub/Sub.
    
    Channels:
      - recognition_events: Real-time face recognition results
      - alerts: Security alerts, spoof attempts, policy violations
      - system_health: Service health pings, metrics
      - federated: Federated learning round coordination
      - sessions: Session lifecycle events
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = RedisPubSubManager()
        return cls._instance
    
    def __init__(self):
        self.redis_url = None
        self.redis_client = None
        self.pubsub = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.running = False
        self.listener_task = None
    
    async def initialize(self, redis_url: str):
        """Initialize Redis connection and start listener"""
        self.redis_url = redis_url
        self.redis_client = await redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20
        )
        self.pubsub = self.redis_client.pubsub()
        self.running = True
        self.listener_task = asyncio.create_task(self._listen())
        logger.info("Redis PubSub manager initialized")
    
    async def _listen(self):
        """Background task listening for messages on subscribed channels"""
        while self.running:
            try:
                async for message in self.pubsub.listen():
                    if message['type'] == 'message':
                        channel = message['channel']
                        data = json.loads(message['data'])
                        
                        # Call registered handlers
                        if channel in self.subscribers:
                            for handler in self.subscribers[channel]:
                                try:
                                    asyncio.create_task(handler(data))
                                except Exception as e:
                                    logger.error(f"PubSub handler error: {e}")
            except Exception as e:
                logger.error(f"PubSub listener error: {e}")
                await asyncio.sleep(1)
    
    async def publish(self, channel: str, data: Dict[str, Any]):
        """Publish event to channel"""
        try:
            payload = json.dumps({
                **data,
                "timestamp": datetime.utcnow().isoformat(),
                "event_id": str(uuid.uuid4())
            })
            await self.redis_client.publish(channel, payload)
            logger.debug(f"Published to {channel}: {data.get('type', 'event')}")
        except Exception as e:
            logger.error(f"Publish failed to {channel}: {e}")
            raise
    
    async def subscribe(self, channel: str, handler: Callable):
        """Subscribe a handler to a channel"""
        if channel not in self.subscribers:
            self.subscribers[channel] = []
            await self.pubsub.subscribe(channel)
        self.subscribers[channel].append(handler)
        logger.info(f"Subscribed to channel: {channel}")
    
    async def unsubscribe(self, channel: str, handler: Callable = None):
        """Unsubscribe handler (or all handlers for channel)"""
        if handler is None:
            # Unsubscribe all from channel
            if channel in self.subscribers:
                await self.pubsub.unsubscribe(channel)
                del self.subscribers[channel]
        else:
            # Remove specific handler
            if channel in self.subscribers:
                self.subscribers[channel].remove(handler)
                if not self.subscribers[channel]:
                    await self.pubsub.unsubscribe(channel)
                    del self.subscribers[channel]
    
    async def close(self):
        """Clean shutdown"""
        self.running = False
        if self.listener_task:
            self.listener_task.cancel()
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("PubSub manager closed")


# Global instance
pubsub_manager = RedisPubSubManager.get_instance()


# Helper functions for common events
async def publish_recognition_event(camera_id: str, faces: List[Dict], processing_latency_ms: float):
    """Publish face recognition event"""
    await pubsub_manager.publish("recognition_events", {
        "type": "recognition",
        "camera_id": camera_id,
        "faces": faces,
        "processing_latency_ms": processing_latency_ms,
        "source": "inference"
    })


async def publish_spoof_alert(camera_id: str, spoof_score: float, details: Dict):
    """Publish spoof detection alert"""
    await pubsub_manager.publish("alerts", {
        "type": "spoof_attempt",
        "severity": "high",
        "camera_id": camera_id,
        "spoof_score": spoof_score,
        "details": details,
        "source": "spoof_detector"
    })


async def publish_policy_violation(user_id: str, resource: str, reason: str):
    """Publish RBAC policy violation"""
    await pubsub_manager.publish("alerts", {
        "type": "policy_violation",
        "severity": "medium",
        "user_id": user_id,
        "resource": resource,
        "reason": reason,
        "source": "policy_engine"
    })


async def publish_system_health(status: str, metrics: Dict):
    """Publish system health status"""
    await pubsub_manager.publish("system_health", {
        "type": "health",
        "status": status,
        "metrics": metrics,
        "source": "monitor"
    })


async def publish_federated_round(round_id: str, status: str, participants: int):
    """Publish federated learning round event"""
    await pubsub_manager.publish("federated", {
        "type": "round_update",
        "round_id": round_id,
        "status": status,
        "participants": participants,
        "source": "federated_learning"
    })
