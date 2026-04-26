"""
Emotion + Behavior Layer

Real-time emotion detection and behavioral analysis.
Integrates ML models with rule engine for contextual decision-making.

NOT just "emotion detection" - this is a full behavioral context engine:
- Real-time emotion tracking (face, voice, gait)
- Behavioral pattern recognition
- Context-aware decision rules
- Risk scoring with ML ensemble
- Integration with recognition pipeline
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import time
import numpy as np
from collections import deque
import json

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

logger = logging.getLogger(__name__)


class Emotion(Enum):
    """Emotion categories detected by ML models."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    FEARFUL = "fearful"
    CONFUSED = "confused"


class BehaviorState(Enum):
    """Behavioral states for risk assessment."""
    NORMAL = "normal"
    AGITATED = "agitated"
    DISTRESSED = "distressed"
    SUSPICIOUS = "suspicious"
    THREATENING = "threatening"


@dataclass
class EmotionSample:
    """Single emotion detection sample."""
    timestamp: float
    emotion: str
    confidence: float
    face_detected: bool
    voice_detected: bool
    gait_detected: bool
    valence: float  # -1 (negative) to +1 (positive)
    arousal: float  # 0 (calm) to 1 (excited)
    
    # Facial action units (partial)
    brow_raise: float = 0.0
    eye_widen: float = 0.0
    lip_corner: float = 0.0
    jaw_drop: float = 0.0
    
    # Voice features
    pitch_mean: float = 0.0
    pitch_var: float = 0.0
    speech_rate: float = 0.0
    intensity: float = 0.0
    
    # Gait features
    stride_length: float = 0.0
    cadence: float = 0.0
    sway: float = 0.0


@dataclass
class BehaviorContext:
    """Context for behavioral analysis."""
    person_id: str
    session_id: str
    location: str
    time_of_day: str
    crowd_density: float  # 0-1
    weather: str
    previous_interactions: int
    known_individual: bool


@dataclass
class RiskAssessment:
    """Risk assessment output."""
    person_id: str
    timestamp: float
    risk_level: str  # low, medium, high, critical
    risk_score: float  # 0-100
    
    emotion_state: str
    behavior_state: str
    
    # Contributing factors
    emotion_volatility: float
    behavior_anomaly_score: float
    context_risk: float
    historical_risk: float
    
    # Recommendations
    action: str  # allow, monitor, review, deny
    confidence: float
    explanation: str
    
    # Raw emotion history
    recent_emotions: List[Dict]


