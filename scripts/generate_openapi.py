#!/usr/bin/env python3
"""
Generate OpenAPI specification from FastAPI app and save to file.
Run: python scripts/generate_openapi.py
"""
import sys
import os
from unittest.mock import MagicMock

# Stub out heavy optional dependencies that aren't needed for OpenAPI generation
# Only mock if they cannot be imported
MOCK_MODULES = [
    'torch', 'torchvision', 'torchaudio',
    'sklearn', 'sklearn.ensemble',
    'cv2', 'insightface', 'speechbrain', 'librosa', 'fer',
    'fairlearn', 'onnxruntime', 'onnx',
    'numpy',
]

import importlib
for mod in MOCK_MODULES:
    try:
        importlib.import_module(mod)
    except ImportError:
        # Module not available, mock it
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()
    except Exception:
        # Any other error (e.g., GPU-specific load failures) - treat as unavailable
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()

# Also stub torch specific classes if torch is mocked
if 'torch' in sys.modules and type(sys.modules['torch']).__name__ == 'MagicMock':
    torch_mock = sys.modules['torch']
    torch_mock.nn = MagicMock()
    torch_mock.randn = MagicMock(return_value=MagicMock())
    torch_mock.onnx = MagicMock()
    torch_mock.cuda = MagicMock()

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from app.main import app
except Exception as e:
    print(f"Failed to import app: {e}")
    sys.exit(1)

def generate():
    # Get OpenAPI schema
    openapi_schema = app.openapi()
    
    # Ensure docs directory exists
    docs_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    
    output_path = os.path.join(docs_dir, 'api_spec.yaml')
    
    # Convert JSON to YAML
    try:
        import yaml
        with open(output_path, 'w') as f:
            yaml.dump(openapi_schema, f, sort_keys=False)
    except ImportError:
        # Fallback to JSON
        output_path = output_path.replace('.yaml', '.json')
        with open(output_path, 'w') as f:
            import json
            json.dump(openapi_schema, f, indent=2)
    
    print(f"OpenAPI spec written to {output_path} ({os.path.getsize(output_path)} bytes)")

if __name__ == "__main__":
    generate()
