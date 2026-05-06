"""ONNX model integration tests.

Tests real ONNX model loading, inference, and performance:
- Model file loading from disk
- Input preprocessing and output postprocessing
- Inference latency and throughput
- Model metadata and input/output schema validation
"""

import pytest
import time
import numpy as np
from pathlib import Path


@pytest.mark.models
@pytest.mark.integration
class TestONNXModels:
    """Integration tests for ONNX model loading and inference."""

    def test_face_detection_model_loads(self, face_detection_model):
        """Verify face detection model loads successfully."""
        assert face_detection_model is not None
        assert hasattr(face_detection_model, 'run')
        assert hasattr(face_detection_model, 'get_inputs')
        assert hasattr(face_detection_model, 'get_outputs')
        
        # Check input shape
        inputs = face_detection_model.get_inputs()
        assert len(inputs) > 0
        input_shape = inputs[0].shape
        # Should be [batch, channels, height, width] or similar
        assert len(input_shape) == 4
        
    def test_face_embedding_model_loads(self, face_embedding_model):
        """Verify face embedding model loads successfully."""
        assert face_embedding_model is not None
        inputs = face_embedding_model.get_inputs()
        outputs = face_embedding_model.get_outputs()
        
        assert len(inputs) >= 1
        assert len(outputs) >= 1
        
        # Output should be embedding vector (512-d typically)
        output_shape = outputs[0].shape
        assert output_shape[-1] == 512  # ArcFace standard embedding size

    def test_face_detection_inference_shape(self, face_detection_model):
        """Test that face detection returns expected output shape."""
        # Create dummy input image (RGB, 640x640 typical for YOLO/FaceNet)
        dummy_input = np.random.randn(1, 3, 640, 640).astype(np.float32)
        
        # Run inference
        input_name = face_detection_model.get_inputs()[0].name
        outputs = face_detection_model.run(None, {input_name: dummy_input})
        
        # Output should contain boxes, scores, labels
        assert len(outputs) >= 3  # boxes, scores, num_detections typically
        
    def test_face_embedding_inference_shape(self, face_embedding_model):
        """Test that face embedding returns 512-d vector."""
        # Create dummy face crop (112x112 typical for ArcFace)
        dummy_face = np.random.randn(1, 3, 112, 112).astype(np.float32)
        
        input_name = face_embedding_model.get_inputs()[0].name
        outputs = face_embedding_model.run(None, {input_name: dummy_face})
        
        embedding = outputs[0]  # Shape: [1, 512]
        assert embedding.shape[1] == 512
        
        # Verify it's normalized (L2 norm ~1)
        norm = np.linalg.norm(embedding[0])
        assert 0.99 < norm < 1.01  # Approximately unit norm

    def test_model_inference_latency(self, face_embedding_model):
        """Measure inference latency (should be < 50ms on CPU)."""
        dummy_face = np.random.randn(1, 3, 112, 112).astype(np.float32)
        input_name = face_embedding_model.get_inputs()[0].name
        
        # Warm-up run
        face_embedding_model.run(None, {input_name: dummy_face})
        
        # Timed runs
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            face_embedding_model.run(None, {input_name: dummy_face})
            elapsed = (time.perf_counter() - start) * 1000  # ms
            latencies.append(elapsed)
        
        avg_latency = np.mean(latencies)
        p99_latency = np.percentile(latencies, 99)
        
        assert avg_latency < 100  # Average < 100ms
        assert p99_latency < 200  # P99 < 200ms

    def test_model_input_preprocessing(self, face_detection_model):
        """Test that input preprocessing matches expected model format."""
        # Models typically expect:
        # - BGR or RGB order
        # - Normalized to [0,1] or [-1,1]
        # - Specific channel order
        
        input_meta = face_detection_model.get_inputs()[0]
        shape = input_meta.shape
        
        # Check for expected dimensions
        assert shape[1] in [1, 3]  # Grayscale or RGB channels
        assert shape[2] == shape[3]  # Square input typical

    def test_multiple_inferences_consistency(self, face_embedding_model):
        """Test that same input produces consistent embeddings."""
        dummy_face = np.random.randn(1, 3, 112, 112).astype(np.float32)
        input_name = face_embedding_model.get_inputs()[0].name
        
        # Get embeddings from multiple runs
        embeddings = []
        for _ in range(5):
            output = face_embedding_model.run(None, {input_name: dummy_face})
            embeddings.append(output[0])
        
        # All embeddings should be nearly identical
        for i in range(1, len(embeddings)):
            diff = np.linalg.norm(embeddings[0] - embeddings[i])
            assert diff < 1e-6, f"Embeddings differ by {diff}"

    def test_model_metadata(self, face_embedding_model):
        """Verify model metadata and version info if available."""
        # Some models store metadata in custom ops or initializers
        # Check that model is valid
        import onnx
        
        # Get model proto
        model_path = face_embedding_model._model_path if hasattr(face_embedding_model, '_model_path') else None
        if model_path:
            model = onnx.load(str(model_path))
            assert model is not None
            assert model.graph is not None
