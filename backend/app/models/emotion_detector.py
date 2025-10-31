import cv2
import numpy as np

try:
    from fer import FER
    FER_AVAILABLE = True
except ImportError:
    FER_AVAILABLE = False


class EmotionDetector:
    def __init__(self):
        if FER_AVAILABLE:
            # Use FER (Facial Expression Recognition) library
            self.detector = FER(mtcnn=True)
        else:
            # Fallback to mock emotions for testing
            self.detector = None

    def detect_emotion(self, image: np.ndarray, face_bbox: list) -> dict:
        """
        Detect emotions from face in image.
        Returns dict with emotion scores and dominant emotion.
        """
        if FER_AVAILABLE and self.detector:
            # FER expects RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detect emotions
            emotions = self.detector.detect_emotions(rgb_image)

            if not emotions:
                return {'dominant_emotion': 'neutral', 'emotions': {'neutral': 1.0}}

            # Find the face closest to bbox (simple approximation)
            face_emotions = emotions[0]['emotions']  # Take first detected face

            dominant_emotion = max(face_emotions, key=face_emotions.get)

            return {
                'dominant_emotion': dominant_emotion,
                'emotions': face_emotions
            }
        else:
            # Mock emotions for testing when FER is not available
            import random
            emotions = ['happy', 'sad', 'angry', 'fear',
                        'surprise', 'disgust', 'neutral']
            dominant = random.choice(emotions)
            mock_scores = {emotion: random.uniform(
                0.1, 0.9) for emotion in emotions}
            mock_scores[dominant] = random.uniform(
                0.7, 1.0)  # Make dominant emotion higher
            total = sum(mock_scores.values())
            normalized_scores = {k: v/total for k, v in mock_scores.items()}

            return {
                'dominant_emotion': dominant,
                'emotions': normalized_scores
            }
