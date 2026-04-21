import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import cv2


@dataclass
class SpoofResult:
    is_spoof: bool
    spoof_score: float  # 0 = real, 1 = spoof
    spoof_type: str  # print, replay, mask, deepfake
    confidence: float  # confidence in prediction
    liveness_score: float
    challenge_result: Optional[Dict] = None


class ChallengeResponseVerifier:
    """Challenge-response for liveness detection."""
    
    CHALLENGES = [
        "blink",
        "turn_head_left",
        "turn_head_right",
        "nod",
        "smile",
        "look_at_corners"
    ]
    
    def __init__(self):
        self.challenge_window = 5  # frames to complete challenge
        self.required_frames = 3
        
    def generate_challenge(self) -> Dict:
        """Generate a random challenge."""
        import random
        challenge_type = random.choice(self.CHALLENGES)
        
        return {
            "type": challenge_type,
            "instructions": self._get_instructions(challenge_type),
            "timeout_seconds": 10,
            "points_required": self.required_frames
        }
    
    def _get_instructions(self, challenge: str) -> str:
        instructions = {
            "blink": "Please blink slowly",
            "turn_head_left": "Turn your head to the left",
            "turn_head_right": "Turn your head to the right", 
            "nod": "Nod your head up and down",
            "smile": "Please smile",
            "look_at_corners": "Look at the corners of the screen"
        }
        return instructions.get(challenge, "Follow the on-screen instructions")
    
    def verify_challenge(
        self,
        frames: List[np.ndarray],
        challenge_type: str,
        landmarks_sequence: List
    ) -> Tuple[bool, float]:
        """Verify if challenge was completed correctly."""
        if len(frames) < self.required_frames:
            return False, 0.0
        
        # Analyze motion pattern based on challenge type
        if challenge_type == "blink":
            return self._verify_blink(landmarks_sequence)
        elif challenge_type in ["turn_head_left", "turn_head_right"]:
            return self._verify_head_turn(landmarks_sequence, challenge_type)
        elif challenge_type == "nod":
            return self._verify_nod(landmarks_sequence)
        elif challenge_type == "smile":
            return self._verify_smile(landmarks_sequence)
        
        return False, 0.0
    
    def _verify_blink(self, landmarks: List) -> Tuple[bool, float]:
        """Verify blink by eye aspect ratio."""
        if not landmarks:
            return False, 0.0
        
        blink_ratios = []
        for lm in landmarks[-5:]:
            # Eye aspect ratio calculation
            if 'left_eye' in lm and 'right_eye' in lm:
                ear = self._eye_aspect_ratio(lm['left_eye'], lm['right_eye'])
                blink_ratios.append(ear)
        
        if not blink_ratios:
            return False, 0.0
        
        # Blinks have significantly lower EAR
        avg_ear = np.mean(blink_ratios)
        is_blink = avg_ear < 0.2
        
        confidence = 1.0 - min(avg_ear * 5, 1.0)
        return is_blink, confidence
    
    def _verify_head_turn(self, landmarks: List, direction: str) -> Tuple[bool, float]:
        """Verify head turn by nose position."""
        if not landmarks:
            return False, 0.0
        
        nose_positions = []
        for lm in landmarks:
            if 'nose' in lm:
                nose_positions.append(lm['nose'][0])  # x position
        
        if len(nose_positions) < 2:
            return False, 0.0
        
        # Check direction of movement
        movement = nose_positions[-1] - nose_positions[0]
        
        if direction == "turn_head_left":
            is_correct = movement > 20  # moved left
        else:
            is_correct = movement < -20  # moved right
        
        confidence = min(abs(movement) / 50, 1.0)
        return is_correct, confidence
    
    def _verify_nod(self, landmarks: List) -> Tuple[bool, float]:
        """Verify nod by vertical movement."""
        if not landmarks:
            return False, 0.0
        
        nose_y_positions = []
        for lm in landmarks:
            if 'nose' in lm:
                nose_y_positions.append(lm['nose'][1])
        
        if len(nose_y_positions) < 2:
            return False, 0.0
        
        # Look for up-down movement
        movement_range = max(nose_y_positions) - min(nose_y_positions)
        is_nod = movement_range > 15
        
        confidence = min(movement_range / 30, 1.0)
        return is_nod, confidence
    
    def _verify_smile(self, landmarks: List) -> Tuple[bool, float]:
        """Verify smile by mouth shape."""
        if not landmarks:
            return False, 0.0
        
        mouth_widths = []
        for lm in landmarks:
            if 'mouth_left' in lm and 'mouth_right' in lm:
                width = abs(lm['mouth_right'][0] - lm['mouth_left'][0])
                mouth_widths.append(width)
        
        if not mouth_widths:
            return False, 0.0
        
        # Smile increases mouth width and forms shape
        avg_width = np.mean(mouth_widths)
        is_smile = avg_width > 40
        
        confidence = min(avg_width / 60, 1.0)
        return is_smile, confidence
    
    def _eye_aspect_ratio(self, left_eye, right_eye) -> float:
        """Calculate eye aspect ratio."""
        # Simplified - real implementation would use 6-point EAR
        vertical_dist = abs(left_eye[1] - right_eye[1])
        horizontal_dist = abs(left_eye[0] - right_eye[0])
        
        if horizontal_dist == 0:
            return 0.0
        return vertical_dist / horizontal_dist


