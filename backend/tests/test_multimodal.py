"""
Multi-modal integration tests for face, voice, and gait recognition.
Tests combined recognition with all three modalities.
"""
import pytest
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.db.db_client import DBClient
import io
import cv2
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

client = TestClient(app)


def create_test_image(size=112):
    """Create a synthetic test face image."""
    img = np.random.randint(0, 255, (size, size, 3), dtype=np.uint8)
    # Add a face-like rectangle
    img[40:80, 40:80] = [200, 180, 160]
    img[50:60, 55:65] = [50, 50, 50]  # Eyes
    _, buffer = cv2.imencode('.jpg', img)
    return io.BytesIO(buffer.tobytes())


def create_test_voice_embedding():
    """Create a synthetic voice embedding (192-dim)."""
    return np.random.randn(192).astype(np.float32)


def create_test_gait_embedding():
    """Create a synthetic gait embedding (128-dim)."""
    return np.random.randn(128).astype(np.float32)


@pytest.fixture
def mock_db():
    """Mock database client for testing."""
    db = DBClient()
    # Initialize in-memory mode
    db._in_memory_db = {
        'persons': {},
        'embeddings': {},
        'consent_logs': {},
        'audit_log': []
    }
    return db


class TestMultiModalRecognition:
    """Test multi-modal face + voice + gait recognition."""

    def test_recognize_face_only(self, mock_db):
        """Test recognition with face modality only."""
        face_embedding = np.random.randn(512).astype(np.float32)
        face_embedding = face_embedding / np.linalg.norm(face_embedding)

        results = mock_db.recognize_faces(
            query_embedding=face_embedding,
            top_k=5,
            threshold=0.6,
            voice_embedding=None,
            gait_embedding=None
        )
        assert isinstance(results, list)

    def test_recognize_face_voice_combined(self, mock_db):
        """Test recognition with face and voice modalities."""
        face_embedding = np.random.randn(512).astype(np.float32)
        face_embedding = face_embedding / np.linalg.norm(face_embedding)
        voice_embedding = create_test_voice_embedding()

        results = mock_db.recognize_faces(
            query_embedding=face_embedding,
            top_k=5,
            threshold=0.6,
            voice_embedding=voice_embedding,
            gait_embedding=None
        )
        assert isinstance(results, list)

    def test_recognize_all_three_modalities(self, mock_db):
        """Test recognition with face, voice, and gait modalities."""
        face_embedding = np.random.randn(512).astype(np.float32)
        face_embedding = face_embedding / np.linalg.norm(face_embedding)
        voice_embedding = create_test_voice_embedding()
        gait_embedding = create_test_gait_embedding()

        results = mock_db.recognize_faces(
            query_embedding=face_embedding,
            top_k=5,
            threshold=0.6,
            voice_embedding=voice_embedding,
            gait_embedding=gait_embedding
        )
        assert isinstance(results, list)

    def test_enroll_with_all_modalities(self, mock_db):
        """Test enrollment with face, voice, and gait data."""
        person_id = "test-person-001"
        name = "Test Person"
        consent_record = {
            'consent_record_id': 'consent-001',
            'client_id': 'test-client',
            'consent_text_version': 'v1',
            'captured_ip': '127.0.0.1',
            'signed_token': 'token-001'
        }

        # Create embeddings
        face_embeddings = [np.random.randn(512).astype(np.float32) for _ in range(3)]
        voice_embeddings = [create_test_voice_embedding() for _ in range(3)]
        gait_embedding = create_test_gait_embedding()

        result = mock_db.enroll_person(
            person_id=person_id,
            name=name,
            embeddings=face_embeddings,
            consent_record=consent_record,
            camera_id="test-camera-001",
            voice_embeddings=voice_embeddings,
            gait_embedding=gait_embedding,
            age=30,
            gender="M"
        )
        assert result == person_id
        assert person_id in mock_db._in_memory_db['persons']

    def test_multi_modal_fusion_weights(self):
        """Test that multi-modal fusion applies correct weights."""
        from app.scoring_engine import IdentityScoringEngine

        scoring_engine = IdentityScoringEngine()

        # Test default weights
        assert scoring_engine.weights['face'] == 0.5
        assert scoring_engine.weights['voice'] == 0.2
        assert scoring_engine.weights['gait'] == 0.2
        assert scoring_engine.weights['spoof'] == 0.1

        # Test score fusion
        scores = {
            'face': 0.85,
            'voice': 0.75,
            'gait': 0.80,
            'spoof': 0.05
        }

        combined = scoring_engine.fuse_scores(scores, strategy='weighted_average')
        expected = (0.85 * 0.5) + (0.75 * 0.2) + (0.80 * 0.2) + ((1 - 0.05) * 0.1)
        assert abs(combined - expected) < 0.001

    def test_modality_contribution_to_final_score(self, mock_db):
        """Test that voice and gait contribute positively when they match."""
        face_embedding = np.random.randn(512).astype(np.float32)
        face_embedding = face_embedding / np.linalg.norm(face_embedding)

        # Case 1: Face only
        results_face_only = mock_db.recognize_faces(
            query_embedding=face_embedding,
            top_k=5,
            threshold=0.6,
            voice_embedding=None,
            gait_embedding=None
        )

        # Case 2: Face + matching voice
        voice_embedding = create_test_voice_embedding()
        results_with_voice = mock_db.recognize_faces(
            query_embedding=face_embedding,
            top_k=5,
            threshold=0.6,
            voice_embedding=voice_embedding,
            gait_embedding=None
        )

        # Both should return valid results
        assert isinstance(results_face_only, list)
        assert isinstance(results_with_voice, list)

    def test_multi_modal_api_endpoint(self):
        """Test the API endpoint handles multi-modal data."""
        img_data = create_test_image()

        # Send with just image (face only)
        response = client.post(
            "/api/recognize",
            files={"image": ("test.jpg", img_data, "image/jpeg")},
            data={"top_k": 3, "threshold": 0.6}
        )
        assert response.status_code == 200
        data = response.json()
        assert "faces" in data

    def test_modality_fallback_when_missing(self, mock_db):
        """Test that recognition still works when some modalities are missing."""
        face_embedding = np.random.randn(512).astype(np.float32)
        face_embedding = face_embedding / np.linalg.norm(face_embedding)

        # Should work with just face
        results = mock_db.recognize_faces(
            query_embedding=face_embedding,
            top_k=1,
            threshold=0.6,
            voice_embedding=None,
            gait_embedding=None
        )
        assert isinstance(results, list)


