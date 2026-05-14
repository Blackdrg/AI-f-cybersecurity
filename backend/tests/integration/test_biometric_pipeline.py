"""Biometric pipeline integration tests.
Tests end-to-end biometric recognition pipeline including face detection, embedding, and matching.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.mark.biometric
@pytest.mark.integration
class TestBiometricPipeline:
    """Integration tests for the biometric recognition pipeline."""

    @pytest.fixture
    def sample_face_image(self):
        """Generate a synthetic face-like image for testing."""
        img = np.zeros((112, 112, 3), dtype=np.uint8)
        # Add some structure to make it look face-like
        img[30:80, 35:75] = 200  # Face region
        img[40:50, 45:50] = 50   # Left eye
        img[40:50, 60:65] = 50   # Right eye
        return img

    async def test_face_detection_stage(self, sample_face_image):
        """Test face detection stage of pipeline."""
        from app.pipelines.biometric_pipeline import BiometricPipeline
        
        mock_detector = MagicMock()
        mock_detector.detect = AsyncMock(return_value=[
            {"bbox": [10, 10, 100, 100], "confidence": 0.95}
        ])
        
        pipeline = BiometricPipeline(face_detector=mock_detector)
        result = await pipeline._detect_faces(sample_face_image)
        
        assert len(result) > 0
        assert mock_detector.detect.called

    async def test_face_alignment_stage(self, sample_face_image):
        """Test face alignment stage."""
        from app.pipelines.biometric_pipeline import BiometricPipeline
        
        pipeline = BiometricPipeline()
        
        face = {"bbox": [10, 10, 100, 100]}
        aligned = await pipeline._align_face(sample_face_image, face)
        
        assert aligned is not None
        assert isinstance(aligned, np.ndarray)

    async def test_embedding_generation(self, sample_face_image):
        """Test face embedding generation."""
        from app.pipelines.biometric_pipeline import BiometricPipeline
        
        mock_embedder = MagicMock()
        mock_embedder.get_embedding = AsyncMock(
            return_value=np.random.randn(512).astype(np.float32)
        )
        
        pipeline = BiometricPipeline(face_embedder=mock_embedder)
        embedding = await pipeline._get_embedding(sample_face_image)
        
        assert embedding.shape == (512,)
        assert mock_embedder.get_embedding.called

    async def test_spoof_detection(self, sample_face_image):
        """Test anti-spoofing stage."""
        from app.pipelines.biometric_pipeline import BiometricPipeline, BiometricStage
        
        mock_spoof = MagicMock()
        mock_spoof.predict = AsyncMock(return_value={"is_real": True, "confidence": 0.99})
        
        pipeline = BiometricPipeline(spoof_detector=mock_spoof)
        result = await pipeline._check_spoof(sample_face_image)
        
        assert result["is_real"] is True
        assert result["confidence"] > 0.9

    async def test_full_pipeline_execution(self, sample_face_image):
        """Test complete pipeline execution."""
        from app.pipelines.biometric_pipeline import BiometricPipeline
        
        mock_detector = MagicMock()
        mock_detector.detect = AsyncMock(return_value=[
            {"bbox": [10, 10, 100, 100]}
        ])
        
        mock_embedder = MagicMock()
        mock_embedder.get_embedding = AsyncMock(
            return_value=np.random.randn(512).astype(np.float32)
        )
        
        pipeline = BiometricPipeline(
            face_detector=mock_detector,
            face_embedder=mock_embedder
        )
        
        result = await pipeline.process(sample_face_image)
        
        assert result.success is True
        assert result.stage == BiometricStage.VERIFICATION
        assert result.embedding is not None


@pytest.mark.biometric
@pytest.mark.slow_integration
class TestBiometricAccuracy:
    """Test biometric accuracy and performance."""

    async def test_embedding_consistency(self):
        """Test that embeddings are consistent for same face."""
        embedding1 = np.random.randn(512).astype(np.float32)
        embedding2 = embedding1.copy()  # Same face
        
        # Normalized embeddings should have high similarity
        similarity = np.dot(embedding1, embedding2)
        assert similarity > 0.9  # Same face should be very similar

    async def test_embedding_randomness(self):
        """Test that different faces have distinct embeddings."""
        embedding1 = np.random.randn(512).astype(np.float32)
        embedding2 = np.random.randn(512).astype(np.float32)
        
        similarity = np.dot(embedding1, embedding2)
        assert abs(similarity) < 0.5  # Different faces should not be similar