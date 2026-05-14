"""
Biometric processing pipeline manager.
"""
from typing import Any, Optional
import numpy as np
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BiometricStage(Enum):
    """Biometric pipeline stages."""
    FACE_DETECTION = "face_detection"
    FACE_ALIGNMENT = "face_alignment"
    FACE_EMBEDDING = "face_embedding"
    ANTI_SPOOF = "anti_spoof"
    VERIFICATION = "verification"


@dataclass
class BiometricResult:
    """Result from biometric pipeline."""
    success: bool
    stage: BiometricStage
    embedding: Optional[np.ndarray] = None
    is_real: bool = True
    confidence: float = 0.0
    faces_detected: int = 0
    error: Optional[str] = None


class BiometricPipeline:
    """Pipeline manager for biometric processing."""
    
    def __init__(self, face_detector=None, face_embedder=None, spoof_detector=None):
        self.face_detector = face_detector
        self.face_embedder = face_embedder
        self.spoof_detector = spoof_detector
        self._current_stage = BiometricStage.FACE_DETECTION
    
    async def process(self, image: np.ndarray) -> BiometricResult:
        """Run full biometric pipeline."""
        try:
            faces = await self._detect_faces(image)
            if not faces:
                return BiometricResult(
                    success=False,
                    stage=BiometricStage.FACE_DETECTION,
                    error="No faces detected"
                )
            
            aligned_face = await self._align_face(image, faces[0])
            
            if self.spoof_detector:
                spoof_result = await self._check_spoof(aligned_face)
                if not spoof_result["is_real"]:
                    return BiometricResult(
                        success=True,
                        stage=BiometricStage.ANTI_SPOOF,
                        is_real=False,
                        confidence=spoof_result["confidence"]
                    )
            
            embedding = await self._get_embedding(aligned_face)
            
            return BiometricResult(
                success=True,
                stage=BiometricStage.VERIFICATION,
                embedding=embedding,
                is_real=True,
                confidence=1.0,
                faces_detected=len(faces)
            )
        except Exception as e:
            logger.error(f"Biometric pipeline error: {e}")
            return BiometricResult(
                success=False,
                stage=self._current_stage,
                error=str(e)
            )
    
    async def _detect_faces(self, image: np.ndarray) -> list:
        self._current_stage = BiometricStage.FACE_DETECTION
        if self.face_detector:
            return await self.face_detector.detect(image)
        return []
    
    async def _align_face(self, image: np.ndarray, face: dict) -> np.ndarray:
        self._current_stage = BiometricStage.FACE_ALIGNMENT
        bbox = face.get("bbox", [])
        if len(bbox) >= 4:
            return image[bbox[1]:bbox[3], bbox[0]:bbox[2]]
        return image
    
    async def _check_spoof(self, face_image: np.ndarray) -> dict:
        self._current_stage = BiometricStage.ANTI_SPOOF
        if self.spoof_detector:
            return await self.spoof_detector.predict(face_image)
        return {"is_real": True, "confidence": 1.0}
    
    async def _get_embedding(self, face_image: np.ndarray) -> np.ndarray:
        self._current_stage = BiometricStage.FACE_EMBEDDING
        if self.face_embedder:
            return await self.face_embedder.get_embedding(face_image)
        return np.zeros(512, dtype=np.float32)