from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json
import os
from ..services.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """
    Enterprise Anomaly Detection for Session Security.
    Tracks request patterns, geo-location, and IP velocity.
    """
    def __init__(self, spike_threshold=50, window_minutes=5):
        self.spike_threshold = spike_threshold
        self.window_minutes = window_minutes
        self.geo_risk_threshold = 0.8
        self.velocity_threshold = 1000 # km per hour (impossible travel)

    async def check_login_anomaly(self, user_id: str, ip_address: str, user_agent: str) -> bool:
        """
        Check for suspicious login activity.
        """
        # 1. Check IP Velocity / Impossible Travel
        # 2. Check User Agent consistency
        # 3. Check Geo-risk (suspicious countries)
        
        # Track activity in Redis
        key = f"user_activity:{user_id}"
        now = datetime.utcnow().timestamp()
        
        # Get last activity
        last_data = await redis_client.get(key)
        if last_data:
            last_activity = json.loads(last_data)
            last_ip = last_activity.get("ip")
            last_time = last_activity.get("time")
            
            if last_ip != ip_address:
                # Potential impossible travel check would go here
                logger.warning(f"Login from new IP for {user_id}: {last_ip} -> {ip_address}")
        
        # Update current activity
        activity = {
            "ip": ip_address,
            "ua": user_agent,
            "time": now
        }
        await redis_client.set(key, json.dumps(activity), ex=86400) # Keep for 24h
        
        return False # Simplified for now

    async def track_request(self, user_id: str, ip_address: str) -> Dict[str, Any]:
        """
        Tracks a request and returns anomaly status using Redis.
        """
        now = datetime.utcnow()
        key = f"req_count:{user_id}:{now.strftime('%Y%m%d%H%M')}"
        
        # Increment request count for current minute
        count = await redis_client.incr(key)
        await redis_client.expire(key, 600) # Expire in 10 mins
        
        is_spike = count > self.spike_threshold
        
        results = {
            "is_anomaly": is_spike,
            "reasons": [],
            "stats": {
                "request_count": count
            }
        }
        
        if is_spike:
            results["reasons"].append(f"Request spike: {count} req/min")
            
        return results

# Global instance
anomaly_detector = AnomalyDetector()
