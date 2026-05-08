"""AI-F Model Registry - ONNX Production Runtime"""
import os
import logging
from pathlib import Path
from typing import Dict, Any
import onnxruntime as ort
import numpy as np

logger = logging.getLogger(__name__)

# Production ONNX bundle path (docker /models/onnx_bundle)
import os
ONNX_BUNDLE_PATH = Path("/models/onnx_bundle") if os.getenv("IN_DOCKER") else Path(__file__).parent.parent.parent / "models" / "onnx_bundle"

class ModelRegistry:
    def __init__(self):
        self.sessions: Dict[str, ort.InferenceSession] = {}
        self.init_onnx_bundle()
    
    def init_onnx_bundle(self):
        """Load production ONNX models from bundle. Fallback to legacy PyTorch."""
        if not ONNX_BUNDLE_PATH.exists():
            logger.warning(f"ONNX bundle missing: {ONNX_BUNDLE_PATH}. Using PyTorch fallback.")
            return
        
        onnx_files = {
            "spoof_detector": "spoof_detector.onnx",
            "deepfake_detector": "deepfake_detector.onnx",
            "face_reconstructor": "face_reconstructor.onnx",
            "face_embedding": "insightface_buffalo_l.onnx",
            "face_detection": "retinaface.onnx",
            "xception_spoof": "xceptionnet_spoof_detector.onnx",
            "behavioral_predictor": "behavioral_predictor.onnx",
            "gait_analyzer": "gaitset.onnx",
        }
        
        for name, onnx_file in onnx_files.items():
            onnx_path = ONNX_BUNDLE_PATH / onnx_file
            if onnx_path.exists():
                try:
                    self.sessions[name] = ort.InferenceSession(str(onnx_path))
                    logger.info(f"Loaded ONNX {name}: {onnx_path}")
                except Exception as e:
                    logger.error(f"Failed to load {onnx_path}: {e}")
        
            else:
                logger.debug(f"ONNX model not found: {onnx_path}")

        loaded_count = len(self.sessions)
        logger.info(f"Loaded {loaded_count} ONNX models from bundle: {ONNX_BUNDLE_PATH}")
    
    def infer_onnx(self, model_name: str, input_data: np.ndarray) -> np.ndarray:
        """Run ONNX inference with preprocessing/normalization."""
        if model_name not in self.sessions:
            raise ValueError(f"ONNX model '{model_name}' not loaded")
        
        session = self.sessions[model_name]
        inputs = {session.get_inputs()[0].name: input_data.astype(np.float32)}
        outputs = session.run(None, inputs)
        output = outputs[0]
        # Handle both scalar and array outputs
        if isinstance(output, np.ndarray):
            if output.ndim == 0:
                return output
            elif output.ndim == 1 and len(output) == 1:
                return output[0]
            elif output.ndim >= 2:
                return output[0]  # Squeeze batch dim only
            return output
        # Scalar float/int
        return output

# Global production registry
registry = ModelRegistry()

# Legacy imports (PyTorch fallback if ONNX unavailable)
try:
    from .face_detector import FaceDetector
    from .face_embedder import FaceEmbedder
    from .spoof_detector import SpoofDetector
    from .face_reconstructor import FaceReconstructor
    from .emotion_detector import EmotionDetector
    from .age_gender_estimator import AgeGenderEstimator
    from .voice_embedder import VoiceEmbedder
    from .gait_analyzer import GaitAnalyzer
    from .bias_detector import BiasDetector
    from .privacy_engine import dp_engine
    from .behavioral_predictor import BehavioralPredictor
    from .hallucination_detector import HallucinationDetector, hallucination_detector
    from .uncertainty_estimator import UncertaintyEstimator, uncertainty_estimator
    from ..scoring_engine import ConfidenceCalibrator, confidence_calibrator
except ImportError as e:
    logger.warning(f"Model import failed: {e}")

__all__ = [
    "registry", "ModelRegistry",
    "FaceDetector", "FaceEmbedder", "SpoofDetector", "FaceReconstructor",
    "EmotionDetector", "AgeGenderEstimator", "VoiceEmbedder", "GaitAnalyzer",
    "BiasDetector", "dp_engine", "BehavioralPredictor",
    "HallucinationDetector", "hallucination_detector",
    "UncertaintyEstimator", "uncertainty_estimator",
    "ConfidenceCalibrator", "confidence_calibrator"
]
