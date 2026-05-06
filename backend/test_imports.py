import sys
sys.path.append('.')

# Test model imports
try:
    from app.models.face_detector import FaceDetector
    print("[OK] FaceDetector imported successfully")
except Exception as e:
    print(f"[FAIL] FaceDetector import failed: {e}")

try:
    from app.models.face_embedder import FaceEmbedder
    print("[OK] FaceEmbedder imported successfully")
except Exception as e:
    print(f"[FAIL] FaceEmbedder import failed: {e}")

try:
    from app.models.emotion_detector import EmotionDetector
    print("[OK] EmotionDetector imported successfully")
except Exception as e:
    print(f"[FAIL] EmotionDetector import failed: {e}")

try:
    from app.models.age_gender_estimator import AgeGenderEstimator
    print("[OK] AgeGenderEstimator imported successfully")
except Exception as e:
    print(f"[FAIL] AgeGenderEstimator import failed: {e}")

try:
    from app.models.spoof_detector import SpoofDetector
    print("[OK] SpoofDetector imported successfully")
except Exception as e:
    print(f"[FAIL] SpoofDetector import failed: {e}")

try:
    from app.models.face_reconstructor import FaceReconstructor
    print("[OK] FaceReconstructor imported successfully")
except Exception as e:
    print(f"[FAIL] FaceReconstructor import failed: {e}")

try:
    from app.models.behavioral_predictor import BehavioralPredictor
    print("[OK] BehavioralPredictor imported successfully")
except Exception as e:
    print(f"[FAIL] BehavioralPredictor import failed: {e}")

try:
    from app.models.gait_analyzer import GaitAnalyzer
    print("[OK] GaitAnalyzer imported successfully")
except Exception as e:
    print(f"[FAIL] GaitAnalyzer import failed: {e}")

try:
    from app.models.voice_embedder import VoiceEmbedder
    print("[OK] VoiceEmbedder imported successfully")
except Exception as e:
    print(f"[FAIL] VoiceEmbedder import failed: {e}")

try:
    from app.models.bias_detector import BiasDetector
    print("[OK] BiasDetector imported successfully")
except Exception as e:
    print(f"[FAIL] BiasDetector import failed: {e}")

try:
    from app.models.crypto_attestation import CryptoAttestation
    print("[OK] CryptoAttestation imported successfully")
except Exception as e:
    print(f"[FAIL] CryptoAttestation import failed: {e}")

try:
    from app.models.ethical_governor import EthicalGovernor
    print("[OK] EthicalGovernor imported successfully")
except Exception as e:
    print(f"[FAIL] EthicalGovernor import failed: {e}")

# Test API imports
try:
    from app.api.enroll import router as enroll_router
    print("[OK] Enroll API imported successfully")
except Exception as e:
    print(f"[FAIL] Enroll API import failed: {e}")

try:
    from app.api.recognize import router as recognize_router
    print("[OK] Recognize API imported successfully")
except Exception as e:
    print(f"[FAIL] Recognize API import failed: {e}")

try:
    from app.api.stream_recognize import router as stream_recognize_router
    print("[OK] Stream Recognize API imported successfully")
except Exception as e:
    print(f"[FAIL] Stream Recognize API import failed: {e}")

try:
    from app.api.admin import router as admin_router
    print("[OK] Admin API imported successfully")
except Exception as e:
    print(f"[FAIL] Admin API import failed: {e}")

try:
    from app.api.ai_assistant import router as ai_assistant_router
    print("[OK] AI Assistant API imported successfully")
except Exception as e:
    print(f"[FAIL] AI Assistant API import failed: {e}")

# Test DB client
try:
    from app.db.db_client import get_db
    print("[OK] DB client imported successfully")
except Exception as e:
    print(f"[FAIL] DB client import failed: {e}")

# Test main app
try:
    from app.main import app
    print("[OK] FastAPI app imported successfully")
except Exception as e:
    print(f"[FAIL] FastAPI app import failed: {e}")

print("\nModel and API import test completed.")
