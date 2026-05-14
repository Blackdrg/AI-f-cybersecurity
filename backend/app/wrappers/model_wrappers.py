"""
Model-specific wrappers for AI components.
"""
from typing import Any, Optional, Tuple
import numpy as np
import logging

from .adapters import BaseAdapter, AdapterConfig

logger = logging.getLogger(__name__)


class ModelAdapter(BaseAdapter):
    """Base adapter for ML models."""
    
    def __init__(self, config: AdapterConfig, model: Any = None):
        super().__init__(config)
        self.model = model
        self._input_shape: Optional[Tuple[int, ...]] = None
        self._output_shape: Optional[Tuple[int, ...]] = None
    
    async def process(self, data: Any) -> Any:
        """Run model inference."""
        if not self.config.enabled or not self.model:
            return None
        
        try:
            result = await self._run_inference(data)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            logger.error(f"Model inference failed: {e}")
            raise
    
    async def _run_inference(self, data: Any) -> Any:
        """Override for model-specific inference."""
        raise NotImplementedError
    
    def get_input_metadata(self) -> dict:
        """Return input shape info."""
        return {"input_shape": self._input_shape}
    
    def get_output_metadata(self) -> dict:
        """Return output shape info."""
        return {"output_shape": self._output_shape}


class FaceRecognitionWrapper(ModelAdapter):
    """Wrapper for face recognition models."""
    
    def __init__(self, config: AdapterConfig, model: Any = None):
        super().__init__(config, model)
        self._input_shape = (112, 112, 3)
        self._output_shape = (512,)
    
    async def _run_inference(self, face_image: np.ndarray) -> np.ndarray:
        """Compute face embedding."""
        embedding = self.model.get_embedding(face_image)
        self._output_shape = embedding.shape
        return embedding
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess face image."""
        height, width = self._input_shape[:2]
        if image.shape[:2] != (height, width):
            import cv2
            image = cv2.resize(image, (width, height))
        return image.astype(np.float32) / 255.0


class SpoofDetectionWrapper(ModelAdapter):
    """Wrapper for anti-spoofing models."""
    
    def __init__(self, config: AdapterConfig, model: Any = None):
        super().__init__(config, model)
        self._input_shape = (224, 224, 3)
        self._output_shape = (1,)
    
    async def _run_inference(self, face_image: np.ndarray) -> dict:
        """Run spoof detection."""
        score = self.model.predict(face_image)
        is_real = score[0] > 0.5 if isinstance(score, np.ndarray) else score > 0.5
        return {
            "is_real": bool(is_real),
            "confidence": float(score),
            "spoof_score": float(1 - score[0]) if isinstance(score, np.ndarray) else float(1 - score)
        }