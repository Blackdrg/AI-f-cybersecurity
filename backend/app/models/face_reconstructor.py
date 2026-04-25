import cv2
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class FaceReconstructor:
    """
    Face reconstruction / inpainting for occlusion handling.
    
    Current implementation: Navier-Stokes inpainting via OpenCV.
    Limitations:
      - Does not detect occlusions automatically; requires an explicit mask.
      - The naive mask generation (thresholding dark pixels) is a placeholder.
      - For production, integrate a dedicated occlusion detector (e.g., face parsing)
        and a state-of-the-art inpainting model (e.g., Stable Diffusion Inpainting,
        LaMa, or real GFPGAN).
    """
    def __init__(self):
        # Note: GFPGAN is not available via insightface.model_zoo.
        # To use real GFPGAN, install `gfpgan` package and load separately.
        self.gfpgan = None
        try:
            import gfpgan
            # GFPGAN would be loaded here if package installed
            # self.gfpgan = gfpgan.GFPGANer(...)
            logger.info("GFPGAN not integrated; using Navier-Stokes fallback")
        except ImportError:
            logger.info("GFPGAN package not installed; using Navier-Stokes inpainting")

    def reconstruct_face(
        self, 
        image: np.ndarray, 
        face_bbox: list, 
        mask: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, float]:
        """
        Reconstruct occluded parts of the face using GAN-based inpainting if available.
        Returns (reconstructed_image, confidence_score).
        
        Args:
            image: Full input image (BGR)
            face_bbox: [x1, y1, x2, y2]
            mask: Optional binary mask (same size as face_roi) where non-zero pixels indicate
                  regions to inpaint. If None and GFPGAN unavailable, returns original image.
        """
        x1, y1, x2, y2 = face_bbox
        h, w = image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return image, 0.0

        face_roi = image[y1:y2, x1:x2]
        if face_roi.size == 0:
            return image, 1.0  # no reconstruction needed

        confidence = 1.0  # default: original image intact

        # Try GFPGAN if available
        if self.gfpgan is not None:
            try:
                restored = self.gfpgan.get(face_roi)
                if restored is not None:
                    restored = np.array(restored)
                    if restored.shape[:2] != (y2-y1, x2-x1):
                        restored = cv2.resize(restored, (x2-x1, y2-y1))
                    reconstructed = image.copy()
                    reconstructed[y1:y2, x1:x2] = restored
                    confidence = 0.9
                    return reconstructed, confidence
            except Exception as e:
                logger.warning(f"GFPGAN failed: {e}, falling back to Navier-Stokes if mask provided")

        # Navier-Stokes fallback: only if explicit mask provided
        if mask is not None:
            try:
                # Ensure mask is binary uint8
                if mask.dtype != np.uint8:
                    mask = (mask > 0).astype(np.uint8) * 255
                if mask.shape != face_roi.shape[:2]:
                    mask = cv2.resize(mask, (face_roi.shape[1], face_roi.shape[0]))
                inpainted = cv2.inpaint(face_roi, mask, 3, cv2.INPAINT_NS)
                reconstructed = image.copy()
                reconstructed[y1:y2, x1:x2] = inpainted
                occlusion_ratio = np.sum(mask > 0) / (mask.shape[0] * mask.shape[1] + 1e-6)
                confidence = max(0.1, 1.0 - occlusion_ratio)
                return reconstructed, confidence
            except Exception as e:
                logger.warning(f"Navier-Stokes inpainting failed: {e}")

        # No reconstruction performed
        return image, confidence
