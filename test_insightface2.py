import sys
sys.path.insert(0, 'backend')
import app.models.face_embedder as fe
print(f'INSIGHTFACE_AVAILABLE: {fe.INSIGHTFACE_AVAILABLE}')
e = fe.FaceEmbedder()
print('FaceEmbedder created successfully')
print(f'has_real_weights: {e.has_real_weights}')