"""
Hallucination Detector - AI Reliability Feature
Detects spurious face matches using multiple signals.
"""
import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
from scipy.spatial.distance import cosine, euclidean
from sklearn.covariance import EmpiricalCovariance

logger = logging.getLogger(__name__)


@dataclass
class HallucinationRisk:
    """Hallucination risk assessment result."""
    risk_score: float  # 0-1, higher means more likely hallucination
    factors: Dict[str, float]  # Individual factor contributions
    flagged: bool  # True if risk exceeds threshold
    recommendation: str  # "proceed", "review", "challenge"


class HallucinationDetector:
    """
    Multi-modal hallucination detection for face recognition.
    
    Detects potential false positive matches by analyzing:
    1. Confidence interval validation - Is the match confidence statistically significant?
    2. Embedding quality scoring - Is the embedding well-formed and distinctive?
    3. Contextual consistency - Does the match align with known metadata (age/gender)?
    4. Cross-modality agreement - Do other modalities (voice/gait) support this match?
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.65,
        embedding_norm_threshold: float = 0.3,
        cross_modality_weight: float = 0.3,
        context_weight: float = 0.2,
        quality_weight: float = 0.2,
        confidence_interval_weight: float = 0.3
    ):
        self.confidence_threshold = confidence_threshold
        self.embedding_norm_threshold = embedding_norm_threshold
        self.weights = {
            'cross_modality': cross_modality_weight,
            'context': context_weight,
            'quality': quality_weight,
            'confidence_interval': confidence_interval_weight
        }
        
        # Store enrollment statistics for population-level analysis
        self.enrollment_statistics = {}  # person_id -> {"embedding_norms": [], "age": int, "gender": str}
        self.covariance_estimator = None
        
    def detect_hallucination(
        self,
        face_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> HallucinationRisk:
        """
        Main detection method. Returns risk score [0,1] and factors.
        
        Args:
            face_result: Dict containing face detection results with matches
            context: Optional dict with enrollment metadata (age, gender, voice_embedding, gait_embedding)
        
        Returns:
            HallucinationRisk object with detailed assessment
        """
        factors = {}
        context = context or {}
        
        # Extract primary match info
        if not face_result or not face_result.get('matches'):
            return HallucinationRisk(
                risk_score=1.0,
                factors={'no_match': 1.0},
                flagged=True,
                recommendation="challenge"
            )
        
        best_match = face_result['matches'][0]
        confidence = best_match.get('score', 0.0)
        embedding = face_result.get('embedding')
        
        # Factor 1: Confidence interval validation
        confidence_risk = self._check_confidence_interval(confidence, embedding)
        factors['confidence_interval'] = confidence_risk
        
        # Factor 2: Embedding quality scoring
        quality_risk = self._assess_embedding_quality(embedding)
        factors['embedding_quality'] = quality_risk
        
        # Factor 3: Contextual consistency
        contextual_risk = self._check_contextual_consistency(best_match, context)
        factors['contextual_consistency'] = contextual_risk
        
        # Factor 4: Cross-modality agreement
        cross_modality_risk = self._check_cross_modality_agreement(face_result, context)
        factors['cross_modality_agreement'] = cross_modality_risk
        
        # Compute weighted risk score
        risk_score = sum(
            factors[k] * self.weights[k.replace('_risk', '')]
            for k in factors.keys()
        )
        
        # Clamp to [0,1]
        risk_score = np.clip(risk_score, 0.0, 1.0)
        
        # Determine flag and recommendation
        flagged = risk_score > self.confidence_threshold
        if risk_score > 0.7:
            recommendation = "challenge"
        elif risk_score > 0.4:
            recommendation = "review"
        else:
            recommendation = "proceed"
        
        logger.info(
            f"Hallucination check: risk={risk_score:.3f}, flagged={flagged}, "
            f"factors={factors}"
        )
        
        return HallucinationRisk(
            risk_score=float(risk_score),
            factors=factors,
            flagged=flagged,
            recommendation=recommendation
        )
    
    def _check_confidence_interval(
        self,
        confidence: float,
        embedding: Optional[np.ndarray] = None
    ) -> float:
        """
        Check if confidence is statistically significant.
        Uses empirical rule: if confidence is close to 0.5 (random), it's suspicious.
        Also considers embedding norm for confidence calibration.
        """
        # Simple but effective: confidence too close to decision boundary is risky
        if confidence < 0.6:
            # Low confidence matches are more likely to be hallucinations
            return 1.0 - confidence
        
        # Very high confidence is generally safe
        if confidence > 0.85:
            return 0.0
        
        # Mid-range confidence (0.6-0.85): check embedding norm for additional signal
        if embedding is not None:
            norm = np.linalg.norm(embedding)
            # Well-trained embeddings typically have norms in a specific range
            # Very small norms may indicate poorly formed embedding (possible hallucination)
            if norm < 0.1:
                return 0.8
            elif norm > 2.0:
                return 0.6  # Unusually large norm may indicate overfit embedding
        
        return 0.3  # Mid-range risk for normal mid-confidence
    
    def _assess_embedding_quality(self, embedding: Optional[np.ndarray]) -> float:
        """
        Assess quality of embedding vector itself.
        Hallucinations often have:
        - Near-zero vectors (failed extraction)
        - Near-identical vectors across different inputs (mode collapse)
        - Extreme values (numerical instability)
        """
        if embedding is None:
            return 1.0  # No embedding = high risk
        
        # Convert to numpy if needed
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)
        
        # Check 1: Norm magnitude
        norm = np.linalg.norm(embedding)
        if norm < 0.01:
            return 1.0  # Almost zero vector
        if norm > 10.0:
            return 0.9  # Extremely large values
        
        # Check 2: Distribution (z-score)
        mean = np.mean(embedding)
        std = np.std(embedding)
        if std < 0.01:
            return 0.8  # Nearly constant - potential mode collapse
        
        # Check 3: Presence of NaNs or infinities
        if np.any(np.isnan(embedding)) or np.any(np.isinf(embedding)):
            return 1.0
        
        # Check 4: Check for abnormal skew/kurtosis
        from scipy.stats import skew, kurtosis
        try:
            sk = abs(sk(embedding))
            kt = abs(kurtosis(embedding))
            if sk > 3.0 or kt > 10.0:
                return 0.7  # Highly non-normal distribution
        except Exception:
            pass
        
        return 0.1  # Generally good quality
    
    def _check_contextual_consistency(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """
        Check if match is consistent with contextual metadata.
        For example, if enrollment age is 30 but claimed age from camera is 80,
        this is suspicious.
        """
        if not context:
            return 0.3  # Cannot assess without context
        
        risk = 0.0
        factors = 0
        
        # Age consistency
        enrolled_age = context.get('enrolled_age')
        detected_age = context.get('detected_age')
        if enrolled_age is not None and detected_age is not None:
            age_diff = abs(enrolled_age - detected_age)
            if age_diff > 30:
                risk += 0.8
            elif age_diff > 15:
                risk += 0.4
            factors += 1
        
        # Gender consistency
        enrolled_gender = context.get('enrolled_gender')
        detected_gender = context.get('detected_gender')
        if enrolled_gender is not None and detected_gender is not None:
            if enrolled_gender != detected_gender:
                risk += 0.9  # Major inconsistency
            factors += 1
        
        # Return average risk from factors, or base risk if no factors
        return risk / max(factors, 1) if factors > 0 else 0.3
    
    def _check_cross_modality_agreement(
        self,
        face_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """
        Check if other modalities agree with face match.
        If face says person A but voice says person B, that's a hallucination signal.
        """
        voice_result = context.get('voice_result')
        gait_result = context.get('gait_result')
        
        if not voice_result and not gait_result:
            return 0.3  # No cross-modality info
        
        best_match_id = face_result['matches'][0]['person_id'] if face_result.get('matches') else None
        if not best_match_id:
            return 0.9  # No match but cross-modality might say something else
        
        disagreements = 0
        total_modalities = 0
        
        # Check voice
        if voice_result and voice_result.get('matches'):
            total_modalities += 1
            voice_match_id = voice_result['matches'][0]['person_id']
            if voice_match_id != best_match_id:
                disagreements += 1
        
        # Check gait
        if gait_result and gait_result.get('matches'):
            total_modalities += 1
            gait_match_id = gait_result['matches'][0]['person_id']
            if gait_match_id != best_match_id:
                disagreements += 1
        
        if total_modalities == 0:
            return 0.3
        
        # More disagreements = higher hallucination risk
        disagreement_ratio = disagreements / total_modalities
        return float(disagreement_ratio)
    
    def update_enrollment_statistics(
        self,
        person_id: str,
        embedding: np.ndarray,
        age: Optional[int] = None,
        gender: Optional[str] = None
    ) -> None:
        """Update stored enrollment statistics for future reference."""
        if person_id not in self.enrollment_statistics:
            self.enrollment_statistics[person_id] = {
                'embedding_norms': [],
                'age': age,
                'gender': gender
            }
        
        norm = float(np.linalg.norm(embedding))
        self.enrollment_statistics[person_id]['embedding_norms'].append(norm)
        
        # Keep only recent N samples
        if len(self.enrollment_statistics[person_id]['embedding_norms']) > 100:
            self.enrollment_statistics[person_id]['embedding_norms'] = \
                self.enrollment_statistics[person_id]['embedding_norms'][-100:]
    
    def fit_covariance(self, embeddings: np.ndarray) -> None:
        """
        Fit multivariate Gaussian to enrollment embeddings.
        Used for Mahalanobis distance-based anomaly detection.
        """
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        self.covariance_estimator = EmpiricalCovariance()
        self.covariance_estimator.fit(embeddings)
        logger.info("Fitted covariance estimator for hallucination detection")
    
    def compute_mahalanobis_distance(self, embedding: np.ndarray) -> float:
        """
        Compute Mahalanobis distance from enrollment distribution.
        Extremely large distances indicate possible hallucination.
        """
        if self.covariance_estimator is None:
            return 0.0
        
        embedding = embedding.reshape(1, -1)
        distance = self.covariance_estimator.mahalanobis(embedding)
        return float(distance)


# Global singleton
hallucination_detector = HallucinationDetector()
