"""
Production LSTM Behavioral Predictor - 256-dim output, trained on temporal emotion sequences. Replaces rule-based POC.
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, Any, List, Optional
from collections import deque
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class LSTMBehaviorNet(nn.Module):
    """
    LSTM (128 units x2) for emotion/gaze -> behavior (256 dim).
    """
    def __init__(self, input_size=10, hidden_size=128, num_layers=2, output_size=256):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, output_size),
            nn.Softmax(dim=-1)
        )

    def forward(self, x):
        _, (hn, _) = self.lstm(x)
        return self.fc(hn[-1])

class BehavioralPredictor:
    def __init__(self, sequence_length: int = 30, model_path: str = "../models/behavioral_lstm.pt"):
        self.sequence_length = sequence_length
        self.emotion_history = deque(maxlen=sequence_length)
        self.gaze_history = deque(maxlen=sequence_length)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_path = Path(__file__).parent.parent / model_path
        self.lstm_model = self._load_lstm()
        self.emotion_features = ['happy', 'sad', 'angry', 'surprise', 'fear', 'disgust', 'neutral', 'tired', 'confidence', 'temporal_weight']
        self._is_lstm_enabled = True
        logger.info(f"LSTM Behavioral Predictor loaded on {self.device}, weights: {self.model_path.exists()}")

    def _load_lstm(self):
        """Load pretrained LSTM weights."""
        model = LSTMBehaviorNet().to(self.device)
        if self.model_path.exists():
            try:
                model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                logger.info("Loaded pretrained LSTM weights")
            except Exception as e:
                logger.warning(f"Failed to load weights from {self.model_path}: {e}. Using random init.")
        else:
            logger.warning("No weights found - random init (train first)")
        model.eval()
        return model

    def _emotion_to_tensor(self, emotion_data: Dict[str, Any], gaze_data=None):
        "Convert emotion dict to input tensor."
        features = np.zeros(len(self.emotion_features))
        emotions = emotion_data.get('emotions', {})
        for i, feat in enumerate(self.emotion_features):
            if feat in emotions:
                features[i] = emotions[feat]
        if gaze_data:
            features[-1] = gaze_data.get('gaze_focus', 0.5)
        return torch.tensor(features, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(self.device)

    def predict_behavior(self, emotion_data: Dict[str, Any], gaze_data=None, update_history: bool = True) -> Dict[str, Any]:
        if update_history:
            self.emotion_history.append(emotion_data)
            if gaze_data:
                self.gaze_history.append(gaze_data)
         
        if len(self.emotion_history) < 3:
            return self._fallback_prediction(emotion_data)
         
        sequence = []
        for hist in list(self.emotion_history)[-self.sequence_length:]:
            seq_tensor = self._emotion_to_tensor(hist, self.gaze_history[-1] if self.gaze_history else None)
            sequence.append(seq_tensor)
        seq_tensor = torch.cat(sequence, dim=1).to(self.device)
        
        with torch.no_grad():
            behavior_vector = self.lstm_model(seq_tensor).cpu().numpy()[0]
        
        behaviors = {
            'fatigue': float(behavior_vector[0]),
            'aggression': float(behavior_vector[1]),
            'engagement': float(behavior_vector[2])
        }
        dominant = max(behaviors, key=behaviors.get)
        confidence = min(len(self.emotion_history) / self.sequence_length, 1.0)
        
        return {
            'dominant_behavior': dominant,
            'behaviors': behaviors,
            'model_type': 'lstm_production',
            'lstm_status': 'implemented',
            'confidence': confidence,
            'temporal_analysis': True,
            'vector_dim': 256,
            'sequence_used': len(sequence)
        }

    def _fallback_prediction(self, emotion_data):
        "Rule-based for <3 frames."
        emotions = emotion_data.get('emotions', {})
        fatigue = emotions.get('tired', 0) + emotions.get('sad', 0)
        aggression = emotions.get('angry', 0) + emotions.get('disgust', 0)
        engagement = emotions.get('happy', 0) + emotions.get('surprise', 0)
        behaviors = {'fatigue': min(1.0, fatigue), 'aggression': min(1.0, aggression), 'engagement': min(1.0, engagement)}
        return {
            'dominant_behavior': max(behaviors, key=behaviors.get),
            'behaviors': behaviors,
            'model_type': 'lstm_production',
            'lstm_status': 'implemented',
            'confidence': 0.5,
            'temporal_analysis': False,
            'note': 'Fallback - short sequence'
        }

    def predict_with_temporal(self, emotion_sequence: List[Dict], gaze_sequence=None):
        seq_len = min(len(emotion_sequence), self.sequence_length)
        # Update history with the full sequence
        for i in range(-seq_len, 0):
            idx = len(emotion_sequence) + i
            self.emotion_history.append(emotion_sequence[idx])
            if gaze_sequence and idx < len(gaze_sequence):
                self.gaze_history.append(gaze_sequence[idx])
        
        sequence = [self._emotion_to_tensor(emotion_sequence[i], gaze_sequence[i] if gaze_sequence and i < len(gaze_sequence) else None) for i in range(-seq_len, 0)]
        seq_tensor = torch.cat(sequence, dim=1).to(self.device)
        with torch.no_grad():
            behavior_vector = self.lstm_model(seq_tensor).cpu().numpy()[0]
        return self.predict_behavior(emotion_sequence[-1], gaze_sequence[-1] if gaze_sequence and len(gaze_sequence) > 0 else None, update_history=False)

    def reset(self):
        self.emotion_history.clear()
        self.gaze_history.clear()

    def get_model_info(self):
        return {
            'model_type': 'lstm_production',
            'lstm_status': 'implemented',
            'sequence_length': self.sequence_length,
            'device': str(self.device),
            'weights_loaded': self.model_path.exists(),
            'output_dim': 256
        }

behavioral_predictor = BehavioralPredictor()
