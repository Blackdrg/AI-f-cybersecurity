import os
import cv2
import numpy as np
from backend.app.models.face_detector import FaceDetector
from backend.app.models.face_embedder import FaceEmbedder

class EdgeCaseTester:
    def __init__(self):
        self.detector = FaceDetector()
        self.embedder = FaceEmbedder()

    def test_low_light(self, image):
        """Simulate low light by reducing brightness."""
        low_light = (image.astype(float) * 0.2).astype(np.uint8)
        return self._run_detection(low_light, "Low Light (20% brightness)")

    def test_motion_blur(self, image):
        """Simulate motion blur using a kernel."""
        size = 15
        kernel = np.zeros((size, size))
        kernel[int((size-1)/2), :] = np.ones(size)
        kernel = kernel / size
        blurred = cv2.filter2D(image, -1, kernel)
        return self._run_detection(blurred, "Motion Blur")

    def test_crowd(self, images):
        """Test detection throughput on multiple faces."""
        print(f"Testing crowd scenario with {len(images)} faces...")
        # Concatenate images or just loop
        detected_count = 0
        for img in images:
            faces = self.detector.detect_faces(img)
            detected_count += len(faces)
        print(f"Detected {detected_count} faces across {len(images)} frames.")
        return detected_count

    def _run_detection(self, img, label):
        faces = self.detector.detect_faces(img)
        status = "✅ Success" if faces else "❌ Failed"
        print(f"[{label}] {status} - Faces detected: {len(faces)}")
        return len(faces) > 0

if __name__ == "__main__":
    # Test on a sample image
    tester = EdgeCaseTester()
    sample = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.putText(sample, "Face Placeholder", (100, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    tester.test_low_light(sample)
    tester.test_motion_blur(sample)
