import cv2
import numpy as np
from typing import List


class GaitAnalyzer:
    def __init__(self):
        # For POC, use Hu Moments of gait silhouette as gait signature.
        # In production, use a deep learning model like GaitSet or OpenPose.
        pass

    def extract_gait_features(self, video_frames: List[np.ndarray]) -> np.ndarray:
        """
        Extract gait features from a sequence of video frames using temporal stacking of Hu Moments.
        Returns a 7-dimensional float32 vector representing Hu moments of the gait silhouette.
        Process: For each frame, compute binary silhouette → Hu Moments (7-d).
        Then aggregate across temporal frames by averaging (temporal pooling).
        Finally apply log transform and L2 normalize.
        This approach preserves temporal dynamics better than single GEI.
        """
        if len(video_frames) < 10:
            return np.zeros(7, dtype=np.float32)

        frame_hu_moments = []
        for frame in video_frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Simple binary silhouette extraction via thresholding
            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            binary = (thresh > 0).astype(np.uint8)

            # Compute spatial moments
            moments = cv2.moments(binary, binaryImage=False)
            if moments["m00"] == 0:
                continue  # skip empty frames

            # Compute Hu moments for this frame
            hu = cv2.HuMoments(moments).flatten().astype(np.float32)
            frame_hu_moments.append(hu)

        if not frame_hu_moments:
            return np.zeros(7, dtype=np.float32)

        # Temporal aggregation: average Hu moments across all frames
        hu_avg = np.mean(frame_hu_moments, axis=0)

        # Log transform
        hu_log = -np.sign(hu_avg) * np.log10(np.abs(hu_avg) + 1e-10)

        # L2 normalize
        norm = np.linalg.norm(hu_log)
        if norm > 0:
            hu_log = hu_log / norm

        return hu_log.astype(np.float32)
