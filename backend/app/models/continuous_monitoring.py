"""
Continuous Identity Monitoring Module.

Implements persistent identity awareness beyond initial authentication.
Tracks behavioral patterns, detects drift, and maintains session continuity.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
import base64
import hashlib
import threading
from collections import deque


class SessionStatus(Enum):
    ACTIVE = 'active'
    EXPIRED = 'expired'
    SUSPENDED = 'suspended'
    TERMINATED = 'terminated'


@dataclass
class SessionContext:
    session_id: str
    person_id: str
    device_id: str
    start_time: str
    last_active: str
    status: SessionStatus
    confidence_history: List[float]
    location_history: List[Dict[str, Any]]
    behavioral_baseline: Dict[str, float]
    risk_score: float
    metadata: Dict[str, Any]
    
    def to_dict(self):
        d = asdict(self)
        d['status'] = self.status.value
        return d


@dataclass
class BehavioralDrift:
    drift_type: str
    severity: str
    confidence_change: float
    baseline_deviation: float
    affected_sessions: List[str]
    timestamp: str
    recommended_action: str


class SessionContinuityTracker:
    def __init__(self, session_timeout_minutes: int = 30):
        self.active_sessions: Dict[str, SessionContext] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.behavioral_baselines: Dict[str, Dict[str, float]] = {}
        self.drift_alerts: List[BehavioralDrift] = []
        self.lock = threading.Lock()
        self.cross_camera_mappings: Dict[str, List[str]] = {}
        
    def create_session(
        self,
        person_id: str,
        device_id: str,
        initial_confidence: float,
        location: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionContext:
        session_id = f'session:{hashlib.sha256(f"{person_id}{device_id}{datetime.now()}".encode()).hexdigest()[:16]}'
        now = datetime.now(timezone.utc).isoformat()
        
        baseline = self._get_behavioral_baseline(person_id)
        
        session = SessionContext(
            session_id=session_id,
            person_id=person_id,
            device_id=device_id,
            start_time=now,
            last_active=now,
            status=SessionStatus.ACTIVE,
            confidence_history=[initial_confidence],
            location_history=[location] if location else [],
            behavioral_baseline=baseline,
            risk_score=0.0,
            metadata=metadata or {},
        )
        
        with self.lock:
            self.active_sessions[session_id] = session
        
        return session
    
    def update_session(
        self,
        session_id: str,
        confidence: float,
        location: Optional[Dict[str, Any]] = None,
        behavioral_signals: Optional[Dict[str, float]] = None
    ) -> Tuple[bool, Optional[BehavioralDrift]]:
        with self.lock:
            if session_id not in self.active_sessions:
                return False, None
            
            session = self.active_sessions[session_id]
            
            # Check timeout
            last_active = datetime.fromisoformat(session.last_active.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) - last_active > self.session_timeout:
                session.status = SessionStatus.EXPIRED
                return False, None
            
            # Update session
            session.last_active = datetime.now(timezone.utc).isoformat()
            session.confidence_history.append(confidence)
            if location:
                session.location_history.append(location)
            
            # Check for behavioral drift
            drift = None
            if behavioral_signals:
                drift = self._detect_behavioral_drift(session, behavioral_signals)
                if drift:
                    self.drift_alerts.append(drift)
            
            # Update risk score
            session.risk_score = self._calculate_risk_score(session)
            
            return True, drift
    
    def _detect_behavioral_drift(
        self,
        session: SessionContext,
        current_signals: Dict[str, float]
    ) -> Optional[BehavioralDrift]:
        baseline = session.behavioral_baseline
        
        drifts = []
        for key, current_val in current_signals.items():
            if key in baseline:
                baseline_val = baseline[key]
                deviation = abs(current_val - baseline_val) / (baseline_val + 1e-8)
                
                if deviation > 0.3:  # 30% deviation threshold
                    drifts.append({
                        'feature': key,
                        'deviation': deviation,
                        'current': current_val,
                        'baseline': baseline_val
                    })
        
        if drifts:
            max_deviation = max(d['deviation'] for d in drifts)
            severity = 'high' if max_deviation > 0.5 else 'medium' if max_deviation > 0.3 else 'low'
            
            return BehavioralDrift(
                drift_type='behavioral_anomaly',
                severity=severity,
                confidence_change=session.confidence_history[-1] - session.confidence_history[0] if session.confidence_history else 0,
                baseline_deviation=max_deviation,
                affected_sessions=[session.session_id],
                timestamp=datetime.now(timezone.utc).isoformat(),
                recommended_action='trigger_reauthentication' if severity == 'high' else 'increase_monitoring'
            )
        
        return None
    
    def _calculate_risk_score(self, session: SessionContext) -> float:
        risk = 0.0
        
        # Confidence variance
        if len(session.confidence_history) > 1:
            conf_array = np.array(session.confidence_history)
            risk += np.std(conf_array) * 0.3
        
        # Location changes
        if len(session.location_history) > 1:
            risk += min(len(session.location_history) * 0.05, 0.3)
        
        # Time since start
        start = datetime.fromisoformat(session.start_time.replace('Z', '+00:00'))
        duration = (datetime.now(timezone.utc) - start).total_seconds() / 3600  # hours
        risk += min(duration * 0.01, 0.2)
        
        return min(risk, 1.0)
    
    def _get_behavioral_baseline(self, person_id: str) -> Dict[str, float]:
        if person_id in self.behavioral_baselines:
            return self.behavioral_baselines[person_id]
        
        return {
            'walking_speed': 1.2,
            'posture_angle': 0.0,
            'interaction_frequency': 0.5
        }
    
    def link_cross_camera_identity(
        self,
        session_id_1: str,
        session_id_2: str,
        confidence: float
    ) -> bool:
        with self.lock:
            if session_id_1 not in self.active_sessions or session_id_2 not in self.active_sessions:
                return False
            
            session_1 = self.active_sessions[session_id_1]
            session_2 = self.active_sessions[session_id_2]
            
            if session_1.person_id != session_2.person_id:
                return False
            
            key = f"{session_1.device_id}:{session_2.device_id}"
            if key not in self.cross_camera_mappings:
                self.cross_camera_mappings[key] = []
            
            self.cross_camera_mappings[key].append({
                'session_1': session_id_1,
                'session_2': session_id_2,
                'confidence': confidence,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            return True
    
    def get_active_sessions(self, person_id: Optional[str] = None) -> List[SessionContext]:
        with self.lock:
            sessions = [s for s in self.active_sessions.values() if s.status == SessionStatus.ACTIVE]
            if person_id:
                sessions = [s for s in sessions if s.person_id == person_id]
            return sessions
    
    def expire_session(self, session_id: str) -> bool:
        with self.lock:
            if session_id in self.active_sessions:
                self.active_sessions[session_id].status = SessionStatus.EXPIRED
                return True
            return False
    
    def get_session(self, session_id: str) -> Optional[SessionContext]:
        return self.active_sessions.get(session_id)
    
    def get_continuity_report(self) -> Dict[str, Any]:
        with self.lock:
            active_count = len([s for s in self.active_sessions.values() if s.status == SessionStatus.ACTIVE])
            
            return {
                'active_sessions': active_count,
                'total_sessions': len(self.active_sessions),
                'cross_camera_links': len(self.cross_camera_mappings),
                'drift_alerts': len(self.drift_alerts),
                'sessions_by_person': self._get_sessions_by_person(),
                'recent_drifts': [asdict(d) for d in self.drift_alerts[-10:]]
            }
    
    def _get_sessions_by_person(self) -> Dict[str, int]:
        counts = {}
        for session in self.active_sessions.values():
            counts[session.person_id] = counts.get(session.person_id, 0) + 1
        return counts


class PassiveReauthManager:
    def __init__(self, reauth_interval_seconds: int = 300):
        self.reauth_interval = timedelta(seconds=reauth_interval_seconds)
        self.last_reauth: Dict[str, datetime] = {}
    
    def check_reauth_required(self, session_id: str) -> bool:
        if session_id not in self.last_reauth:
            return True
        
        elapsed = datetime.now(timezone.utc) - self.last_reauth[session_id]
        return elapsed > self.reauth_interval
    
    def record_reauth(self, session_id: str):
        self.last_reauth[session_id] = datetime.now(timezone.utc)


class PrivacyAwareSessionManager:
    def __init__(self, default_session_timeout: int = 900):
        self.session_tracker = SessionContinuityTracker(
            session_timeout_minutes=default_session_timeout // 60
        )
        self.reauth_manager = PassiveReauthManager()
        self.privacy_policies: Dict[str, Dict[str, Any]] = {}
    
    def start_authenticated_session(
        self,
        person_id: str,
        device_id: str,
        confidence: float,
        jurisdiction: str,
        privacy_level: str = 'standard'
    ) -> SessionContext:
        metadata = {
            'jurisdiction': jurisdiction,
            'privacy_level': privacy_level,
            'privacy_aware': True
        }
        
        session = self.session_tracker.create_session(
            person_id=person_id,
            device_id=device_id,
            initial_confidence=confidence,
            metadata=metadata
        )
        
        self._apply_privacy_policy(session, privacy_level)
        
        return session
    
    def _apply_privacy_policy(self, session: SessionContext, privacy_level: str):
        policies = {
            'strict': {'timeout': 300, 'reauth': True, 'location_tracking': False},
            'standard': {'timeout': 900, 'reauth': True, 'location_tracking': True},
            'relaxed': {'timeout': 1800, 'reauth': False, 'location_tracking': True}
        }
        
        policy = policies.get(privacy_level, policies['standard'])
        session.metadata['privacy_policy'] = policy
    
    def update_session_with_privacy_check(
        self,
        session_id: str,
        confidence: float,
        location: Optional[Dict[str, Any]] = None,
        behavioral_signals: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        session = self.session_tracker.get_session(session_id)
        if not session:
            return {'success': False, 'error': 'session_not_found'}
        
        policy = session.metadata.get('privacy_policy', {})
        if not policy.get('location_tracking', True) and location:
            location = None
        
        success, drift = self.session_tracker.update_session(
            session_id, confidence, location, behavioral_signals
        )
        
        reauth_required = self.reauth_manager.check_reauth_required(session_id)
        
        result = {
            'success': success,
            'reauth_required': reauth_required,
            'drift_detected': drift is not None
        }
        
        if drift:
            result['drift'] = asdict(drift)
        
        if reauth_required and success:
            self.reauth_manager.record_reauth(session_id)
            result['reauth_performed'] = True
        
        return result
    
    def get_privacy_aware_continuity_report(self) -> Dict[str, Any]:
        report = self.session_tracker.get_continuity_report()
        report['privacy_aware'] = True
        report['auto_expiry_enabled'] = True
        report['passive_reauth_enabled'] = True
        return report
    
    def terminate_session(self, session_id: str, reason: str = 'user_logout') -> bool:
        return self.session_tracker.expire_session(session_id)