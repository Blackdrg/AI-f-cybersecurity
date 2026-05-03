# Insightface Installation Issue (Windows)

## Root Cause
`pip install insightface==0.7.3` fails on Windows with Python 3.11+ due to missing MSVC compiler (C++ extensions).

## Fixes (Choose One)

### 1. Easiest (Recommended for Dev)
Requirements updated - insightface commented out. Uses pre-exported ONNX models (`models/onnx_bundle/`).

**Install without compiler:**
```bash
cd backend
pip install -r requirements-cpu.txt  # or requirements-gpu.txt
```

✅ No compiler needed, full functionality.

### 2. Install Compiler (Full insightface)
Download [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Select: Desktop development with C++
- MSVC v143 (latest)
- Windows 11 SDK
- Restart terminal
```bash
pip install insightface==0.7.3
```

### 3. Python 3.10 (Stable Wheels)
```bash
# Use pyenv or conda
pyenv install 3.10.14
pyenv local 3.10.14
pip install insightface==0.7.3
```

### 4. Docker/WSL (Linux)
```bash
docker build -f backend/Dockerfile.cpu -t ai-f-cpu .
docker run -p 8000:8000 ai-f-cpu
```

### Model Regen (If Needed)
If you need to re-export ONNX:
1. Use Linux VM/Docker/Python 3.10
2. `pip install insightface==0.7.3 onnxruntime`
3. Run export script (not included; contact support)

**Status:** Fixed in requirements.txt - pip install now succeeds without compiler.

## Verify
```bash
pip install -r backend/requirements-cpu.txt  # Should succeed
pytest backend/tests/test_recognize.py  # ONNX fallback works
```