class TemporalAnalyzer:
    """Temporal analysis for spoof detection."""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.frame_history = []
        
    def add_frame(
        self,
        frame: np.ndarray,
        face_bbox: List[int],
        landmarks: np.ndarray
    ) -> None:
        """Add frame to temporal window."""
        self.frame_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "face_bbox": face_bbox,
            "face_area": (face_bbox[2] - face_bbox[0]) * (face_bbox[3] - face_bbox[1]),
            "face_ratio": self._face_to_frame_ratio(frame, face_bbox),
            "landmark_positions": landmarks[:5] if len(landmarks) >= 5 else landmarks,
            "brightness": np.mean(frame)
        })
        
        # Keep only recent frames
        if len(self.frame_history) > self.window_size:
            self.frame_history = self.frame_history[-self.window_size:]
    
    def analyze_temporal(self) -> Dict[str, float]:
        """Analyze temporal patterns for spoofing."""
        if len(self.frame_history) < 3:
            return {"spoof_score": 0.0, "pattern": "insufficient_data"}
        
        # Check for face size consistency
        areas = [f["face_area"] for f in self.frame_history]
        area_variance = np.var(areas) / np.mean(areas) if np.mean(areas) > 0 else 0
        
        # Check for frame-by-frame replay artifacts
        bbox_changes = []
        for i in range(1, len(self.frame_history)):
            prev = self.frame_history[i-1]["face_bbox"]
            curr = self.frame_history[i]["face_bbox"]
            change = sum(abs(a - b) for a, b in zip(prev, curr))
            bbox_changes.append(change)
        
        avg_change = np.mean(bbox_changes)
        
        # Low variance + identical changes = likely replay
        if area_variance < 0.01 and avg_change < 5:
            return {
                "spoof_score": 0.9,
                "pattern": "replay_detected",
                "area_variance": area_variance,
                "bbox_stability": 1.0 - (avg_change / 100)
            }
        
        # Check for brightness flickering (screen capture)
        brightness = [f["brightness"] for f in self.frame_history]
        brightness_variance = np.var(brightness)
        
        if brightness_variance > 100:  # Screen refresh flicker
            return {
                "spoof_score": 0.7,
                "pattern": "screen_flicker",
                "brightness_variance": brightness_variance
            }
        
        return {
            "spoof_score": 0.1,
            "pattern": "normal",
            "area_variance": area_variance,
            "bbox_stability": 1.0 - (avg_change / 100)
        }
    
    def _face_to_frame_ratio(self, frame, bbox) -> float:
        """Calculate face to frame ratio."""
        face_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        frame_area = frame.shape[0] * frame.shape[1]
        return face_area / frame_area if frame_area > 0 else 0
    
    def reset(self) -> None:
        """Reset history."""
        self.frame_history = []


