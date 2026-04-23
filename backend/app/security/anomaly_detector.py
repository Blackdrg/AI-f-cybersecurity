from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class AnomalyDetector:
    """
    Enterprise Anomaly Detection for API Abuse Protection.
    Tracks request patterns to detect spikes and multi-IP logins.
    """
    def __init__(self, spike_threshold=50, window_minutes=5):
        self.spike_threshold = spike_threshold
        self.window_minutes = window_minutes
        # In-memory storage (Should use Redis in production)
        self.request_history: Dict[str, List[datetime]] = {}
        self.user_ips: Dict[str, set] = {}

    def track_request(self, user_id: str, ip_address: str) -> Dict[str, Any]:
        """
        Tracks a request and returns anomaly status.
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        # Initialize if new
        if user_id not in self.request_history:
            self.request_history[user_id] = []
            self.user_ips[user_id] = set()
            
        # Add current request
        self.request_history[user_id].append(now)
        self.user_ips[user_id].add(ip_address)
        
        # Clean up old records
        self.request_history[user_id] = [t for t in self.request_history[user_id] if t > window_start]
        
        # Analyze
        request_count = len(self.request_history[user_id])
        ip_count = len(self.user_ips[user_id])
        
        is_spike = request_count > self.spike_threshold
        is_multi_ip = ip_count > 3  # Alert if > 3 IPs in 5 mins
        
        results = {
            "is_anomaly": is_spike or is_multi_ip,
            "reasons": [],
            "stats": {
                "request_count": request_count,
                "ip_count": ip_count
            }
        }
        
        if is_spike:
            results["reasons"].append(f"Request spike: {request_count} in {self.window_minutes}m")
        if is_multi_ip:
            results["reasons"].append(f"Multi-IP login: {ip_count} unique IPs detected")
            
        return results

    def get_risk_score(self, user_id: str) -> float:
        """Returns a normalized risk score from 0.0 to 1.0."""
        if user_id not in self.request_history:
            return 0.0
            
        count = len(self.request_history[user_id])
        score = min(count / (self.spike_threshold * 2), 1.0)
        return score

# Global instance
anomaly_detector = AnomalyDetector()
