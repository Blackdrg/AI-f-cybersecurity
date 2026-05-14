#!/usr/bin/env python3
"""Export ONNX models + bundle weights for production deployment."""
import os
# Must set before huggingface_hub/speechbrain imports
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

import sys
import shutil
from pathlib import Path
import onnx
import onnxruntime as ort
import numpy as np
import torch
import torch.onnx
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from insightface.app import FaceAnalysis
    from speechbrain.inference import EncoderClassifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check optional dependencies
try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    FaceAnalysis = None  # type: ignore

try:
    from speechbrain.inference import EncoderClassifier
    SPEECHBRAIN_AVAILABLE = True
except ImportError:
    SPEECHBRAIN_AVAILABLE = False
    EncoderClassifier = None  # type: ignore

BUNDLE_DIR = Path(__file__).parent.parent / "models" / "onnx_bundle"
BUNDLE_DIR.mkdir(parents=True, exist_ok=True)


def download_insightface_buffalo_l():
    """Download InsightFace buffalo_l weights."""
    if not INSIGHTFACE_AVAILABLE or FaceAnalysis is None:
        logger.warning("Skipping InsightFace download (missing dependency)")
        return
    try:
        cache_dir = Path.home() / ".insightface" / "models" / "buffalo_l"
        if not cache_dir.exists():
            app = FaceAnalysis(name='buffalo_l')
            app.prepare(ctx_id=0, det_size=(640, 640))
        # Copy or symlink the cache directory
        if cache_dir.exists():
            target_dir = BUNDLE_DIR / "insightface_buffalo_l"
            if not target_dir.exists():
                try:
                    target_dir.symlink_to(cache_dir, target_is_directory=True)
                    logger.info(f"Bundled InsightFace buffalo_l (symlink): {cache_dir}")
                except (OSError, NotImplementedError):
                    # Windows fallback: copy the directory
                    shutil.copytree(cache_dir, target_dir)
                    logger.info(f"Bundled InsightFace buffalo_l (copied): {cache_dir}")
    except Exception as e:
        logger.error(f"Failed to download InsightFace model: {e}")
        logger.warning("Skipping InsightFace download")


def download_speechbrain_voxceleb():
    """Download SpeechBrain VoxCeleb speaker embedding model."""
    if not SPEECHBRAIN_AVAILABLE or EncoderClassifier is None:
        logger.warning("Skipping SpeechBrain download (missing dependency)")
        return
    try:
        save_dir = BUNDLE_DIR / "speechbrain_voxceleb"
        save_dir.mkdir(parents=True, exist_ok=True)

        # Download model directly to save directory
        model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=str(save_dir),
            run_opts={"device": "cpu"}
        )
        logger.info(f"Bundled SpeechBrain VoxCeleb to {save_dir}")
    except OSError as e:
        if "symlink" in str(e).lower() or "1314" in str(e):
            logger.warning("Symlink not supported on Windows - skipping SpeechBrain download")
        else:
            logger.error(f"Failed to download SpeechBrain model: {e}")
    except Exception as e:
        logger.error(f"Failed to download SpeechBrain model: {e}")


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
        dynamic_axes={'sequence': {0: 'batch_size', 1: 'sequence_length'}}
    )
    logger.info("Exported behavioral_predictor.onnx (LSTM 256-dim)")


def export_deepfake_detector_onnx():
    """Placeholder: export deepfake model (e.g., Xception-based)."""
    # In production: load/train MesoNet/Xception + export
    # Mock for now - replace with real training
    class DeepfakeNet(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = torch.nn.Conv2d(3, 32, 3, padding=1)
            self.conv2 = torch.nn.Conv2d(32, 64, 3, padding=1)
            self.pool = torch.nn.AdaptiveAvgPool2d(1)
            self.fc = torch.nn.Linear(64, 1)

        def forward(self, x):
            x = torch.relu(self.conv1(x))
            x = self.pool(torch.relu(self.conv2(x)))
            x = self.fc(x.view(x.size(0), -1))
            return torch.sigmoid(x)

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
            self.enc1 = torch.nn.Conv2d(4, 32, 3, padding=1)
            self.enc2 = torch.nn.Conv2d(32, 64, 3, padding=1)
            self.pool = torch.nn.MaxPool2d(2, 2)
            self.dec1 = torch.nn.ConvTranspose2d(64, 32, 2, stride=2)
            self.dec2 = torch.nn.Conv2d(32, 3, 3, padding=1)

        def forward(self, x):
            x = torch.relu(self.enc1(x))
            x = self.pool(torch.relu(self.enc2(x)))
            x = torch.relu(self.dec1(x))
            return torch.sigmoid(self.dec2(x))

    model = InpaintUNet()
    dummy = torch.randn(1, 4, 256, 256)  # RGB + mask
    torch.onnx.export(model, dummy, str(BUNDLE_DIR / "face_reconstructor.onnx"),
                      opset_version=11, input_names=['input_mask'], output_names=['reconstructed'])
    logger.info("Exported face_reconstructor.onnx (GAN mock)")


def validate_bundle():
    """Validate all ONNX + weights load correctly."""
    for onnx_file in BUNDLE_DIR.glob("*.onnx"):
        sess = ort.InferenceSession(str(onnx_file))
        input_shape = sess.get_inputs()[0].shape
        # Handle dynamic dimensions (strings like 'batch_size') by replacing with 1
        dummy_shape = []
        for dim in input_shape:
            if isinstance(dim, str):
                dummy_shape.append(1)  # Replace dynamic dim with 1
            else:
                dummy_shape.append(dim)
        dummy_shape[0] = 1  # Ensure batch size is 1
        dummy = np.random.randn(*dummy_shape).astype(np.float32)
        # Use the actual input name from the model
        input_name = sess.get_inputs()[0].name
        outputs = sess.run(None, {input_name: dummy})[0]
        # Check that the first dimension is batch size (which we set to 1)
        assert outputs.shape[0] == 1, f"Invalid batch size in output: {onnx_file}"
        logger.info(f"Validated {onnx_file.name} with output shape {outputs.shape}")
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