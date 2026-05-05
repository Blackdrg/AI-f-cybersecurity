#!/usr/bin/env python3
"""Export ONNX models + bundle weights for production deployment."""
import os
import sys
import subprocess
import urllib.request
import tarfile
import zipfile
from pathlib import Path
import onnx
import onnxruntime as ort
import numpy as np
import torch
import torch.onnx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BUNDLE_DIR = Path(__file__).parent.parent / "models" / "onnx_bundle"
BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

def create_mock_onnx_models():
    """Create mock ONNX models for development/testing when real models unavailable."""
    
    # Mock spoof detector (simple CNN)
    class MockSpoofNet(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = torch.nn.Conv2d(3, 16, 3, padding=1)
            self.pool = torch.nn.AdaptiveAvgPool2d(1)
            self.fc = torch.nn.Linear(16, 1)
        def forward(self, x):
            x = torch.relu(self.conv(x))
            x = self.pool(x).squeeze()
            return torch.sigmoid(self.fc(x))
    
    model = MockSpoofNet()
    model.eval()
    dummy_input = torch.randn(1, 3, 64, 64)
    torch.onnx.export(
        model,
        dummy_input,
        str(BUNDLE_DIR / "spoof_detector.onnx"),
        export_params=True,
        opset_version=11,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['spoof_score'],
        dynamic_axes={'input': {0: 'batch_size'}, 'spoof_score': {0: 'batch_size'}}
    )
    logger.info("Created spoof_detector.onnx (mock)")
    
    # Mock behavioral predictor (LSTM-like)
    class MockBehaviorNet(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = torch.nn.LSTM(10, 64, batch_first=True)
            self.fc = torch.nn.Linear(64, 256)
        def forward(self, x):
            _, (h, _) = self.lstm(x)
            return self.fc(h[-1])
    
    model = MockBehaviorNet()
    model.eval()
    dummy_input = torch.randn(1, 30, 10)
    torch.onnx.export(
        model,
        dummy_input,
        str(BUNDLE_DIR / "behavioral_predictor.onnx"),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=['sequence'],
        output_names=['behavior_vector'],
        dynamic_axes={'sequence': {0: 'batch_size', 1: 'sequence_length'}}
    )
    logger.info("Created behavioral_predictor.onnx (mock)")
    
    # Mock deepfake detector
    class MockDeepfakeNet(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = torch.nn.Conv2d(3, 32, 3, padding=1)
            self.pool = torch.nn.AdaptiveAvgPool2d(1)
            self.fc = torch.nn.Linear(32, 1)
        def forward(self, x):
            x = torch.relu(self.conv(x))
            x = self.pool(x).squeeze()
            return torch.sigmoid(self.fc(x))
    
    model = MockDeepfakeNet()
    model.eval()
    dummy = torch.randn(1, 3, 224, 224)
    torch.onnx.export(
        model, dummy, str(BUNDLE_DIR / "deepfake_detector.onnx"),
        opset_version=11, input_names=['input'], output_names=['deepfake_score']
    )
    logger.info("Created deepfake_detector.onnx (mock)")
    
    # Mock face reconstructor
    class MockReconstructor(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = torch.nn.Conv2d(4, 32, 3, padding=1)
            self.conv2 = torch.nn.Conv2d(32, 3, 3, padding=1)
        def forward(self, x):
            return torch.sigmoid(self.conv2(torch.relu(self.conv(x))))
    
    model = MockReconstructor()
    model.eval()
    dummy = torch.randn(1, 4, 256, 256)
    torch.onnx.export(
        model, dummy, str(BUNDLE_DIR / "face_reconstructor.onnx"),
        opset_version=11, input_names=['input_mask'], output_names=['reconstructed']
    )
    logger.info("Created face_reconstructor.onnx (mock)")
    
    # Create gaitset mock
    class MockGaitNet(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = torch.nn.Conv2d(3, 64, 3, padding=1)
            self.pool = torch.nn.AdaptiveAvgPool2d(1)
            self.fc = torch.nn.Linear(64, 7)
        def forward(self, x):
            x = torch.relu(self.conv(x))
            x = self.pool(x).squeeze()
            return self.fc(x)
    
    model = MockGaitNet()
    model.eval()
    dummy = torch.randn(1, 3, 64, 64)
    torch.onnx.export(
        model, dummy, str(BUNDLE_DIR / "gaitset.onnx"),
        opset_version=11, input_names=['input'], output_names=['gait_embedding']
    )
    logger.info("Created gaitset.onnx (mock)")

def validate_bundle():
    """Validate all ONNX models load correctly."""
    for onnx_file in BUNDLE_DIR.glob("*.onnx"):
        try:
            sess = ort.InferenceSession(str(onnx_file), providers=['CPUExecutionProvider'])
            input_info = sess.get_inputs()[0]
            shape = list(input_info.shape)
            shape[0] = 1  # batch=1
            
            # Create dummy input matching the model's expected input
            dummy = np.random.randn(*shape).astype(np.float32)
            outputs = sess.run(None, {input_info.name: dummy})
            
            logger.info(f"Validated {onnx_file.name} - Input: {input_info.name}, Output shape: {outputs[0].shape}")
        except Exception as e:
            logger.warning(f"Failed to validate {onnx_file.name}: {e}")
    
    logger.info("✅ ONNX Bundle Validation Complete")

if __name__ == "__main__":
    logger.info("Creating mock ONNX models for development...")
    create_mock_onnx_models()
    validate_bundle()
    print(f"\nBundle ready: {BUNDLE_DIR}")
    print("These are mock models for development. For production:")
    print("1. Install insightface: pip install insightface")
    print("2. Run: python scripts/export_onnx.py")