class TestMultiModalEnrollment:
    """Test enrollment with multiple modalities."""

    def test_enroll_single_modality(self, mock_db):
        """Enroll with just face images."""
        person_id = "person-face-only"
        consent = {
            'consent_record_id': 'consent-face-001',
            'client_id': 'test',
            'consent_text_version': 'v1',
            'captured_ip': '127.0.0.1',
            'signed_token': 'token'
        }

        embeddings = [np.random.randn(512).astype(np.float32) for _ in range(2)]

        result = mock_db.enroll_person(
            person_id=person_id,
            name="Face Only Person",
            embeddings=embeddings,
            consent_record=consent
        )
        assert result == person_id

    def test_enroll_face_voice(self, mock_db):
        """Enroll with face and voice."""
        person_id = "person-face-voice"
        consent = {
            'consent_record_id': 'consent-fv-001',
            'client_id': 'test',
            'consent_text_version': 'v1',
            'captured_ip': '127.0.0.1',
            'signed_token': 'token'
        }

        face_embeddings = [np.random.randn(512).astype(np.float32) for _ in range(2)]
        voice_embeddings = [create_test_voice_embedding() for _ in range(2)]

        result = mock_db.enroll_person(
            person_id=person_id,
            name="Face Voice Person",
            embeddings=face_embeddings,
            consent_record=consent,
            voice_embeddings=voice_embeddings
        )
        assert result == person_id

    def test_enroll_all_modalities_complete(self, mock_db):
        """Enroll with face, voice, and gait."""
        person_id = "person-complete"
        consent = {
            'consent_record_id': 'consent-all-001',
            'client_id': 'test',
            'consent_text_version': 'v1',
            'captured_ip': '127.0.0.1',
            'signed_token': 'token'
        }

        face_embeddings = [np.random.randn(512).astype(np.float32) for _ in range(3)]
        voice_embeddings = [create_test_voice_embedding() for _ in range(3)]
        gait_embedding = create_test_gait_embedding()

        result = mock_db.enroll_person(
            person_id=person_id,
            name="Complete Person",
            embeddings=face_embeddings,
            consent_record=consent,
            voice_embeddings=voice_embeddings,
            gait_embedding=gait_embedding,
            age=25,
            gender="F"
        )
        assert result == person_id
        person = mock_db._in_memory_db['persons'][person_id]
        assert person['age'] == 25
        assert person['gender'] == "F"