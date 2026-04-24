"""
Enhanced Anti-Deepfake & Synthetic Identity Defense.

Advanced defense against deepfakes, synthetic identities, and presentation attacks.
Implements multimodal detection and temporal consistency analysis.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
import json
import base64
import hashlib
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


class DeepfakeThreatIntelligence:
    """Deepfake threat intelligence feed."""
    
    def __init__(self):
        self.known_attacks = []
        self.threat_patterns = self._load_threat_patterns()
        self.last_update = datetime.now(timezone.utc)
    
    def _load_threat_patterns(self) -> Dict[str, Any]:
        """Load known threat patterns."""
        return {
            "face_swap": {
                "indicators": [
                    "inconsistent_lighting",
                    "edge_blending_artifacts",
                    "temporal_flickering"
                ],
                "severity": "high"
            },
            "lip_sync_attack": {
                "indicators": [
                    "audio_visual_desync",
                    "unnatural_mouth_movement"
                ],
                "severity": "high"
            },
            "voice_clone": {
                "indicators": [
                    "spectral_artifacts",
                    "phase_inconsistency",
                    "unnatural_tremor"
                ],
                "severity": "medium"
            },
            "gan_generated": {
                "indicators": [
                    "high_frequency_artifacts",
                    "texture_inconsistency"
                ],
                "severity": "high"
            },
            "3d_mask": {
                "indicators": [
                    "depth_inconsistency",
                    "reflection_anomaly"
                ],
                "severity": "medium"
            }
        }
    
    def update_threat_feed(self, feed_data: List[Dict]) -> None:
        """Update threat intelligence from external feed."""
        self.known_attacks.extend(feed_data)
        self.last_update = datetime.now(timezone.utc)
    
    def check_match(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check if analysis matches known threat patterns.
        
        Args:
            analysis: Deepfake analysis results
        
        Returns:
            List of matching threat patterns
        """
        matches = []
        artifacts = analysis.get("analysis", {})
        
        face_artifacts = artifacts.get("face", {}).get("artifacts", [])
        voice_artifacts = artifacts.get("voice", {}).get("artifacts", [])
        temporal_issues = artifacts.get("temporal", {}).get("inconsistencies", [])
        
        all_indicators = face_artifacts + voice_artifacts + temporal_issues
        
        for threat_type, pattern in self.threat_patterns.items():
            pattern_indicators = pattern.get("indicators", [])
            matched_indicators = [i for i in all_indicators if i in pattern_indicators]
            
            if matched_indicators:
                confidence = len(matched_indicators) / len(pattern_indicators)
                matches.append({
                    "threat_type": threat_type,
                    "severity": pattern["severity"],
                    "matched_indicators": matched_indicators,
                    "confidence": confidence
                })
        
        return matches
    
    def get_recent_threats(self, hours: int = 24) -> List[Dict]:
        """Get recent threat intelligence."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent = [
            threat for threat in self.known_attacks
            if datetime.fromisoformat(threat.get("timestamp", "1970-01-01")) > cutoff
        ]
        return recent


class WatermarkDetector:
    """
    Detect AI-generated content watermarks.
    
    Checks for invisible watermarks embedded by AI generation tools
    like OpenAI, Midjourney, Stable Diffusion, etc.
    """
    
    def __init__(self):
        self.known_watermarks = self._load_watermark_patterns()
    
    def _load_watermark_patterns(self) -> Dict[str, Any]:
        """Load known watermark patterns."""
        return {
            "openai_dalle": {
                "frequency_domain": {
                    "pattern": "high_freq_grid",
                    "locations": [(40, 40), (40, -40), (-40, 40), (-40, -40)],
                    "tolerance": 5
                },
                "confidence_threshold": 0.8
            },
            "midjourney": {
                "metadata": {
                    "signatures": ["midjourney", "mj_"],
                    "exif_tags": ["Software: Adobe Photoshop"]
                },
                "confidence_threshold": 0.7
            },
            "stable_diffusion": {
                "metadata": {
                    "keywords": ["stable diffusion", "a1111", "webui"],
                    "comment_field": True
                },
                "confidence_threshold": 0.75
            },
            "generic_ai": {
                "texture_analysis": {
                    "unnatural_uniformity": 0.8,
                    "frequency_clustering": True
                },
                "confidence_threshold": 0.6
            }
        }
    
    def detect(self, media_data: np.ndarray) -> Dict[str, Any]:
        """
        Detect watermarks in media data.
        
        Args:
            media_data: Image or video frame (numpy array)
        
        Returns:
            Watermark detection results
        """
        results = {
            "has_watermark": False,
            "watermark_type": None,
            "confidence": 0.0,
            "details": []
        }
        
        # Check frequency domain
        freq_results = self._check_frequency_domain(media_data)
        if freq_results["detected"]:
            results["has_watermark"] = True
            results["details"].append(freq_results)
        
        # Check for metadata (if applicable)
        # Note: In production, would extract EXIF metadata
        
        # Texture analysis
        texture_results = self._analyze_texture(media_data)
        if texture_results["detected"]:
            results["has_watermark"] = True
            results["details"].append(texture_results)
        
        # Determine watermark type and confidence
        if results["has_watermark"]:
            results["watermark_type"] = self._identify_watermark_type(results["details"])
            results["confidence"] = max(d["confidence"] for d in results["details"])
        
        return results
    
    def _check_frequency_domain(self, image: np.ndarray) -> Dict[str, Any]:
        """Check frequency domain for watermark patterns."""
        result = {
            "method": "frequency_domain",
            "detected": False,
            "confidence": 0.0,
            "patterns": []
        }
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # FFT
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude = np.log(np.abs(f_shift) + 1)
            
            # Check for grid patterns (common in AI-generated images)
            h, w = magnitude.shape
            center_h, center_w = h // 2, w // 2
            
            # Check outer corners for high-frequency grid patterns
            corner_size = 10
            corners = [
                magnitude[:corner_size, :corner_size],
                magnitude[:corner_size, -corner_size:],
                magnitude[-corner_size:, :corner_size],
                magnitude[-corner_size:, -corner_size:]
            ]
            
            corner_energies = [np.mean(corner) for corner in corners]
            center_energy = np.mean(magnitude[center_h-20:center_h+20, center_w-20:center_w+20])
            
            if center_energy > 0:
                energy_ratio = np.mean(corner_energies) / center_energy
                
                # AI-generated images often have unusual high-frequency energy
                if energy_ratio > 1.5:
                    result["detected"] = True
                    result["confidence"] = min(energy_ratio / 3.0, 1.0)
                    result["patterns"].append("high_frequency_grid")
        
        except Exception:
            pass
        
        return result
    
    def _analyze_texture(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze image texture for AI generation artifacts."""
        result = {
            "method": "texture_analysis",
            "detected": False,
            "confidence": 0.0,
            "artifacts": []
        }
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Calculate local variance (texture uniformity)
            kernel_size = 15
            local_var = cv2.blur(gray, (kernel_size, kernel_size))
            local_var = cv2.subtract(gray, local_var)
            local_var = cv2.multiply(local_var, local_var)
            local_var = cv2.blur(local_var, (kernel_size, kernel_size))
            
            var_score = np.mean(local_var) / 255.0
            
            # AI-generated images often have unnaturally uniform textures
            if var_score < 0.01:  # Very low variance
                result["detected"] = True
                result["confidence"] = 0.7
                result["artifacts"].append("unnatural_uniformity")
            elif var_score < 0.02:
                result["detected"] = True
                result["confidence"] = 0.5
                result["artifacts"].append("slight_uniformity")
        
        except Exception:
            pass
        
        return result
    
    def _identify_watermark_type(self, details: List[Dict]) -> str:
        """Identify specific watermark type from detection details."""
        patterns_found = []
        for detail in details:
            if "patterns" in detail:
                patterns_found.extend(detail["patterns"])
        
        # Match against known watermark signatures
        if "high_frequency_grid" in patterns_found:
            return "openai_dalle"
        elif "unnatural_uniformity" in patterns_found:
            return "stable_diffusion"
        else:
            return "generic_ai"


