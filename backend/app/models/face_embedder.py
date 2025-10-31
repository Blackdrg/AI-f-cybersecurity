import numpy as np

try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False


class FaceEmbedder:
    def __init__(self):
        if INSIGHTFACE_AVAILABLE:
            # Includes ArcFace embedder
            self.app = FaceAnalysis(name='buffalo_l')
            self.app.prepare(ctx_id=0, det_size=(640, 640))
        else:
            # Fallback to mock embeddings
            self.app = None

    def get_embedding(self, image: np.ndarray) -> np.ndarray:
        """
        Compute normalized face embedding from aligned face image.
        Returns 1-D float32 vector (512-d for buffalo_l).
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
            # Use image shape and mean as seed for deterministic mock
            seed = hash((image.shape, image.mean()))
            np.random.seed(seed % 2**32)
            embedding = np.random.normal(0, 1, 512).astype(np.float32)

            # L2 normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding /= norm

            return embedding
