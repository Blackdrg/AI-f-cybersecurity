import cv2
import numpy as np
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

class FaceReconstructor:
    def __init__(self):
        # For POC, try to use GFPGAN for GAN-based inpainting if available.
        # Falls back to Navier-Stokes inpainting.
        self.gfpgan = None
        try:
            from insightface.model_zoo import get_model
            self.gfpgan = get_model('gfpgan')
            self.gfpgan.prepare(ctx_id=0)
            logger.info("GFPGAN face restoration model loaded.")
        except Exception as e:
            logger.warning(f"GFPGAN not available, using Navier-Stokes inpainting: {e}")
            self.gfpgan = None

    def reconstruct_face(self, image: np.ndarray, face_bbox: list) -> Tuple[np.ndarray, float]:
        """
        Reconstruct occluded parts of the face using GAN-based inpainting if available.
        Returns reconstructed image and confidence score.
        """
        x1, y1, x2, y2 = face_bbox
        # Clip to image bounds
        h, w = image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return image, 0.0

        face_roi = image[y1:y2, x1:x2]

        if face_roi.size == 0:
            return image, 0.0

        confidence = 0.5  # default moderate confidence

        if self.gfpgan is not None:
            try:
                # GFPGAN expects BGR image; output is restored face of same size
                restored = self.gfpgan.get(face_roi)
                if restored is not None:
                    restored = np.array(restored)
                    # Ensure size matches ROI
                    if restored.shape[:2] != (y2-y1, x2-x1):
                        restored = cv2.resize(restored, (x2-x1, y2-y1))
                    reconstructed = image.copy()
                    reconstructed[y1:y2, x1:x2] = restored
                    confidence = 0.9  # high confidence for GAN-based restoration
                    return reconstructed, confidence
            except Exception as e:
                logger.warning(f"GFPGAN reconstruction failed: {e}, falling back to Navier-Stokes")

        # Fallback: Navier-Stokes inpainting for minor occlusions
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY_INV)
        reconstructed_roi = cv2.inpaint(face_roi, mask, 3, cv2.INPAINT_NS)
        reconstructed = image.copy()
        reconstructed[y1:y2, x1:x2] = reconstructed_roi
        occlusion_ratio = np.sum(mask > 0) / mask.size
        confidence = max(0.1, 1.0 - occlusion_ratio)  # lower confidence for navier-stokes

        return reconstructed, confidence
