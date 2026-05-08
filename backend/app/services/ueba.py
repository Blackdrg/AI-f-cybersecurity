"""User and Entity Behavior Analytics (UEBA) for AI-f"""

import numpy as np
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import asyncio

class UEBABase:
    """Base class for UEBA analytics."""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.baseline_profiles = {}
        self.anomaly_threshold = 2.5  # Z-score threshold
        
    def update_profile(self, user_id: str, features: Dict[str, float]):
        """Update user behavioral profile."""
        if user_id not in self.baseline_profiles:
            self.baseline_profiles[user_id] = {
                'features': defaultdict(lambda: deque(maxlen=self.window_size)),
                'mean': {},
                'std': {},
                'last_seen': datetime.utcnow()
            }
        
        profile = self.baseline_profiles[user_id]
        for feature, value in features.items():
            profile['features'][feature].append(value)
            
            # Update statistics
            values = list(profile['features'][feature])
            if len(values) >= 10:
                profile['mean'][feature] = np.mean(values)
                profile['std'][feature] = np.std(values) + 1e-8
        
        profile['last_seen'] = datetime.utcnow()


class LoginBehaviorAnalyzer(UEBABase):
    """Analyzes login patterns for anomalies."""
    
    def check_anomaly(self, user_id: str, login_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for anomalous login behavior."""
        profile = self.baseline_profiles.get(user_id, {})
        
        features = {
            'hour_of_day': login_data.get('hour', 0),
            'day_of_week': login_data.get('day', 0),
            'geohash': hash(login_data.get('location', 'unknown')) % 1000,
            'session_duration': login_data.get('duration', 0)
        }
        
        # Update profile
        self.update_profile(user_id, features)
        
        # Calculate anomaly score
        anomaly_score = 0.0
        anomalies = []
        
        for feature, value in features.items():
            if feature in profile.get('mean', {}):
                mean = profile['mean'].get(feature, 0)
                std = profile['std'].get(feature, 1)
                
                z_score = abs(value - mean) / std
                if z_score > self.anomaly_threshold:
                    anomaly_score = max(anomaly_score, z_score)
                    anomalies.append({
                        'feature': feature,
                        'value': value,
                        'expected': mean,
                        'z_score': z_score
                    })
        
        return {
            'user_id': user_id,
            'score': anomaly_score,
            'is_anomaly': anomaly_score > self.anomaly_threshold,
            'anomalies': anomalies,
            'timestamp': datetime.utcnow().isoformat()
        }


class RecognitionPatternAnalyzer(UEBABase):
    """Analyzes face recognition patterns."""
    
    def check_anomaly(self, user_id: str, recognition_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for anomalous recognition behavior."""
        features = {
            'confidence': recognition_data.get('confidence', 0),
            'latency': recognition_data.get('latency', 0),
            'false_accept_rate': recognition_data.get('far', 0),
            'enrollment_count': recognition_data.get('enrollment_count', 0)
        }
        
        profile = self.baseline_profiles.get(user_id, {})
        self.update_profile(user_id, features)
        
        anomaly_score = 0.0
        anomalies = []
        
        for feature, value in features.items():
            if feature in profile.get('mean', {}):
                mean = profile['mean'].get(feature, 0)
                std = profile['std'].get(feature, 1)
                
                z_score = abs(value - mean) / std
                if z_score > self.anomaly_threshold:
                    anomaly_score = max(anomaly_score, z_score)
                    anomalies.append({
                        'feature': feature,
                        'value': value,
                        'expected': mean,
                        'z_score': z_score
                    })
        
        return {
            'user_id': user_id,
            'score': anomaly_score,
            'is_anomaly': anomaly_score > self.anomaly_threshold,
            'anomalies': anomalies
        }


class UEBAEngine:
    """Combined UEBA analytics engine."""
    
    def __init__(self):
        self.login_analyzer = LoginBehaviorAnalyzer()
        self.recognition_analyzer = RecognitionPatternAnalyzer()
        self.alerts = deque(maxlen=10000)
        
    async def analyze_event(self, event_type: str, user_id: str, data: Dict) -> Optional[Dict]:
        """Analyze an event for behavioral anomalies."""
        if event_type == 'login':
            result = self.login_analyzer.check_anomaly(user_id, data)
        elif event_type == 'recognition':
            result = self.recognition_analyzer.check_anomaly(user_id, data)
        else:
            return None
        
        if result.get('is_anomaly'):
            self.alerts.append(result)
            await self._trigger_alert(result)
        
        return result
    
    async def _trigger_alert(self, alert: Dict):
        """Trigger security alert for anomaly."""
        # Log for SOAR integration
        print(f"UEBA ALERT: {alert}")
    
    def get_user_risk_score(self, user_id: str) -> float:
        """Get aggregate risk score for user."""
        scores = [
            a.get('score', 0) 
            for a in self.alerts 
            if a.get('user_id') == user_id
        ]
        return np.mean(scores) if scores else 0.0
    
    def get_security_dashboard(self) -> Dict:
        """Get UEBA security dashboard data."""
        recent_alerts = list(self.alerts)[-100:]
        
        return {
            'total_users': len(self.login_analyzer.baseline_profiles),
            'recent_alerts': len(recent_alerts),
            'high_risk_users': [
                {'user_id': uid, 'risk': self.get_user_risk_score(uid)}
                for uid in self.login_analyzer.baseline_profiles
                if self.get_user_risk_score(uid) > 2.0
            ],
            'anomaly_trend': len([a for a in recent_alerts if a.get('score', 0) > 3.0])
        }


# Global UEBA instance
ueba = UEBAEngine()


if __name__ == "__main__":
    async def demo():
        # Simulate login events
        for i in range(20):
            await ueba.analyze_event('login', 'user1', {
                'hour': 10,
                'day': 1,
                'location': 'US-NYC',
                'duration': 300
            })
        
        # Anomalous login
        result = await ueba.analyze_event('login', 'user1', {
            'hour': 3,  # Unusual hour
            'day': 1,
            'location': 'RU-MOW',  # Different country
            'duration': 300
        })
        
        print(f"Anomaly detected: {result}")
        print(f"Dashboard: {ueba.get_security_dashboard()}")
    
    asyncio.run(demo())