class SyntheticRiskModel:
    """
    Assess risk of synthetic/AI-generated identity.
    
    Evaluates multiple signals to determine if an identity
    appears to be AI-generated or synthetic.
    """
    
    def __init__(self):
        self.risk_weights = {
            "face_generation_score": 0.3,
            "voice_generation_score": 0.2,
            "temporal_consistency_score": 0.2,
            "metadata_anomaly_score": 0.15,
            "behavioral_anomaly_score": 0.15
        }
    
    def assess(self, person_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess synthetic identity risk.
        
        Args:
            person_data: Person information including biometric data
        
        Returns:
            Synthetic identity risk assessment
        """
        risk_scores = {}
        
        # Face generation score
        face_data = person_data.get("face", {})
        risk_scores["face_generation_score"] = self._assess_face_generation(face_data)
        
        # Voice generation score
        voice_data = person_data.get("voice", {})
        risk_scores["voice_generation_score"] = self._assess_voice_generation(voice_data)
        
        # Temporal consistency score
        temporal_data = person_data.get("temporal", {})
        risk_scores["temporal_consistency_score"] = self._assess_temporal_consistency(temporal_data)
        
        # Metadata anomaly score
        metadata = person_data.get("metadata", {})
        risk_scores["metadata_anomaly_score"] = self._assess_metadata_anomaly(metadata)
        
        # Behavioral anomaly score
        behavior_data = person_data.get("behavior", {})
        risk_scores["behavioral_anomaly_score"] = self._assess_behavioral_anomaly(behavior_data)
        
        # Calculate weighted risk score
        total_risk = sum(
            risk_scores[key] * self.risk_weights[key]
            for key in self.risk_weights
        )
        
        # Determine risk level
        if total_risk > 0.8:
            risk_level = "critical"
        elif total_risk > 0.6:
            risk_level = "high"
        elif total_risk > 0.4:
            risk_level = "medium"
        elif total_risk > 0.2:
            risk_level = "low"
        else:
            risk_level = "minimal"
        
        return {
            "overall_risk_score": round(total_risk, 4),
            "risk_level": risk_level,
            "component_scores": risk_scores,
            "risk_factors": self._identify_risk_factors(risk_scores),
            "recommendation": self._get_recommendation(total_risk),
            "assessment_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _assess_face_generation(self, face_data: Dict[str, Any]) -> float:
        """Assess face generation probability."""
        score = 0.0
        
        # Check for GAN artifacts
        if "gan_artifact_score" in face_data:
            score += face_data["gan_artifact_score"] * 0.5
        
        # Check geometric consistency
        if "geometry_score" in face_data:
            geometry_score = face_data["geometry_score"]
            if geometry_score < 0.6:
                score += (1.0 - geometry_score) * 0.3
        
        # Check temporal consistency
        if "temporal_consistency_score" in face_data:
            temporal_score = face_data["temporal_consistency_score"]
            score += (1.0 - temporal_score) * 0.2
        
        return min(score, 1.0)
    
    def _assess_voice_generation(self, voice_data: Dict[str, Any]) -> float:
        """Assess voice generation probability."""
        score = 0.0
        
        # Check spectral artifacts
        spectral = voice_data.get("spectral_analysis", {})
        if "spectral_irregularities" in spectral:
            score += spectral["spectral_irregularities"] * 0.4
        
        # Check phase coherence
        if "phase_coherence" in spectral:
            coherence = spectral["phase_coherence"]
            score += (1.0 - coherence) * 0.3
        
        # Check micro-tremor
        if "microtremor_analysis" in voice_data:
            tremor = voice_data["microtremor_analysis"]
            if tremor.get("unnatural_pattern", False):
                score += 0.3
        
        return min(score, 1.0)
    
    def _assess_temporal_consistency(self, temporal_data: Dict[str, Any]) -> float:
        """Assess temporal consistency."""
        if not temporal_data:
            return 0.0
        
        consistency_score = temporal_data.get("consistency_score", 1.0)
        return 1.0 - consistency_score
    
    def _assess_metadata_anomaly(self, metadata: Dict[str, Any]) -> float:
        """Assess metadata anomalies."""
        score = 0.0
        
        # Check for missing or inconsistent metadata
        expected_fields = ["capture_device", "timestamp", "location"]
        missing_fields = sum(1 for f in expected_fields if f not in metadata)
        
        if missing_fields > 0:
            score += missing_fields * 0.2
        
        # Check timestamp anomalies
        if "timestamp" in metadata:
            try:
                ts = datetime.fromisoformat(metadata["timestamp"])
                now = datetime.now(ts.tzinfo or timezone.utc)
                age = abs((now - ts).total_seconds())
                
                # Future dates or very old dates are suspicious
                if age > 365 * 24 * 3600 or age < 0:
                    score += 0.3
            except:
                score += 0.2
        
        return min(score, 1.0)
    
    def _assess_behavioral_anomaly(self, behavior_data: Dict[str, Any]) -> float:
        """Assess behavioral anomalies."""
        score = 0.0
        
        # Check for unnatural patterns
        if "movement_pattern" in behavior_data:
            pattern = behavior_data["movement_pattern"]
            if pattern.get("unnatural", False):
                score += 0.4
        
        # Check for inconsistency over time
        if "consistency_score" in behavior_data:
            consistency = behavior_data["consistency_score"]
            score += (1.0 - consistency) * 0.3
        
        return min(score, 1.0)
    
    def _identify_risk_factors(self, risk_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """Identify specific risk factors."""
        factors = []
        
        for key, score in risk_scores.items():
            if score > 0.5:
                factor_name = key.replace("_score", "").replace("_", " ").title()
                factors.append({
                    "factor": factor_name,
                    "severity": "high" if score > 0.7 else "medium",
                    "score": score
                })
        
        return factors
    
    def _get_recommendation(self, risk_score: float) -> str:
        """Get recommendation based on risk score."""
        if risk_score > 0.8:
            return "Reject and flag for manual review"
        elif risk_score > 0.6:
            return "Require additional verification steps"
        elif risk_score > 0.4:
            return "Proceed with caution and enhanced monitoring"
        else:
            return "Accept with standard procedures"


# Convenience functions

def detect_deepfake(
    face_data: Dict[str, Any],
    voice_data: Optional[Dict[str, Any]] = None,
    video_frames: Optional[List[np.ndarray]] = None
) -> Dict[str, Any]:
    """
    Detect deepfake in multimodal data.
    
    Args:
        face_data: Face recognition results
        voice_data: Voice recognition results
        video_frames: Video frames for analysis
    
    Returns:
        Deepfake detection results
    """
    detector = DeepfakeDetector()
    return detector.analyze_multimodal(face_data, voice_data, video_frames)


def check_synthetic_identity(
    person_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Check if identity appears synthetic.
    
    Args:
        person_data: Person information
    
    Returns:
        Synthetic identity risk assessment
    """
    detector = DeepfakeDetector()
    return detector.check_synthetic_identity(person_data)


def check_watermark(
    media_data: np.ndarray
) -> Dict[str, Any]:
    """
    Check media for AI generation watermarks.
    
    Args:
        media_data: Image or video frame
    
    Returns:
        Watermark detection results
    """
    detector = DeepfakeDetector()
    return detector.check_watermarked_content(media_data)


class TemporalAnalyzer:
    """Temporal analysis for spoof detection."""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.frame_history = []



class DeepfakeDetector:
    """Advanced deepfake and synthetic identity detection."""
    
    def __init__(self):
        self.detection_history = []
        self.threat_intelligence = DeepfakeThreatIntelligence()
        self.watermark_detector = WatermarkDetector()
        self.synthetic_risk_model = SyntheticRiskModel()
    
    def analyze_multimodal(
        self,
        face_data: Dict[str, Any],
        voice_data: Optional[Dict[str, Any]] = None,
        video_frames: Optional[List[np.ndarray]] = None
    ) -> Dict[str, Any]:
        """
        Perform multimodal deepfake detection.
        
        Analyzes face, voice, and video for consistency and artifacts.
        
        Args:
            face_data: Face detection results
            voice_data: Voice analysis results
            video_frames: Video frames for temporal analysis
        
        Returns:
            Deepfake analysis results
        """
        results = {
            "is_deepfake": False,
            "confidence": 0.0,
            "risk_score": 0.0,
            "analysis": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Face analysis
        face_analysis = self._analyze_face_deepfake(face_data)
        results["analysis"]["face"] = face_analysis
        
        # Voice analysis
        if voice_data:
            voice_analysis = self._analyze_voice_deepfake(voice_data)
            results["analysis"]["voice"] = voice_analysis
        
        # Temporal consistency
        if video_frames and len(video_frames) > 1:
            temporal_analysis = self._analyze_temporal_consistency(video_frames)
            results["analysis"]["temporal"] = temporal_analysis
        
        # Lip-sync verification
        if face_data and voice_data:
            lip_sync_score = self._verify_lip_sync(face_data, voice_data)
            results["analysis"]["lip_sync"] = {
                "score": lip_sync_score,
                "synchronized": lip_sync_score > 0.7
            }
        
        # Calculate overall risk
        risk_scores = [a.get("risk_score", 0.0) for a in results["analysis"].values()]
        results["risk_score"] = max(risk_scores) if risk_scores else 0.0
        results["confidence"] = 1.0 - results["risk_score"]
        results["is_deepfake"] = results["risk_score"] > 0.7
        
        return results
    
    def _analyze_face_deepfake(self, face_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze face for deepfake artifacts."""
        analysis = {
            "risk_score": 0.0,
            "artifacts": [],
            "gan_indicators": [],
            "geometry_score": 1.0
        }
        
        # Check for GAN artifacts
        if "face_box" in face_data:
            geometry_score = self._check_3d_geometry(face_data)
            analysis["geometry_score"] = geometry_score
            
            if geometry_score < 0.6:
                analysis["artifacts"].append("inconsistent_3d_geometry")
                analysis["risk_score"] += 0.3
        
        # Check temporal consistency (if multiple frames)
        if "temporal_analysis" in face_data:
            temporal_score = face_data["temporal_analysis"].get("consistency_score", 1.0)
            if temporal_score < 0.7:
                analysis["artifacts"].append("temporal_inconsistency")
                analysis["risk_score"] += 0.2
        
        # Check for blending artifacts
        if "blending_score" in face_data:
            blending = face_data["blending_score"]
            if blending < 0.5:
                analysis["artifacts"].append("edge_blending_artifact")
                analysis["risk_score"] += 0.2
        
        # GAN-specific detection
        gan_score = self._detect_gan_artifacts(face_data)
        if gan_score > 0.5:
            analysis["gan_indicators"].append({
                "type": "gan_artifact",
                "confidence": gan_score
            })
            analysis["risk_score"] += 0.3
        
        analysis["risk_score"] = min(analysis["risk_score"], 1.0)
        
        return analysis
    
    def _analyze_voice_deepfake(self, voice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze voice for deepfake indicators."""
        analysis = {
            "risk_score": 0.0,
            "artifacts": [],
            "synthetic_confidence": 0.0
        }
        
        # Check for synthetic voice indicators
        spectral_analysis = voice_data.get("spectral_analysis", {})
        
        # Spectral artifacts
        if "spectral_irregularities" in spectral_analysis:
            irregularities = spectral_analysis["spectral_irregularities"]
            if irregularities > 0.5:
                analysis["artifacts"].append("spectral_artifact")
                analysis["risk_score"] += 0.3
        
        # Phase inconsistency
        if "phase_coherence" in spectral_analysis:
            coherence = spectral_analysis["phase_coherence"]
            if coherence < 0.6:
                analysis["artifacts"].append("phase_inconsistency")
                analysis["risk_score"] += 0.25
        
        # Micro-tremor analysis
        if "microtremor_analysis" in voice_data:
            tremor = voice_data["microtremor_analysis"]
            if tremor.get("unnatural_pattern", False):
                analysis["artifacts"].append("unnatural_tremor")
                analysis["risk_score"] += 0.2
        
        analysis["synthetic_confidence"] = analysis["risk_score"]
        analysis["risk_score"] = min(analysis["risk_score"], 1.0)
        
        return analysis
    
    def _analyze_temporal_consistency(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """Analyze temporal consistency across video frames."""
        analyzer = TemporalAnalyzer(window_size=len(frames))
        
        inconsistencies = []
        total_consistency = 0.0
        
        for i, frame in enumerate(frames):
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            
            # Detect face in frame
            faces = detector.detect_faces(gray, check_spoof=False)
            
            if faces:
                face = faces[0]
                analyzer.add_frame(frame, face["bbox"], face.get("landmarks", []))
        
        # Check for inconsistencies
        if len(analyzer.frame_history) > 1:
            consistency_issues = self._check_temporal_issues(analyzer.frame_history)
            inconsistencies.extend(consistency_issues)
            total_consistency = 1.0 - (len(consistency_issues) * 0.2)
        
        return {
            "consistency_score": max(0.0, total_consistency),
            "num_frames": len(frames),
            "inconsistencies": inconsistencies,
            "has_artifacts": len(inconsistencies) > 0
        }
    
    def _check_temporal_issues(self, frame_history: List[Dict]) -> List[str]:
        """Check for temporal inconsistencies."""
        issues = []
        
        for i in range(1, len(frame_history)):
            prev = frame_history[i-1]
            curr = frame_history[i]
            
            # Check for unnatural movements
            if self._has_unnatural_movement(prev, curr):
                issues.append("unnatural_movement")
            
            # Check for flickering
            if self._has_flickering(prev, curr):
                issues.append("temporal_flickering")
            
            # Check for inconsistent lighting
            if self._has_lighting_inconsistency(prev, curr):
                issues.append("lighting_inconsistency")
        
        return issues
    
    def _verify_lip_sync(
        self,
        face_data: Dict[str, Any],
        voice_data: Dict[str, Any]
    ) -> float:
        """Verify audio-visual synchronization."""
        # Extract lip movements
        lip_movements = face_data.get("lip_movements", [])
        
        # Extract voice segments
        voice_segments = voice_data.get("segments", [])
        
        if not lip_movements or not voice_segments:
            return 0.5  # Neutral score
        
        # Calculate correlation
        correlation = self._calculate_av_correlation(lip_movements, voice_segments)
        
        return correlation
    
    def _calculate_av_correlation(
        self,
        lip_movements: List[float],
        voice_segments: List[Dict]
    ) -> float:
        """Calculate audio-visual correlation."""
        if len(lip_movements) != len(voice_segments):
            return 0.5
        
        correlations = []
        for lip_val, voice_seg in zip(lip_movements, voice_segments):
            voice_activity = voice_seg.get("intensity", 0.0)
            correlation = 1.0 - abs(lip_val - voice_activity)
            correlations.append(correlation)
        
        return np.mean(correlations) if correlations else 0.5
    
    def _detect_gan_artifacts(self, face_data: Dict[str, Any]) -> float:
        """Detect GAN-specific artifacts."""
        # Frequency domain analysis
        image = face_data.get("aligned_face")
        if image is None:
            return 0.0
        
        # FFT-based detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)
        
        # GANs often have characteristic frequency patterns
        high_freq_energy = np.sum(magnitude[-10:, -10:]) + np.sum(magnitude[:10, :10])
        total_energy = np.sum(magnitude)
        
        if total_energy > 0:
            high_freq_ratio = high_freq_energy / total_energy
            # Unusual high-frequency patterns may indicate GAN
            if high_freq_ratio > 0.1:
                return min(high_freq_ratio * 5, 1.0)
        
        return 0.0
    
    def _check_3d_geometry(self, face_data: Dict[str, Any]) -> float:
        """Check 3D geometric consistency."""
        # Analyze facial landmarks for geometric plausibility
        landmarks = face_data.get("landmarks", {})
        
        if not landmarks:
            return 0.5
        
        # Check triangle inequalities for facial features
        geometry_score = 1.0
        
        # Eye distance should be reasonable
        if "left_eye" in landmarks and "right_eye" in landmarks:
            left_eye = np.array(landmarks["left_eye"])
            right_eye = np.array(landmarks["right_eye"])
            eye_dist = np.linalg.norm(right_eye - left_eye)
            
            if eye_dist < 5 or eye_dist > 200:
                geometry_score *= 0.7
        
        # Nose position relative to eyes
        if "nose" in landmarks and "left_eye" in landmarks:
            nose = np.array(landmarks["nose"])
            left_eye = np.array(landmarks["left_eye"])
            nose_eye_dist = np.linalg.norm(nose - left_eye)
            
            if nose_eye_dist < 5 or nose_eye_dist > 100:
                geometry_score *= 0.8
        
        return geometry_score
    
    def check_synthetic_identity(
        self,
        person_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if identity appears synthetic/AI-generated.
        
        Args:
            person_data: Person information including biometric data
        
        Returns:
            Synthetic identity risk assessment
        """
        return self.synthetic_risk_model.assess(person_data)
    
    def check_watermarked_content(self, media_data: np.ndarray) -> Dict[str, Any]:
        """
        Detect AI-generated content watermarks.
        
        Args:
            media_data: Image or video frame
        
        Returns:
            Watermark detection results
        """
        return self.watermark_detector.detect(media_data)


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