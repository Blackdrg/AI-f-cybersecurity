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
try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    logger.warning("insightface not available, skipping buffalo_l download")

try:
    import speechbrain
    from speechbrain.pretrained import EncoderClassifier
    SPEECHBRAIN_AVAILABLE = True
except ImportError:
    SPEECHBRAIN_AVAILABLE = False
    logger.warning("speechbrain not available, skipping voxceleb download")
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BUNDLE_DIR = Path(__file__).parent.parent / "models" / "onnx_bundle"
BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

def download_insightface_buffalo_l():
    """Download InsightFace buffalo_l weights."""
    if not INSIGHTFACE_AVAILABLE:
        logger.warning("Skipping InsightFace download (missing dependency)")
        return
    cache_dir = Path.home() / ".insightface" / "models" / "buffalo_l"
    if not cache_dir.exists():
        app = FaceAnalysis(name='buffalo_l')
        app.prepare(ctx_id=0, det_size=(640,640))
    # Create symlink only if cache_dir exists
    if cache_dir.exists():
        (BUNDLE_DIR / "insightface_buffalo_l").symlink_to(cache_dir, target_is_directory=True)
        logger.info(f"Bundled InsightFace buffalo_l: {cache_dir}")

def download_speechbrain_voxceleb():
    """Download SpeechBrain VoxCeleb speaker embedding model."""
    if not SPEECHBRAIN_AVAILABLE:
        logger.warning("Skipping SpeechBrain download (missing dependency)")
        return
    model = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=str(BUNDLE_DIR / "speechbrain_voxceleb")
    )
    torch.save(model, BUNDLE_DIR / "speechbrain_voxceleb" / "model.pt")
    logger.info("Bundled SpeechBrain VoxCeleb")

def export_spoof_detector_onnx():
    """Train simple spoof CNN and export to ONNX."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "models"))
    from spoof_detector import SpoofNet  # noqa
    
    model = SpoofNet()
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
    logger.info("Exported spoof_detector.onnx")

def export_behavioral_lstm_onnx():
    """Train/export LSTM behavioral predictor to ONNX."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "models"))
    from behavioral_predictor import LSTMBehaviorNet
    
    model = LSTMBehaviorNet()
    model.eval()
    dummy_input = torch.randn(1, 30, 10)  # batch, seq, features
    torch.onnx.export(
        model,
        dummy_input,
        str(BUNDLE_DIR / "behavioral_predictor.onnx"),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=['sequence'],
        output_names=['behavior_vector'],
        dynamic_axes={'sequence' : {0 : 'batch_size', 1 : 'sequence_length'}}
    )
    logger.info("Exported behavioral_predictor.onnx (LSTM 256-dim)")

def export_deepfake_detector_onnx():
    """Placeholder: export deepfake model (e.g., Xception-based)."""

    # In production: load/train MesoNet/Xception + export
    # Mock for now - replace with real training
    class DeepfakeNet(torch.nn.Module):
        def __init__(self): super().__init__(); self.fc = torch.nn.Linear(2048, 1)
        def forward(self, x): return torch.sigmoid(self.fc(x.mean(dim=[2,3])))
    
    model = DeepfakeNet()
    dummy = torch.randn(1, 3, 224, 224)
    torch.onnx.export(model, dummy, str(BUNDLE_DIR / "deepfake_detector.onnx"), 
                      opset_version=11, input_names=['input'], output_names=['deepfake_score'])
    logger.info("Exported deepfake_detector.onnx (mock - needs real training)")

def export_face_reconstructor_onnx():
    """Export GAN-based reconstructor (placeholder Navier-Stokes -> ONNX)."""
    # Real: pix2pix/LaMa GAN. Mock UNet for inpainting.
    class InpaintUNet(torch.nn.Module):
        def __init__(self): 
            super().__init__()
            self.conv = torch.nn.Conv2d(4, 3, 3, padding=1)  # image + mask -> output
        def forward(self, x): return torch.sigmoid(self.conv(x))
    
    model = InpaintUNet()
    dummy = torch.randn(1, 4, 256, 256)  # RGB + mask
    torch.onnx.export(model, dummy, str(BUNDLE_DIR / "face_reconstructor.onnx"),
                      opset_version=11, input_names=['input_mask'], output_names=['reconstructed'])
    logger.info("Exported face_reconstructor.onnx (GAN mock)")

def validate_bundle():
    """Validate all ONNX + weights load correctly."""
    sessions = {}
    for onnx_file in BUNDLE_DIR.glob("*.onnx"):
        sess = ort.InferenceSession(str(onnx_file))
        dummy = sess.get_inputs()[0].shape
        dummy[0] = 1  # batch=1
        dummy = np.random.randn(*dummy).astype(np.float32)
        outputs = sess.run(None, {'input': dummy})[0]
        assert outputs.shape[1] == 1, f"Invalid output shape: {onnx_file}"
        logger.info(f"Validated {onnx_file.name}")
    logger.info("✅ ONNX Bundle Validation PASS")

if __name__ == "__main__":
    download_insightface_buffalo_l()
    download_speechbrain_voxceleb()
    export_spoof_detector_onnx()
    export_behavioral_lstm_onnx()
    export_deepfake_detector_onnx()
    export_face_reconstructor_onnx()
    validate_bundle()
    print(f"Bundle ready: {BUNDLE_DIR}")
    print("Next: docker cp backend/models/onnx_bundle container:/models/")

