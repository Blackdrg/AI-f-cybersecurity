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
        Returns 1-D float32 vector representing gait signature.
        """
        if len(video_frames) < 10:
            # Placeholder for insufficient data
            return np.zeros(128, dtype=np.float32)

        features = []

        for frame in video_frames:
            # Simple silhouette extraction (thresholding)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

            # Extract basic shape features (moments)
            moments = cv2.moments(thresh)
            hu_moments = cv2.HuMoments(moments).flatten()
            features.append(hu_moments)

        # Aggregate over frames (mean and std)
        features = np.array(features)
        mean_features = np.mean(features, axis=0)
        std_features = np.std(features, axis=0)
        gait_vector = np.concatenate([mean_features, std_features])

        # Normalize to fixed size (e.g., 128-d)
        if len(gait_vector) > 128:
            gait_vector = gait_vector[:128]
        elif len(gait_vector) < 128:
            gait_vector = np.pad(
                gait_vector, (0, 128 - len(gait_vector)), 'constant')

        # L2 normalize
        norm = np.linalg.norm(gait_vector)
        if norm > 0:
            gait_vector /= norm

        return gait_vector.astype(np.float32)
