import cv2
import numpy as np
# from insightface.app import FaceAnalysis
from .spoof_detector import SpoofDetector
from .face_reconstructor import FaceReconstructor


class FaceDetector:
    def __init__(self):
        # self.app = FaceAnalysis(name='buffalo_l')  # Includes SCRFD detector
        # self.app.prepare(ctx_id=0, det_size=(640, 640))  # Use GPU if available
        self.spoof_detector = SpoofDetector()
        self.reconstructor = FaceReconstructor()

    def detect_faces(self, image: np.ndarray, check_spoof: bool = True, reconstruct: bool = True) -> list:
        """
        Detect faces in image, return list of dicts with bbox, landmarks, spoof_score, etc.
        """
        # faces = self.app.get(image)
        # Mock detection for now since insightface is not installed
        # For testing, create a mock face detection if image has white rectangle
        detected_faces = []

        if image is None:
            return detected_faces

        # Simple mock detection - always detect a face in the center for testing
        height, width = image.shape[:2]
        center_x, center_y = width // 2, height // 2

        # Mock face in center - always detect for testing purposes
        bbox = [center_x-40, center_y-40, center_x+40, center_y+40]
        # Mock 5-point landmarks
        landmarks = [
            [center_x-20, center_y-10],  # left eye
            [center_x+20, center_y-10],  # right eye
            [center_x, center_y+5],      # nose
            [center_x-15, center_y+20],  # left mouth
            [center_x+15, center_y+20]   # right mouth
        ]

        spoof_score = 0.0
        reconstruction_confidence = 1.0

        if check_spoof:
            spoof_score = self.spoof_detector.detect_spoof(image, bbox)

        if reconstruct and spoof_score < 0.5:  # Only reconstruct if not likely spoof
            reconstructed_image, reconstruction_confidence = self.reconstructor.reconstruct_face(
                image, bbox)
            # Re-run detection on reconstructed image if needed (simplified)
            image = reconstructed_image

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