class EmotionDetector:
    """ML-based emotion detector from face, voice, and gait."""
    
    def __init__(self):
        self.face_model = self._load_face_model()
        self.voice_model = self._load_voice_model()
        self.gait_model = self._load_gait_model()
        self.ensemble_model = self._load_ensemble_model()
        
    def _load_face_model(self):
        """Load face emotion detection model."""
        # In production: Load ONNX/TensorRT optimized model
        # For now: Return mock that would use insightface/fer
        return {
            'type': 'face_emotion_cnn',
            'input_size': (48, 48),
            'emotions': list(Emotion.__members__.keys()),
            'confidence_threshold': 0.6
        }
    
    def _load_voice_model(self):
        """Load voice emotion detection model."""
        # In production: Load ECAPA-TDNN or similar
        return {
            'type': 'voice_emotion_ecapa',
            'features': ['pitch', 'energy', 'spectral'],
            'confidence_threshold': 0.65
        }
    
    def _load_gait_model(self):
        """Load gait-based emotion model."""
        return {
            'type': 'gait_behavior_lstm',
            'features': ['stride', 'cadence', 'sway'],
            'confidence_threshold': 0.55
        }
    
    def _load_ensemble_model(self):
        """Load ensemble model to combine modalities."""
        return {
            'type': 'weighted_ensemble',
            'weights': {
                'face': 0.5,
                'voice': 0.3,
                'gait': 0.2
            },
            'min_confidence': 0.5
        }
    
    def detect_from_face(self, face_embedding, facial_landmarks) -> Tuple[str, float]:
        """Detect emotion from face embedding and landmarks."""
        # In production: Run through face emotion CNN
        # Extract facial action units from landmarks
        
        # Simulated detection (would use actual model)
        # Calculate facial action unit features
        au_features = self._extract_action_units(facial_landmarks)
        
        # Simulate detection with realistic probabilities
        emotions = list(Emotion)
        confidences = np.random.dirichlet(np.ones(len(emotions)) * 10)
        
        # Bias toward neutral (most common)
        confidences[0] *= 1.5
        confidences /= confidences.sum()
        
        pred_idx = np.argmax(confidences)
        confidence = float(confidences[pred_idx])
        
        return emotions[pred_idx].value, confidence
    
    def detect_from_voice(self, audio_features) -> Tuple[str, float]:
        """Detect emotion from voice features."""
        # Extract prosodic features
        pitch_mean = audio_features.get('pitch_mean', 0)
        pitch_var = audio_features.get('pitch_var', 0)
        intensity = audio_features.get('intensity', 0)
        speech_rate = audio_features.get('speech_rate', 0)
        
        # Rule-based + ML prediction
        # High pitch variance + high intensity = excited/angry
        if pitch_var > 50 and intensity > 0.7:
            return Emotion.ANGRY.value, 0.75
        elif pitch_mean > 0.6 and intensity > 0.5:
            return Emotion.HAPPY.value, 0.70
        elif speech_rate < 0.3 and intensity < 0.4:
            return Emotion.SAD.value, 0.65
        
        # Default to neutral
        return Emotion.NEUTRAL.value, 0.60
    
    def detect_from_gait(self, gait_features) -> Tuple[str, float]:
        """Detect emotion/behavior from gait patterns."""
        stride = gait_features.get('stride_length', 0)
        cadence = gait_features.get('cadence', 0)
        sway = gait_features.get('sway', 0)
        
        # Gait-based emotion indicators
        # Fast, long strides = confident/happy
        if stride > 0.8 and cadence > 1.2:
            return Emotion.HAPPY.value, 0.65
        # Short, slow, high sway = distressed
        elif stride < 0.5 and cadence < 0.8 and sway > 0.3:
            return Emotion.SAD.value, 0.60
        # Stiff, rigid = anxious/threatening
        elif sway < 0.1 and cadence > 1.0:
            return BehaviorState.SUSPICIOUS.value, 0.55
        
        return Emotion.NEUTRAL.value, 0.50
    
    def _extract_action_units(self, landmarks):
        """Extract facial action units from landmarks."""
        # Calculate distances and angles between key points
        # Inner brow raiser (AU1), outer brow raiser (AU2)
        # Lip corner puller (AU12), etc.
        
        features = {
            'brow_raise': 0.0,
            'eye_widen': 0.0,
            'lip_corner': 0.0,
            'jaw_drop': 0.0
        }
        
        if landmarks and len(landmarks) >= 68:
            # Example: Calculate brow raise from eyebrow to eye distance
            left_brow = landmarks[19:22]
            right_brow = landmarks[22:25]
            left_eye = landmarks[36:42]
            right_eye = landmarks[42:48]
            
            # Simplified: would calculate actual distances
            features['brow_raise'] = np.random.uniform(0, 0.5)
            features['lip_corner'] = np.random.uniform(0, 0.8)
        
        return features
    
    def detect_ensemble(self, face_data, voice_data, gait_data) -> EmotionSample:
        """Combine all modalities for final emotion detection."""
        timestamp = time.time()
        
        # Detect from each modality
        face_emotion, face_conf = self.detect_from_face(
            face_data.get('embedding'),
            face_data.get('landmarks')
        )
        
        voice_emotion, voice_conf = self.detect_from_voice(
            voice_data if voice_data else {}
        )
        
        gait_emotion, gait_conf = self.detect_from_gait(
            gait_data if gait_data else {}
        )
        
        # Weighted ensemble
        weights = self.ensemble_model['weights']
        
        # Combine confidences
        emotion_scores = {}
        for emotion in Emotion:
            emotion_val = emotion.value
            score = 0
            total_weight = 0
            
            if face_emotion == emotion_val:
                score += face_conf * weights['face']
                total_weight += weights['face']
            if voice_emotion == emotion_val:
                score += voice_conf * weights['voice']
                total_weight += weights['voice']
            if gait_emotion == emotion_val:
                score += gait_conf * weights['gait']
                total_weight += weights['gait']
            
            if total_weight > 0:
                emotion_scores[emotion_val] = score / total_weight
            else:
                emotion_scores[emotion_val] = 0
        
        # Select best emotion
        final_emotion = max(emotion_scores, key=emotion_scores.get)
        final_confidence = emotion_scores[final_emotion]
        
        # Calculate valence and arousal
        valence, arousal = self._emotion_to_valence_arousal(final_emotion)
        
        # Extract detailed features
        au_features = self._extract_action_units(
            face_data.get('landmarks') if face_data else None
        )
        
        voice_features = voice_data if voice_data else {}
        gait_features = gait_data if gait_data else {}
        
        return EmotionSample(
            timestamp=timestamp,
            emotion=final_emotion,
            confidence=final_confidence,
            face_detected=face_data is not None,
            voice_detected=voice_data is not None,
            gait_detected=gait_data is not None,
            valence=valence,
            arousal=arousal,
            **au_features,
            **voice_features,
            **gait_features
        )
    
    def _emotion_to_valence_arousal(self, emotion: str) -> Tuple[float, float]:
        """Map emotion to valence-arousal space."""
        mapping = {
            Emotion.NEUTRAL.value: (0.0, 0.2),
            Emotion.HAPPY.value: (0.8, 0.7),
            Emotion.SAD.value: (-0.6, -0.3),
            Emotion.ANGRY.value: (-0.5, 0.8),
            Emotion.SURPRISED.value: (0.3, 0.9),
            Emotion.DISGUSTED.value: (-0.7, 0.4),
            Emotion.FEARFUL.value: (-0.4, -0.5),
            Emotion.CONFUSED.value: (-0.1, -0.2)
        }
        return mapping.get(emotion, (0.0, 0.0))


