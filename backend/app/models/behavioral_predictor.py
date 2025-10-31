from typing import Dict, Any


class BehavioralPredictor:
    def __init__(self):
        # Rule-based predictor for POC
        pass

    def predict_behavior(self, emotion_data: Dict[str, Any], gaze_data: Dict[str, Any] = None) -> dict:
        """
        Predict behavioral states like fatigue, aggression, engagement based on emotion and gaze.
        Returns dict with predictions and confidence.
        """
        dominant_emotion = emotion_data.get('dominant_emotion', 'neutral')
        emotions = emotion_data.get('emotions', {})

        # Simple rules
        fatigue_score = emotions.get('tired', 0) + emotions.get('sad', 0)
        aggression_score = emotions.get(
            'angry', 0) + emotions.get('disgust', 0)
        engagement_score = emotions.get(
            'happy', 0) + emotions.get('surprise', 0) + emotions.get('neutral', 0.5)

        # Normalize
        fatigue_score = min(1.0, fatigue_score)
        aggression_score = min(1.0, aggression_score)
        engagement_score = min(1.0, engagement_score)

        # Determine dominant behavior
        behaviors = {
            'fatigue': fatigue_score,
            'aggression': aggression_score,
            'engagement': engagement_score
        }
        dominant_behavior = max(behaviors, key=behaviors.get)

        return {
            'dominant_behavior': dominant_behavior,
            'behaviors': behaviors
        }
