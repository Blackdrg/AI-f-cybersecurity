import sys
sys.path.insert(0, 'backend')
from app.models.face_embedder import FaceEmbedder
e = FaceEmbedder()
print('FaceEmbedder created successfully')
print(f'INSIGHTFACE_AVAILABLE: {e.INSIGHTFACE_AVAILABLE}')
print(f'has_real_weights: {e.has_real_weights}')