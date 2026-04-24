import cv2
import numpy as np
from typing import List


class GaitAnalyzer:
    def __init__(self):
        # For POC, use simple silhouette-based gait features
        # In production, use a pre-trained model like GaitSet or OpenPose + temporal analysis
        pass

    def extract_gait_features(self, video_frames: List[np.ndarray]) -> np.ndarray:
        """
        Extract gait features from a sequence of video frames.
        Returns a 128-dimensional float32 vector representing gait signature.
        Uses Gait Energy Image (GEI) representation: silhouettes are averaged,
        then resized to 16x8 and L2-normalized.
        """
        if len(video_frames) < 10:
            return np.zeros(128, dtype=np.float32)

        silhouettes = []
        for frame in video_frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Simple binary silhouette extraction via thresholding
            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            silhouettes.append(thresh.astype(np.float32) / 255.0)  # normalize 0-1

        # Compute Gait Energy Image (GEI) - mean silhouette
        gei = np.mean(silhouettes, axis=0)  # shape (H, W)

        # Resize to fixed 16x8 (128 values) using area interpolation for downsampling
        gei_resized = cv2.resize(gei, (16, 8), interpolation=cv2.INTER_AREA)

        # Flatten to 1-D vector
        gait_vector = gei_resized.flatten()

        # L2 normalize
        norm = np.linalg.norm(gait_vector)
        if norm > 0:
            gait_vector = gait_vector / norm

        return gait_vector.astype(np.float32)