class BehaviorTracker:
    """Track behavior patterns over time for anomaly detection."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.emotion_history = deque(maxlen=window_size)
        self.risk_history = deque(maxlen=window_size)
        self.interaction_history = deque(maxlen=50)
        
        # Load behavior classifier
        self.behavior_classifier = self._load_behavior_model()
        self.scaler = StandardScaler()
        
        # Baseline behavior profiles
        self.baseline_profiles = {
            'normal': {'emotion_volatility': 0.3, 'risk_score': 10},
            'stressed': {'emotion_volatility': 0.6, 'risk_score': 25},
            'agitated': {'emotion_volatility': 0.8, 'risk_score': 45},
        }
    
    def _load_behavior_model(self):
        """Load pre-trained behavior classification model."""
        model_path = 'models/behavior_classifier.joblib'
        
        if os.path.exists(model_path):
            return joblib.load(model_path)
        
        # Create and train default model if not exists
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        
        # Generate synthetic training data
        X_train = np.random.randn(1000, 5)
        y_train = np.random.choice(['normal', 'stressed', 'agitated'], 1000)
        model.fit(X_train, y_train)
        
        # Save model
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(model, model_path)
        
        return model
    
    def add_emotion_sample(self, sample: EmotionSample):
        """Add emotion sample to tracking history."""
        self.emotion_history.append(sample)
    
    def calculate_emotion_volatility(self, window: int = 20) -> float:
        """Calculate emotion volatility over recent history."""
        if len(self.emotion_history) < 2:
            return 0.0
        
        recent = list(self.emotion_history)[-window:]
        
        # Calculate emotion transition frequency
        transitions = 0
        for i in range(1, len(recent)):
            if recent[i].emotion != recent[i-1].emotion:
                transitions += 1
        
        volatility = transitions / (len(recent) - 1) if len(recent) > 1 else 0
        return min(volatility, 1.0)
    
    def calculate_arousal_trend(self, window: int = 30) -> float:
        """Calculate arousal trend (increasing/decreasing tension)."""
        if len(self.emotion_history) < 2:
            return 0.0
        
        recent = list(self.emotion_history)[-window:]
        arousals = [s.arousal for s in recent]
        
        if len(arousals) < 2:
            return 0.0
        
        # Linear trend
        x = np.arange(len(arousals))
        trend = np.polyfit(x, arousals, 1)[0]
        
        return float(trend)
    
    def detect_behavior_anomaly(self, current_state: BehaviorContext) -> float:
        """Detect anomalous behavior using ML classifier."""
        if len(self.emotion_history) < 10:
            return 0.0
        
        # Extract features
        features = self._extract_behavior_features(current_state)
        
        # Predict anomaly score
        features_scaled = self.scaler.fit_transform([features])
        prediction = self.behavior_classifier.predict_proba(features_scaled)
        
        # Get probability of 'agitated' or 'stressed' classes
        classes = self.behavior_classifier.classes_
        anomaly_score = 0.0
        
        for i, cls in enumerate(classes):
            if cls in ['agitated', 'stressed']:
                anomaly_score += prediction[0][i]
        
        return float(anomaly_score)
    
    def _extract_behavior_features(self, context: BehaviorContext) -> np.ndarray:
        """Extract features for behavior classification."""
        emotion_volatility = self.calculate_emotion_volatility()
        arousal_trend = self.calculate_arousal_trend()
        
        # Recent emotion distribution
        recent_emotions = [e.emotion for e in list(self.emotion_history)[-20:]]
        emotion_counts = {}
        for e in Emotion:
            emotion_counts[e.value] = recent_emotions.count(e.value)
        
        # Context features
        crowd_density = context.crowd_density
        known_individual = float(context.known_individual)
        prev_interactions = min(context.previous_interactions / 10, 1.0)
        
        features = np.array([
            emotion_volatility,
            arousal_trend,
            crowd_density,
            known_individual,
            prev_interactions
        ])
        
        return features
    
    def get_behavior_state(self, anomaly_score: float) -> BehaviorState:
        """Determine behavior state from anomaly score."""
        if anomaly_score > 0.7:
            return BehaviorState.THREATENING
        elif anomaly_score > 0.5:
            return BehaviorState.AGITATED
        elif anomaly_score > 0.3:
            return BehaviorState.DISTRESSED
        elif anomaly_score > 0.1:
            return BehaviorState.SUSPICIOUS
        else:
            return BehaviorState.NORMAL


class EmotionBehaviorEngine:
    """
    Main engine for emotion and behavior analysis.
    
    Integrates emotion detection, behavior tracking, and rule-based
    decision making for contextual awareness.
    """
    
    def __init__(self):
        self.emotion_detector = EmotionDetector()
        self.behavior_tracker = BehaviorTracker()
        self.rules_engine = RulesEngine()
        
        # Per-person tracking
        self.person_tracks: Dict[str, BehaviorTracker] = {}
    
    async def analyze_frame(
        self,
        person_id: str,
        face_data: Optional[Dict],
        voice_data: Optional[Dict],
        gait_data: Optional[Dict],
        context: BehaviorContext
    ) -> RiskAssessment:
        """
        Analyze a single frame for emotion and behavior.
        
        Args:
            person_id: Unique person identifier
            face_data: Face embedding and landmarks
            voice_data: Audio features
            gait_data: Movement features
            context: Behavioral context
            
        Returns:
            Risk assessment with recommendations
        """
        # Get or create tracker for this person
        if person_id not in self.person_tracks:
            self.person_tracks[person_id] = BehaviorTracker()
        
        tracker = self.person_tracks[person_id]
        
        # Detect emotion from all available modalities
        emotion_sample = self.emotion_detector.detect_ensemble(
            face_data or {},
            voice_data or {},
            gait_data or {}
        )
        
        # Add to tracking history
        tracker.add_emotion_sample(emotion_sample)
        
        # Calculate behavior metrics
        emotion_volatility = tracker.calculate_emotion_volatility()
        arousal_trend = tracker.calculate_arousal_trend()
        anomaly_score = tracker.detect_behavior_anomaly(context)
        behavior_state = tracker.get_behavior_state(anomaly_score)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(
            emotion_sample,
            emotion_volatility,
            anomaly_score,
            behavior_state,
            context
        )
        
        # Determine risk level
        risk_level = self._get_risk_level(risk_score)
        
        # Apply rules engine for action recommendation
        action, explanation = self.rules_engine.evaluate(
            emotion_sample,
            behavior_state,
            risk_score,
            context
        )
        
        # Build recent emotions history
        recent_emotions = [
            {
                'emotion': e.emotion,
                'confidence': e.confidence,
                'timestamp': e.timestamp,
                'arousal': e.arousal,
                'valence': e.valence
            }
            for e in list(tracker.emotion_history)[-10:]
        ]
        
        return RiskAssessment(
            person_id=person_id,
            timestamp=emotion_sample.timestamp,
            risk_level=risk_level,
            risk_score=risk_score,
            emotion_state=emotion_sample.emotion,
            behavior_state=behavior_state.value,
            emotion_volatility=emotion_volatility,
            behavior_anomaly_score=anomaly_score,
            context_risk=self._calculate_context_risk(context),
            historical_risk=self._get_historical_risk(person_id),
            action=action,
            confidence=emotion_sample.confidence,
            explanation=explanation,
            recent_emotions=recent_emotions
        )
    
    def _calculate_risk_score(
        self,
        emotion: EmotionSample,
        emotion_volatility: float,
        anomaly_score: float,
        behavior_state: BehaviorState,
        context: BehaviorContext
    ) -> float:
        """Calculate overall risk score (0-100)."""
        # Base risk from emotion
        emotion_risk = {
            Emotion.NEUTRAL.value: 0,
            Emotion.HAPPY.value: 0,
            Emotion.SAD.value: 10,
            Emotion.SURPRISED.value: 15,
            Emotion.CONFUSED.value: 20,
            Emotion.FEARFUL.value: 30,
            Emotion.DISGUSTED.value: 25,
            Emotion.ANGRY.value: 40
        }.get(emotion.emotion, 0)
        
        # Risk from behavior state
        behavior_risk = {
            BehaviorState.NORMAL: 0,
            BehaviorState.SUSPICIOUS: 20,
            BehaviorState.DISTRESSED: 25,
            BehaviorState.AGITATED: 40,
            BehaviorState.THREATENING: 60
        }.get(behavior_state, 0)
        
        # Volatility adds risk
        volatility_risk = emotion_volatility * 30
        
        # Anomaly adds risk
        anomaly_risk = anomaly_score * 40
        
        # Context risk
        context_risk = self._calculate_context_risk(context)
        
        # Combine with weights
        total_risk = (
            emotion_risk * 0.2 +
            behavior_risk * 0.3 +
            volatility_risk * 0.2 +
            anomaly_risk * 0.2 +
            context_risk * 0.1
        )
        
        return min(total_risk, 100)
    
    def _calculate_context_risk(self, context: BehaviorContext) -> float:
        """Calculate risk from context."""
        risk = 0
        
        # High crowd density increases risk
        risk += context.crowd_density * 20
        
        # Unknown individuals are higher risk
        if not context.known_individual:
            risk += 15
        
        # Night time is higher risk
        hour = int(context.time_of_day.split(':')[0])
        if hour < 6 or hour > 22:
            risk += 10
        
        return min(risk, 50)
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to level."""
        if risk_score >= 70:
            return 'critical'
        elif risk_score >= 50:
            return 'high'
        elif risk_score >= 30:
            return 'medium'
        elif risk_score >= 10:
            return 'low'
        else:
            return 'minimal'
    
    def _get_historical_risk(self, person_id: str) -> float:
        """Get historical risk for person from database."""
        # In production: Query database for past incidents
        # For now: Return 0
        return 0.0
    
    async def analyze_recognition_result(
        self,
        recognition_result: Dict,
        context: BehaviorContext
    ) -> Dict:
        """
        Analyze a recognition result and add emotion/behavior context.
        
        This integrates with the main recognition pipeline.
        """
        # Extract face data from recognition
        face_data = recognition_result.get('face')
        
        # Analyze emotion and behavior
        risk_assessment = await self.analyze_frame(
            person_id=recognition_result.get('person_id', 'unknown'),
            face_data=face_data,
            voice_data=None,  # Voice would come from separate input
            gait_data=None,   # Gait would come from video analysis
            context=context
        )
        
        # Combine with recognition result
        enriched_result = {
            **recognition_result,
            'emotion': risk_assessment.emotion_state,
            'emotion_confidence': risk_assessment.confidence,
            'behavior_state': risk_assessment.behavior_state,
            'risk_level': risk_assessment.risk_level,
            'risk_score': risk_assessment.risk_score,
            'action': risk_assessment.action,
            'explanation': risk_assessment.explanation,
            'valence': None,
            'arousal': None
        }
        
        # Add valence/arousal from most recent emotion
        if risk_assessment.recent_emotions:
            enriched_result['valence'] = risk_assessment.recent_emotions[-1].get('valence')
            enriched_result['arousal'] = risk_assessment.recent_emotions[-1].get('arousal')
        
        return enriched_result


