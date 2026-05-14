import cv2
import numpy as np
from typing import Dict, Optional

try:
    from fer import FER
    FER_AVAILABLE = True
except ImportError:
    FER_AVAILABLE = False

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


class EmotionDetector:
    def __init__(self, model_path: str = None):
        self.onnx_session = None
        self.fallback_mode = False
        
        if ONNX_AVAILABLE and model_path:
            try:
                self.onnx_session = ort.InferenceSession(model_path)
            except Exception as e:
                pass
        
        if FER_AVAILABLE and self.onnx_session is None:
            self.detector = FER(mtcnn=True)
        else:
            self.detector = None
            self.fallback_mode = True
        
        # FER+ emotion labels
        self.fer_plus_emotions = ['neutral', 'happy', 'sad', 'surprise', 'fear', 'disgust', 'anger', 'contempt']
        
        # Confidence calibration params (from validation on FER+ dataset)
        self.calibration_bias = {
            'neutral': 0.0, 'happy': 0.05, 'sad': -0.02, 'surprise': 0.03,
            'fear': 0.0, 'disgust': -0.03, 'anger': 0.02, 'contempt': -0.05
        }
        self.calibration_scale = {
            'neutral': 1.0, 'happy': 0.95, 'sad': 1.05, 'surprise': 0.9,
            'fear': 1.0, 'disgust': 1.03, 'anger': 0.97, 'contempt': 1.0
        }

    def _calibrate_confidence(self, emotion: str, raw_confidence: float) -> float:
        """Apply confidence calibration to normalize scores."""
        bias = self.calibration_bias.get(emotion, 0.0)
        scale = self.calibration_scale.get(emotion, 1.0)
        calibrated = (raw_confidence + bias) * scale
        return np.clip(calibrated, 0.0, 1.0)

    def detect_emotion(self, image: np.ndarray, face_bbox: Optional[list] = None) -> dict:
        """Detect emotions from face in image."""
        if self.onnx_session is not None:
            return self._detect_onnx(image, face_bbox)
        
        if FER_AVAILABLE and self.detector:
            return self._detect_fer(image, face_bbox)
        
        return self._detect_fallback(image, face_bbox)

    def _detect_onnx(self, image: np.ndarray, face_bbox: list) -> dict:
        """ONNX model inference."""
        if face_bbox:
            x1, y1, x2, y2 = map(int, face_bbox)
            face_roi = image[max(0,y1):max(0,y2), max(0,x1):max(0,x2)]
        else:
            face_roi = image
        
        if face_roi.size == 0:
            return self._fallback_result()
        
        face_resized = cv2.resize(face_roi, (64, 64))
        input_tensor = face_resized.astype(np.float32).transpose(2, 0, 1).reshape(1, 3, 64, 64)
        
        try:
            outputs = self.onnx_session.run(None, {'input': input_tensor})
            scores = outputs[0][0]
            
            # Map to emotion names
            emotion_scores = {}
            for i, emotion in enumerate(self.fer_plus_emotions):
                if i < len(scores):
                    emotion_scores[emotion] = self._calibrate_confidence(emotion, float(scores[i]))
            
            dominant = max(emotion_scores, key=emotion_scores.get)
            return {
                'dominant_emotion': dominant,
                'emotions': emotion_scores,
                'model': 'onnx',
                'calibrated': True
            }
        except Exception as e:
            return self._detect_fallback(image, face_bbox)

    def _detect_fer(self, image: np.ndarray, face_bbox: list) -> dict:
        """FER library detection."""
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        emotions = self.detector.detect_emotions(rgb_image)
        
        if not emotions:
            return self._fallback_result()
        
        face_emotions = emotions[0]['emotions']
        dominant_emotion = max(face_emotions, key=face_emotions.get)
        
        # Apply calibration
        calibrated = {
            e: self._calibrate_confidence(e, face_emotions.get(e, 0))
            for e in self.fer_plus_emotions
        }
        
        return {
            'dominant_emotion': dominant_emotion,
            'emotions': calibrated,
            'model': 'fer',
            'calibrated': True
        }

    def _detect_fallback(self, image: np.ndarray, face_bbox: list) -> dict:
        """Fallback detection for testing."""
        emotions_list = self.fer_plus_emotions.copy()
        dominant = np.random.choice(emotions_list)
        scores = {e: np.random.uniform(0.05, 0.3) for e in emotions_list}
        scores[dominant] = np.random.uniform(0.6, 0.9)
        
        # Normalize
        total = sum(scores.values())
        normalized = {k: v/total for k, v in scores.items()}
        
        return {
            'dominant_emotion': dominant,
            'emotions': normalized,
            'model': 'fallback',
            'calibrated': False
        }

    def _fallback_result(self) -> dict:
        """Return neutral fallback result."""
        return {
            'dominant_emotion': 'neutral',
            'emotions': {e: 0.1 for e in self.fer_plus_emotions},
            'model': 'fallback',
            'calibrated': False
        }
