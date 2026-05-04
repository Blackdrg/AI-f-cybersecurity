import cv2
import numpy as np
import torch
import torch.nn as nn
import logging
# from insightface.app import FaceAnalysis

logger = logging.getLogger(__name__)


class SpoofNet(nn.Module):
    """Simple CNN for spoof detection based on texture features."""

    def __init__(self):
        super(SpoofNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(32 * 16 * 16, 128)
        self.fc2 = nn.Linear(128, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = x.view(-1, 32 * 16 * 16)
        x = torch.relu(self.fc1(x))
        x = self.sigmoid(self.fc2(x))
        return x


class SpoofDetector:
    """Production ONNX + PyTorch hybrid spoof/deepfake detector."""

    def __init__(self):
        from . import registry
        self.registry = registry
        self.use_onnx = hasattr(self.registry, 'sessions') and 'spoof_detector' in self.registry.sessions
        self.use_onnx_deepfake = self.use_onnx and 'deepfake_detector' in self.registry.sessions
        logger.info(f"SpoofDetector: ONNX={self.use_onnx}, Deepfake ONNX={self.use_onnx_deepfake}")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        if not self.use_onnx:
            self.model = SpoofNet().to(self.device)
            self.model.eval()

    def detect_spoof(self, image: np.ndarray, face_bbox: list) -> float:
        """
        Detect if face is spoofed (mask, photo, deepfake).
        Returns spoof score (0-1, higher = more likely spoof).
        """
        x1, y1, x2, y2 = face_bbox
        face_roi = image[y1:y2, x1:x2]

        if face_roi.size == 0:
            return 1.0  # Invalid face, assume spoof

        # Use insightface anti-spoof if available
        # if self.use_insightface:
        #     faces = self.app.get(image)
        #     for face in faces:
        #         if 'spoofing' in face:
        #             return face['spoofing']  # Assuming 0-1 score
        #     # Fallback if no spoof score

        # ONNX priority, PyTorch fallback
        face_resized = cv2.resize(face_roi, (64, 64))
        face_tensor = torch.from_numpy(face_resized).permute(2, 0, 1).float().unsqueeze(0) / 255.0
        
        if self.use_onnx:
            # ONNX SpoofNet inference
            spoof_prob = float(self.registry.infer_onnx('spoof_detector', face_tensor.numpy())[0])
        else:
            # PyTorch fallback
            face_tensor = face_tensor.to(self.device)
            with torch.no_grad():
                spoof_prob = self.model(face_tensor).item()

        # Combine with heuristics for robustness
        # Variance of Laplacian (blur detection)
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_score = max(0, 1 - laplacian_var / 500.0)

        # Color entropy
        hist = cv2.calcHist([face_roi], [0, 1, 2], None, [
                            8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        entropy = -np.sum(hist * np.log2(hist + 1e-7))
        color_score = max(0, 1 - entropy / 10.0)

        heuristic_score = (blur_score + color_score) / 2

        # Deepfake check if available
        deepfake_prob = 0.0
        if self.use_onnx_deepfake:
            deepfake_tensor = cv2.resize(face_roi, (224, 224))
            deepfake_tensor = torch.from_numpy(deepfake_tensor).permute(2, 0, 1).float().unsqueeze(0) / 255.0
            deepfake_prob = float(self.registry.infer_onnx('deepfake_detector', deepfake_tensor.numpy())[0])
        
        # Weighted: spoof 40%, deepfake 30%, heuristic 15%, LBP 15%
        lbp_score = self._compute_lbp_score(face_roi)
        combined_score = 0.4 * spoof_prob + 0.3 * deepfake_prob + 0.15 * heuristic_score + 0.15 * lbp_score

        return min(1.0, combined_score)

    def _compute_lbp_image(self, gray: np.ndarray) -> np.ndarray:
        """Compute Local Binary Pattern (LBP) image using 8-neighbor circular LBP."""
        # Ensure grayscale 2D uint8
        if gray.dtype != np.uint8:
            gray = (gray / gray.max() * 255).astype(np.uint8) if gray.max() > 0 else gray.astype(np.uint8)
        h, w = gray.shape
        # Pad to handle borders
        padded = cv2.copyMakeBorder(gray, 1, 1, 1, 1, cv2.BORDER_REFLECT)
        lbp = np.zeros((h, w), dtype=np.uint8)
        # Offsets for 8 neighbors in order: top(-1,0), top-right(-1,1), right(0,1), bottom-right(1,1),
        # bottom(1,0), bottom-left(1,-1), left(0,-1), top-left(-1,-1)
        offsets = [(-1, 0), (-1, 1), (0, 1), (1, 1),
                   (1, 0), (1, -1), (0, -1), (-1, -1)]
        for i, (dy, dx) in enumerate(offsets):
            # Neighbor region corresponding to original size
            neighbor = padded[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            # Set bit if neighbor >= center
            mask = (neighbor >= gray).astype(np.uint8)
            lbp |= (mask << i)
        return lbp

    def _compute_lbp_score(self, face_roi: np.ndarray) -> float:
        """
        Compute a spoof score based on LBP texture features.
        Real faces have higher texture entropy; spoof (printed) have lower entropy.
        Returns a score in [0,1] where higher means more likely spoof.
        """
        try:
            gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        except Exception:
            # Already grayscale?
            gray = face_roi if len(face_roi.shape) == 2 else face_roi[:, :, 0]
        gray = cv2.resize(gray, (64, 64))
        lbp = self._compute_lbp_image(gray)
        # Compute histogram of LBP values (256 bins)
        hist = cv2.calcHist([lbp], [0], None, [256], [0, 256]).flatten()
        hist_norm = hist / (hist.sum() + 1e-7)
        # Compute entropy
        entropy = -np.sum(hist_norm * np.log2(hist_norm + 1e-7))
        max_entropy = np.log2(256)
        # Normalize spoof score: 1 - (entropy / max_entropy)
        lbp_spoof_score = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0.5
        return float(np.clip(lbp_spoof_score, 0.0, 1.0))
