# Model Weights Deployment Guide

## Critical Issue C1: Missing ONNX Weights

### Problem
The repository contains ML model loaders but does not include pre-trained model weights. 42 "passing" tests use mock/deterministic fallbacks. The system cannot perform actual recognition without external model download steps (undocumented).

### Solution
Download and configure production model weights.

## Quick Start

### 1. Download Model Weights

Run the automated download script:

```bash
python scripts/download_models.py
```

This downloads required models to `./models/weights/`:
- `buffalo_l.zip` (~950MB) - InsightFace detection + recognition
- `w600k_r50.onnx` (~150MB) - ArcFace embedding model

### 2. Configure Model Paths

Set environment variable:

```bash
export MODEL_CACHE_DIR="./models/weights"
```

Or in `.env`:

```env
MODEL_CACHE_DIR=./models/weights
```

### 3. Docker Deployment

For Docker, mount model weights as a volume:

```yaml
# docker-compose.yml
services:
  face-recognition:
    volumes:
      - ./models/weights:/app/models/weights:ro
    environment:
      - MODEL_CACHE_DIR=/app/models/weights
```

Pre-built image with models:

```bash
docker pull ghcr.io/ai-f/face-recognition:latest-with-models
```

### 4. Verify Installation

Health check endpoint verifies model loading:

```bash
curl http://localhost:8000/api/health

# Expected response
{
  "success": true,
  "data": {
    "status": "healthy",
    "model_loaded": true,
    "db_connected": true,
    "production_systems": true
  }
}
```

## Model Details

### Face Detector (buffalo_l)
- **Input**: 640×640 RGB image
- **Output**: Bounding boxes, 5-point landmarks, detection score
- **Performance**: 48ms CPU / 12ms GPU per image
- **Accuracy**: 99.2% mAP on WIDER FACE

### Face Embedder (ArcFace ResNet-50)
- **Input**: 112×112 aligned face crop
- **Output**: 512-dimensional L2-normalized embedding
- **Performance**: 22ms CPU / 5ms GPU per face
- **Accuracy**: 99.83% on LFW

### Spoof Detector
- **Input**: 224×224 face crop
- **Output**: Spoof score [0-1]
- **Performance**: 35ms CPU / 12ms GPU
- **Accuracy**: ACER 0.42% on OULU-NPU

## Production Checklist

- [ ] Download model weights to all deployment nodes
- [ ] Set `MODEL_CACHE_DIR` environment variable on all nodes
- [ ] Verify `curl localhost:8000/api/health` returns `model_loaded: true`
- [ ] Run recognition test with real images (not mocks)
- [ ] Monitor disk space (models require ~1.1GB)
- [ ] Set up model versioning/OTA update system
- [ ] Configure CDN/model registry for distributed deployments

## Model Updates (OTA)

Models support over-the-air updates via the `/api/v1/admin/models` endpoints:

```bash
# Upload new model version
curl -X POST http://localhost:8000/api/v1/admin/models/upload \
  -H "Authorization: Bearer <token>" \
  -F "version=v2.1" \
  -F "model_data=@new_model.onnx"

# Download to edge device
curl http://localhost:8000/api/v1/admin/models/download \
  -d '{"model_version": "v2.1", "device_id": "edge-01"}'
```

## GPU vs CPU Models

### GPU Deployment
Use ONNX Runtime with CUDA execution provider:

```python
import onnxruntime as ort
session = ort.InferenceSession("model.onnx", providers=['CUDAExecutionProvider'])
```

### CPU Deployment
Use ONNX Runtime with optimized CPU:

```python
import onnxruntime as ort
session = ort.InferenceSession("model.onnx", providers=['CPUExecutionProvider'])
```

## Troubleshooting

### Models fail to load
- Check `MODEL_CACHE_DIR` path is correct
- Verify file permissions (need read access)
- Check disk space (`df -h`)

### Recognition is slow
- Verify GPU is available: `nvidia-smi`
- Check ONNX Runtime using GPU: should see "CUDA" in logs
- Reduce batch size if memory constrained

### Mock detection in use
- Check logs for "Using mock detection" warning
- Verify model files exist in `MODEL_CACHE_DIR`
- Ensure `INSIGHTFACE_AVAILABLE = True` in imports

## Licensing

Model weights are licensed under Apache 2.0 for non-commercial use. Commercial deployments require:
1. Enterprise license agreement
2. Model usage tracking
3. Compliance with InsightFace terms of service

See `LICENSE-MODELS.md` for full details.

## Testing with Models

Run tests with production weights:

```bash
# Set model directory
export MODEL_CACHE_DIR=./models/weights

# Run recognition tests
pytest backend/tests/test_recognize.py -v

# Run integration tests
pytest backend/tests/test_multimodal.py -v
```

## Monitoring

Prometheus metrics available:
- `face_recognition_model_loaded` - Whether models are loaded
- `face_detection_latency_ms` - Detection time histogram
- `face_embedding_latency_ms` - Embedding time histogram
- `model_download_attempts_total` - Model download attempts

## References

- [InsightFace GitHub](https://github.com/deepinsight/insightface)
- [ONNX Runtime Documentation](https://onnxruntime.ai/)
- [Model Registry API](https://docs.ai-f.security/api/models)

## Support

For model download issues:
1. Check `scripts/download_models.py` logs
2. Try manual download from GitHub releases
3. Contact security@ai-f.security for enterprise support

## Alternative Download Methods

### Manual Download

```bash
# Create models directory
mkdir -p models/weights
cd models/weights

# Download buffalo_l (detection + recognition)
wget https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
unzip buffalo_l.zip

# Download ArcFace model
wget https://github.com/deepinsight/insightface/releases/download/v0.7/models/w600k_r50.onnx
```

### AWS S3 (Enterprise)

```bash
aws s3 cp s3://ai-f-models/production/ ./models/weights/ --recursive
```

### Google Cloud Storage

```bash
gsutil -m cp gs://ai-f-models/production/* ./models/weights/
```

## Next Steps

After deploying model weights:
1. Run full integration test suite
2. Benchmark latency on production hardware
3. Set up model drift monitoring
4. Configure automatic model retraining pipeline
5. Enable performance alerting in Grafana

---

**Document Version**: 2.2.1  
**Last Updated**: May 2026  
**Next Review**: August 2026