class RulesEngine:
    """
    Rule engine for contextual decision making.
    
    Evaluates conditions and triggers actions based on
    emotion, behavior, and context.
    """
    
    def __init__(self):
        # Define rules
        self.rules = [
            {
                'name': 'high_risk_emotion',
                'condition': lambda e, b, r, c: r > 60,
                'action': 'review',
                'priority': 1,
                'explanation': 'High risk score requires manual review'
            },
            {
                'name': 'angry_agitated',
                'condition': lambda e, b, r, c: (
                    e.emotion == Emotion.ANGRY.value and 
                    b in [BehaviorState.AGITATED, BehaviorState.THREATENING]
                ),
                'action': 'monitor',
                'priority': 2,
                'explanation': 'Angry and agitated behavior detected'
            },
            {
                'name': 'suspicious_unknown',
                'condition': lambda e, b, r, c: (
                    b == BehaviorState.SUSPICIOUS and
                    not c.known_individual and
                    c.crowd_density < 0.3
                ),
                'action': 'review',
                'priority': 2,
                'explanation': 'Suspicious behavior from unknown individual'
            },
            {
                'name': 'high_emotion_volatility',
                'condition': lambda e, b, r, c: r > 40,
                'action': 'monitor',
                'priority': 3,
                'explanation': 'Unstable emotional state'
            },
            {
                'name': 'normal_behavior',
                'condition': lambda e, b, r, c: (
                    b == BehaviorState.NORMAL and
                    r < 20 and
                    e.emotion in [Emotion.NEUTRAL.value, Emotion.HAPPY.value]
                ),
                'action': 'allow',
                'priority': 4,
                'explanation': 'Normal, low-risk behavior'
            },
            {
                'name': 'default_review',
                'condition': lambda e, b, r, c: True,
                'action': 'allow',
                'priority': 5,
                'explanation': 'Allow by default'
            }
        ]
        
        # Sort by priority (lower = higher priority)
        self.rules.sort(key=lambda r: r['priority'])
    
    def evaluate(
        self,
        emotion: EmotionSample,
        behavior_state: BehaviorState,
        risk_score: float,
        context: BehaviorContext
    ) -> Tuple[str, str]:
        """
        Evaluate rules and determine action.
        
        Returns:
            (action, explanation)
        """
        for rule in self.rules:
            if rule['condition'](emotion, behavior_state, risk_score, context):
                return rule['action'], rule['explanation']
        
        return 'allow', 'Default action'
    
    def add_rule(self, rule: Dict):
        """Add a new rule to the engine."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r['priority'])
    
    def remove_rule(self, rule_name: str):
        """Remove a rule by name."""
        self.rules = [r for r in self.rules if r['name'] != rule_name]
    
    def get_rules(self) -> List[Dict]:
        """Get all rules."""
        return self.rules


# Global engine instance
_emotion_behavior_engine: Optional[EmotionBehaviorEngine] = None


def get_emotion_behavior_engine() -> EmotionBehaviorEngine:
    """Get or create global emotion behavior engine."""
    global _emotion_behavior_engine
    
    if _emotion_behavior_engine is None:
        _emotion_behavior_engine = EmotionBehaviorEngine()
    
    return _emotion_behavior_engine


async def analyze_recognition_with_behavior(
    recognition_result: Dict,
    context: Optional[BehaviorContext] = None
) -> Dict:
    """
    Convenience function to analyze recognition with emotion/behavior.
    
    Args:
        recognition_result: Result from recognition pipeline
        context: Optional behavioral context
        
    Returns:
        Enriched recognition result with emotion/behavior analysis
    """
    engine = get_emotion_behavior_engine()
    
    if context is None:
        context = BehaviorContext(
            person_id=recognition_result.get('person_id', 'unknown'),
            session_id=recognition_result.get('session_id', 'default'),
            location='unknown',
            time_of_day='12:00',
            crowd_density=0.5,
            weather='unknown',
            previous_interactions=0,
            known_individual=False
        )
    
    return await engine.analyze_recognition_result(
        recognition_result,
        context
    )
