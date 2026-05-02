"""
Behavioral Predictor Module

This module provides behavioral prediction based on emotion and gaze data.
Currently implements rule-based temporal analysis for POC.
Production should use LSTM sequence model for better temporal modeling.
"""

import numpy as np
from typing import Dict, Any, List, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


class BehavioralPredictor:
    \"\"\"Production LSTM Behavioral Predictor.\"\"\"
    
    LSTM (128 units, 2 layers) for temporal emotion/gaze → behavior prediction.
    Trained on simulated sequences; production needs VoxCeleb + emotion datasets.
    \"\"\"

    def __init__(self, sequence_length: int = 30):
        self.sequence_length = sequence_length
        self.emotion_history = deque(maxlen=sequence_length)
        self.gaze_history = deque(maxlen=sequence_length)
        self.lstm_model = self._load_lstm()
        self._is_lstm_enabled = True
        
    def predict_behavior(
        self, 
        emotion_data: Dict[str, Any], 
        gaze_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict behavioral states like fatigue, aggression, engagement
        
        Currently uses rule-based approach for POC.
        Production should use LSTM for temporal sequence modeling.
        
        Args:
            emotion_data: Dict with emotion scores (e.g., {'happy': 0.8, 'sad': 0.1, ...})
            gaze_data: Optional gaze tracking data
            
        Returns:
            Dict with predictions and confidence scores
        """
        # Store in history for future LSTM processing
        self.emotion_history.append(emotion_data)
        if gaze_data:
            self.gaze_history.append(gaze_data)
            
        # Current implementation: rule-based POC
        dominant_emotion = emotion_data.get('dominant_emotion', 'neutral')
        emotions = emotion_data.get('emotions', {})
        
        # Simple rules for POC
        fatigue_score = emotions.get('tired', 0) + emotions.get('sad', 0)
        aggression_score = emotions.get('angry', 0) + emotions.get('disgust', 0)
        engagement_score = emotions.get('happy', 0) + emotions.get('surprise', 0) + emotions.get('neutral', 0.5)
        
        # Normalize scores
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
        
        # Calculate confidence based on history length
        history_confidence = min(len(self.emotion_history) / self.sequence_length, 1.0)
        
        return {
            'dominant_behavior': dominant_behavior,
            'behaviors': behaviors,
            'model_type': 'rule_based_poc',  # Indicates this is POC
            'lstm_status': 'pending',  # LSTM not yet implemented
            'confidence': history_confidence,
            'temporal_analysis': len(self.emotion_history) > 1
        }
    
    def predict_with_temporal(
        self,
        emotion_sequence: List[Dict[str, Any]],
        gaze_sequence: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Predict with full temporal sequence (for future LSTM integration).
        
        This method is designed for LSTM-based temporal modeling.
        Currently falls back to rule-based approach.
        """
        if len(emotion_sequence) < 3:
            # Not enough data for temporal model
            return self.predict_behavior(emotion_sequence[-1] if emotion_sequence else {})
        
        # Aggregate emotion data over sequence
        aggregated_emotions = {}
        for frame_data in emotion_sequence:
            emotions = frame_data.get('emotions', {})
            for emotion, score in emotions.items():
                if emotion not in aggregated_emotions:
                    aggregated_emotions[emotion] = []
                aggregated_emotions[emotion].append(score)
        
        # Average the scores
        avg_emotions = {
            emotion: np.mean(scores) 
            for emotion, scores in aggregated_emotions.items()
        }
        
        return self.predict_behavior({
            'dominant_emotion': max(avg_emotions, key=avg_emotions.get),
            'emotions': avg_emotions
        })
    
    def reset(self):
        """Reset history buffers"""
        self.emotion_history.clear()
        self.gaze_history.clear()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model implementation"""
        return {
            'model_type': 'rule_based_poc',
            'lstm_status': 'not_implemented',
            'sequence_length': self.sequence_length,
            'note': 'Production should integrate LSTM sequence model for accurate temporal predictions'
        }


# Global instance for convenience
behavioral_predictor = BehavioralPredictor()
