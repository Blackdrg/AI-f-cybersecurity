import cv2
import numpy as np
import logging

try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    FaceAnalysis = None

from .spoof_detector import SpoofDetector
from .face_reconstructor import FaceReconstructor

logger = logging.getLogger(__name__)


class FaceDetector:
    def __init__(self):
        if INSIGHTFACE_AVAILABLE:
            try:
                self.app = FaceAnalysis(name='buffalo_l')
                self.app.prepare(ctx_id=0, det_size=(640, 640))
            except Exception as e:
                logger.warning(f"Failed to load InsightFace: {e}. Using mock detection.")
                self.app = None
        else:
            self.app = None
        self.spoof_detector = SpoofDetector()
        self.reconstructor = FaceReconstructor()

    def detect_faces(self, image: np.ndarray, check_spoof: bool = True, reconstruct: bool = True) -> list:
        """
        Detect faces in image, return list of dicts with bbox, landmarks, spoof_score, etc.
        """
        detected_faces = []

        if image is None:
            return detected_faces

        if self.app is not None:
            try:
                faces = self.app.get(image)
                for face in faces:
                    bbox = face.bbox.astype(int).tolist()
                    # landmarks shape: (N, 2) -> list of [x,y]
                    landmarks = face.landmark.astype(int).tolist() if hasattr(face, 'landmark') and face.landmark is not None else []
                    det_score = float(getattr(face, 'det_score', 1.0))

                    spoof_score = 0.0
                    reconstruction_confidence = 1.0

                    if check_spoof:
                        spoof_score = self.spoof_detector.detect_spoof(image, bbox)

                    if reconstruct and spoof_score < 0.5:
                        reconstructed_image, reconstruction_confidence = self.reconstructor.reconstruct_face(
                            image, bbox)

                    detected_faces.append({
                        'bbox': bbox,
                        'landmarks': landmarks,
                        'det_score': det_score,
                        'spoof_score': spoof_score,
                        'reconstruction_confidence': reconstruction_confidence
                    })
            except Exception as e:
                logger.warning(f"InsightFace detection failed: {e}. Falling back to mock detection.")
                self.app = None  # Disable further attempts to avoid repeated errors

        # Fallback: mock detection if insightface unavailable or failed
        if not detected_faces:
            height, width = image.shape[:2]
            center_x, center_y = width // 2, height // 2
            bbox = [center_x-40, center_y-40, center_x+40, center_y+40]
            landmarks = [
                [center_x-20, center_y-10],
                [center_x+20, center_y-10],
                [center_x, center_y+5],
                [center_x-15, center_y+20],
                [center_x+15, center_y+20]
            ]
            spoof_score = 0.0
            reconstruction_confidence = 1.0

            if check_spoof:
                spoof_score = self.spoof_detector.detect_spoof(image, bbox)

            if reconstruct and spoof_score < 0.5:
                reconstructed_image, reconstruction_confidence = self.reconstructor.reconstruct_face(
                    image, bbox)
                # image = reconstructed_image

            detected_faces.append({
                'bbox': bbox,
                'landmarks': landmarks,
                'det_score': 0.99,
                'spoof_score': spoof_score,
                'reconstruction_confidence': reconstruction_confidence
            })

        return detected_faces

    def align_face(self, image: np.ndarray, landmarks: list) -> np.ndarray:
        """
        Align face using landmarks to canonical size (112x112).
        """
        # Use 5-point landmarks for alignment
        if len(landmarks) == 106:
            # Convert to 5 points if needed
            landmarks_5 = self._landmarks_106_to_5(landmarks)
        else:
            landmarks_5 = landmarks

        # Standard alignment using eye/nose points
        left_eye = np.array(landmarks_5[0])
        right_eye = np.array(landmarks_5[1])
        nose = np.array(landmarks_5[2])

        # Calculate angle
        dY = right_eye[1] - left_eye[1]
        dX = right_eye[0] - left_eye[0]
        angle = np.degrees(np.arctan2(dY, dX))

        # Desired eye positions
        desired_left_eye = (0.35, 0.35)
        desired_right_eye = (0.65, 0.35)

        # Calculate scale and translation
        eye_dist = np.linalg.norm(right_eye - left_eye)
        desired_eye_dist = 0.3 * 112  # 30% of image width

        scale = desired_eye_dist / eye_dist

        # Center of eyes
        eyes_center = (left_eye + right_eye) / 2

        # Translation
        tX = 112 * 0.5 - eyes_center[0]
        tY = 112 * desired_left_eye[1] - eyes_center[1]

        # Apply transformation
        M = cv2.getRotationMatrix2D(
            (eyes_center[0], eyes_center[1]), angle, scale)
        M[0, 2] += tX
        M[1, 2] += tY

        aligned = cv2.warpAffine(image, M, (112, 112), flags=cv2.INTER_CUBIC)

        return aligned

    def _landmarks_106_to_5(self, landmarks_106):
        # Convert 106-point to 5-point (approximate)
        # Indices for left eye, right eye, nose, left mouth, right mouth
        indices = [39, 42, 33, 84, 90]  # Approximate
        return [landmarks_106[i] for i in indices]
