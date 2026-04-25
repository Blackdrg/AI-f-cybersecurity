import sys
sys.path.append('.')

# Test model imports
try:
    from app.models.face_detector import FaceDetector
    print("✓ FaceDetector imported successfully")
except Exception as e:
    print(f"✗ FaceDetector import failed: {e}")

try:
    from app.models.face_embedder import FaceEmbedder
    print("✓ FaceEmbedder imported successfully")
except Exception as e:
    print(f"✗ FaceEmbedder import failed: {e}")

try:
    from app.models.emotion_detector import EmotionDetector
    print("✓ EmotionDetector imported successfully")
except Exception as e:
    print(f"✗ EmotionDetector import failed: {e}")

try:
    from app.models.age_gender_estimator import AgeGenderEstimator
    print("✓ AgeGenderEstimator imported successfully")
except Exception as e:
    print(f"✗ AgeGenderEstimator import failed: {e}")

try:
    from app.models.spoof_detector import SpoofDetector
    print("✓ SpoofDetector imported successfully")
except Exception as e:
    print(f"✗ SpoofDetector import failed: {e}")

try:
    from app.models.face_reconstructor import FaceReconstructor
    print("✓ FaceReconstructor imported successfully")
except Exception as e:
    print(f"✗ FaceReconstructor import failed: {e}")

try:
    from app.models.behavioral_predictor import BehavioralPredictor
    print("✓ BehavioralPredictor imported successfully")
except Exception as e:
    print(f"✗ BehavioralPredictor import failed: {e}")

try:
    from app.models.gait_analyzer import GaitAnalyzer
    print("✓ GaitAnalyzer imported successfully")
except Exception as e:
    print(f"✗ GaitAnalyzer import failed: {e}")

try:
    from app.models.voice_embedder import VoiceEmbedder
    print("✓ VoiceEmbedder imported successfully")
except Exception as e:
    print(f"✗ VoiceEmbedder import failed: {e}")

try:
    from app.models.bias_detector import BiasDetector
    print("✓ BiasDetector imported successfully")
except Exception as e:
    print(f"✗ BiasDetector import failed: {e}")

try:
    from app.models.crypto_attestation import CryptoAttestation
    print("✓ CryptoAttestation imported successfully")
except Exception as e:
    print(f"✗ CryptoAttestation import failed: {e}")

try:
    from app.models.ethical_governor import EthicalGovernor
    print("✓ EthicalGovernor imported successfully")
except Exception as e:
    print(f"✗ EthicalGovernor import failed: {e}")

# Test API imports
try:
    from app.api.enroll import router as enroll_router
    print("✓ Enroll API imported successfully")
except Exception as e:
    print(f"✗ Enroll API import failed: {e}")

try:
    from app.api.recognize import router as recognize_router
    print("✓ Recognize API imported successfully")
except Exception as e:
    print(f"✗ Recognize API import failed: {e}")

try:
    from app.api.stream_recognize import router as stream_recognize_router
    print("✓ Stream Recognize API imported successfully")
except Exception as e:
    print(f"✗ Stream Recognize API import failed: {e}")

try:
    from app.api.admin import router as admin_router
    print("✓ Admin API imported successfully")
except Exception as e:
    print(f"✗ Admin API import failed: {e}")

try:
    from app.api.ai_assistant import router as ai_assistant_router
    print("✓ AI Assistant API imported successfully")
except Exception as e:
    print(f"✗ AI Assistant API import failed: {e}")

# Test DB client
try:
    from app.db.db_client import get_db
    print("✓ DB client imported successfully")
except Exception as e:
    print(f"✗ DB client import failed: {e}")

# Test main app
try:
    from app.main import app
    print("✓ FastAPI app imported successfully")
except Exception as e:
    print(f"✗ FastAPI app import failed: {e}")

print("\nModel and API import test completed.")
