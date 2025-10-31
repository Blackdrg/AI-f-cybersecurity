import cv2
import numpy as np

try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False


class AgeGenderEstimator:
    def __init__(self):
        if INSIGHTFACE_AVAILABLE:
            # Use InsightFace's built-in attribute estimation
            self.app = FaceAnalysis(name='buffalo_l')
            self.app.prepare(ctx_id=0, det_size=(640, 640))
        else:
            # Fallback to mock estimation
            self.app = None

    def estimate_age_gender(self, image: np.ndarray, face_bbox: list) -> dict:
        """
        Estimate age and gender from face.
        Returns dict with age, gender, and confidence.
        """
        if INSIGHTFACE_AVAILABLE and self.app:
            faces = self.app.get(image)

            if not faces:
                return {'age': None, 'gender': None, 'gender_confidence': 0.0}

            # Take the first face (assuming single face for simplicity)
            face = faces[0]

            age = int(face.age) if hasattr(face, 'age') else None
            gender = 'M' if face.gender == 1 else 'F' if face.gender == 0 else None
            gender_confidence = float(face.det_score)  # Approximation

            return {
                'age': age,
                'gender': gender,
                'gender_confidence': gender_confidence
            }
        else:
            # Fallback: mock estimation based on face size and position
            x1, y1, x2, y2 = face_bbox
            face_area = (x2 - x1) * (y2 - y1)

            # Mock age based on face area (larger faces assumed younger)
            if face_area > 50000:
                age = np.random.randint(18, 30)
            elif face_area > 30000:
                age = np.random.randint(30, 50)
            else:
                age = np.random.randint(50, 80)

            # Mock gender based on random
            gender = 'M' if np.random.random() > 0.5 else 'F'
            gender_confidence = np.random.uniform(0.5, 0.9)

            return {
                'age': age,
                'gender': gender,
                'gender_confidence': gender_confidence
            }