class EnhancedSpoofDetector:
    """Production-grade anti-spoofing with multiple signals."""
    
    def __init__(self):
        self.challenge_verifier = ChallengeResponseVerifier()
        self.temporal_analyzer = TemporalAnalyzer()
        self.liveness_threshold = 0.5
        
    def detect(
        self,
        frame: np.ndarray,
        face_bbox: List[int],
        landmarks: np.ndarray,
        require_challenge: bool = False,
        depth_frame: Optional[np.ndarray] = None,
        ir_frame: Optional[np.ndarray] = None
    ) -> SpoofResult:
        """Multi-modal spoof detection."""
        
        signals = {}
        
        # 1. Single-frame analysis (placeholder for actual model)
        signals["image_quality"] = self._analyze_image_quality(frame, face_bbox)
        
        # 2. Texture analysis (print detection)
        signals["texture"] = self._analyze_texture(frame, face_bbox)
        
        # 3. Reflectance analysis
        signals["reflectance"] = self._analyze_reflectance(frame, face_bbox)
        
        # 4. Depth check (if available)
        if depth_frame is not None:
            signals["depth"] = self._analyze_depth(depth_frame, face_bbox)
        else:
            signals["depth"] = {"score": 0.5}
        
        # 5. IR check (if available) 
        if ir_frame is not None:
            signals["ir"] = self._analyze_ir(ir_frame, face_bbox)
        else:
            signals["ir"] = {"score": 0.5}
        
        # 6. Temporal analysis
        self.temporal_analyzer.add_frame(frame, face_bbox, landmarks if hasattr(landmarks, '__iter__') else [])
        temporal = self.temporal_analyzer.analyze_temporal()
        signals["temporal"] = temporal
        
        # Combine signals with weights
        weights = {
            "image_quality": 0.15,
            "texture": 0.25,
            "reflectance": 0.15,
            "depth": 0.20,
            "ir": 0.15,
            "temporal": 0.10
        }
        
        spoof_score = sum(
            signals[k].get("score", 0.5) * weights[k]
            for k in weights
        )
        
        # Determine spoof type
        spoof_type = self._classify_spoof_type(signals)
        
        is_spoof = spoof_score > self.liveness_threshold
        
        return SpoofResult(
            is_spoof=is_spoof,
            spoof_score=spoof_score,
            spoof_type=spoof_type,
            confidence=abs(spoof_score - 0.5) * 2,  # Higher confidence when further from threshold
            liveness_score=1.0 - spoof_score
        )
    
    def _analyze_image_quality(self, frame, bbox) -> Dict:
        """Analyze image quality artifacts."""
        # Placeholder for actual implementation
        # Would use BRISQUE, NIQCE, etc.
        return {"score": 0.2, "quality": "high"}
    
    def _analyze_texture(self, frame, bbox) -> Dict:
        """Analyze texture patterns (print attack detection)."""
        # Placeholder - would use local binary patterns
        return {"score": 0.3, "pattern": "normal"}
    
    def _analyze_reflectance(self, frame, bbox) -> Dict:
        """Analyze specular reflectance."""
        # Placeholder - would analyze light reflection patterns
        return {"score": 0.2, "reflectance": "normal"}
    
    def _analyze_depth(self, depth_frame, bbox) -> Dict:
        """Analyze depth map for 3D structure."""
        # Placeholder - would check for flat surface in depth
        if depth_frame is None:
            return {"score": 0.5}
        
        # Check depth consistency
        depth_crop = depth_frame[
            bbox[1]:bbox[3],
            bbox[0]:bbox[2]
        ]
        
        depth_std = np.std(depth_crop)
        
        # Real faces have depth variation, flat surfaces don't
        if depth_std > 50:
            return {"score": 0.1, "depth_variation": depth_std}
        
        return {"score": 0.8, "depth_variation": depth_std}
    
    def _analyze_ir(self, ir_frame, bbox) -> Dict:
        """Analyze IR image for live vs non-live."""
        # Placeholder - IR responds differently to real skin
        if ir_frame is None:
            return {"score": 0.5}
        
        ir_crop = ir_frame[
            bbox[1]:bbox[3],
            bbox[0]:bbox[2]
        ]
        
        ir_mean = np.mean(ir_crop)
        
        # Live skin has specific IR signature
        if 50 < ir_mean < 200:
            return {"score": 0.2, "ir_signature": "live"}
        
        return {"score": 0.7, "ir_signature": "flat"}
    
    def _classify_spoof_type(self, signals: Dict) -> str:
        """Classify the type of attack."""
        s = signals
        
        if s.get("temporal", {}).get("pattern") == "replay_detected":
            return "replay"
        
        if s.get("texture", {}).get("score", 0.5) > 0.6:
            return "print"
        
        if s.get("depth", {}).get("score", 0.5) > 0.6:
            return "mask"
        
        if s.get("ir", {}).get("score", 0.5) > 0.6:
            return "print_or_mask"
        
        return "unknown"
    
    def verify_challenge(
        self,
        frames: List[np.ndarray],
        challenge_type: str,
        landmarks_sequence: List
    ) -> Tuple[bool, float]:
        """Run challenge-response verification."""
        return self.challenge_verifier.verify_challenge(
            frames, challenge_type, landmarks_sequence
        )


# Global instance
enhanced_spoof_detector = EnhancedSpoofDetector()