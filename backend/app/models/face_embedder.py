import numpy as np
import logging
import os

try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Model cache directory
MODEL_CACHE_DIR = os.getenv('MODEL_CACHE_DIR', os.path.join(os.path.dirname(__file__), '../../../models/weights'))


def _check_model_weights() -> bool:
    """Check if actual ArcFace model weights are available."""
    if not INSIGHTFACE_AVAILABLE:
        return False
    
    arcface_path = os.path.join(MODEL_CACHE_DIR, 'w600k_r50.onnx')
    buffalo_path = os.path.join(MODEL_CACHE_DIR, 'buffalo_l')
    
    return os.path.exists(arcface_path) or os.path.exists(os.path.join(buffalo_path, 'models', 'w600k_r50.onnx'))


class FaceEmbedder:
    def __init__(self):
        self.has_real_weights = _check_model_weights()
        
        if INSIGHTFACE_AVAILABLE and self.has_real_weights:
            try:
                model_path = os.path.join(MODEL_CACHE_DIR, 'buffalo_l')
                if os.path.exists(model_path):
                    self.app = FaceAnalysis(name=model_path, root=MODEL_CACHE_DIR)
                else:
                    self.app = FaceAnalysis(name='buffalo_l')
                
                self.app.prepare(ctx_id=0, det_size=(640, 640))
                logger.info("✓ FaceEmbedder: Using production ArcFace model (w600k_r50)")
            except Exception as e:
                logger.warning(f"FaceEmbedder: Failed to load model: {e}")
                logger.warning("FaceEmbedder: Falling back to mock embeddings")
                self.app = None
                self.has_real_weights = False
        elif INSIGHTFACE_AVAILABLE and not self.has_real_weights:
            logger.warning("=" * 70)
            logger.warning("CRITICAL: FaceEmbedder using MOCK embeddings")
            logger.warning(f"ArcFace model not found at: {MODEL_CACHE_DIR}/w600k_r50.onnx")
            logger.warning("Download weights: python scripts/download_models.py")
            logger.warning("=" * 70)
            self.app = None
        else:
            logger.warning("FaceEmbedder: InsightFace not available. Using mock embeddings.")
            self.app = None
    
    def get_embedding(self, image: np.ndarray) -> np.ndarray:
        """
        Compute normalized face embedding from aligned face image.
        Returns 1-D float32 vector (512-d for ArcFace).
        """
        if INSIGHTFACE_AVAILABLE and self.app:
            faces = self.app.get(image)
            if len(faces) == 0:
                raise ValueError("No face detected in image")
            
            # Use the first (highest confidence) face
            embedding = faces[0].embedding.astype(np.float32)
            
            # L2 normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding /= norm
            
            return embedding
        else:
            # Fallback: generate mock embedding based on image hash
            seed = hash((image.shape, image.mean()))
            np.random.seed(abs(seed) % 2**32)
            embedding = np.random.normal(0, 1, 512).astype(np.float32)
            
            # L2 normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding /= norm
            
            return embedding
