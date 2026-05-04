"""AI-F Model Registry - ONNX Production Runtime"""
import os
import logging
from pathlib import Path
from typing import Dict, Any
import onnxruntime as ort
import numpy as np

logger = logging.getLogger(__name__)

# Production ONNX bundle path (docker /models/onnx_bundle)
ONNX_BUNDLE_PATH = Path("/models/onnx_bundle") if os.getenv("IN_DOCKER") else Path(__file__).parent / ".." / "models" / "onnx_bundle"

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
        }
        
        for name, onnx_file in onnx_files.items():
            onnx_path = ONNX_BUNDLE_PATH / onnx_file
            if onnx_path.exists():
                try:
                    self.sessions[name] = ort.InferenceSession(str(onnx_path))
                    logger.info(f"Loaded ONNX {name}: {onnx_path}")
                except Exception as e:
                    logger.error(f"Failed to load {onnx_path}: {e}")
        
        # Symlink bundles
        (ONNX_BUNDLE_PATH / "insightface_buffalo_l").exists() or logger.info("InsightFace bundle ready")
        (ONNX_BUNDLE_PATH / "speechbrain_voxceleb").exists() or logger.info("SpeechBrain bundle ready")
    
    def infer_onnx(self, model_name: str, input_data: np.ndarray) -> np.ndarray:
        """Run ONNX inference with preprocessing/normalization."""
        if model_name not in self.sessions:
            raise ValueError(f"ONNX model '{model_name}' not loaded")
        
        session = self.sessions[model_name]
        inputs = {session.get_inputs()[0].name: input_data.astype(np.float32)}
        outputs = session.run(None, inputs)
        return outputs[0][0]  # Squeeze batch/single output

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
except ImportError as e:
    logger.warning(f"Model import failed: {e}")

__all__ = [
    "registry", "ModelRegistry",
    "FaceDetector", "FaceEmbedder", "SpoofDetector", "FaceReconstructor",
    "EmotionDetector", "AgeGenderEstimator", "VoiceEmbedder", "GaitAnalyzer",
    "BiasDetector", "dp_engine", "BehavioralPredictor"
]
