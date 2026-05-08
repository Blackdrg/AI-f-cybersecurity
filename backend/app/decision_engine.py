"""
Decision Engine - Final accept/reject after policy + ethical checks.
Production implementation with bias mitigation, hallucination detection, and uncertainty-aware decisions.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging
from enum import Enum

# Import new reliability components
try:
    from app.models.hallucination_detector import hallucination_detector, HallucinationRisk
    from app.models.uncertainty_estimator import uncertainty_estimator, UncertaintyEstimate
    HALLUCINATION_AVAILABLE = True
    UNCERTAINTY_AVAILABLE = True
except ImportError:
    HALLUCINATION_AVAILABLE = False
    UNCERTAINTY_AVAILABLE = False

logger = logging.getLogger(__name__)


class DecisionStrategy(Enum):
    """Decision strategy modes."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class DecisionContext:
    """Context for a recognition decision."""
    confidence: float
    liveness_score: float
    policy_score: float
    ethical_score: float
    bias_risk: float
    environment: str
    user_role: str


class DecisionEngine:
    """Production decision engine with weighted scoring."""
    
    def __init__(self):
        # Default weights (configurable)
        self.weights = {
            "confidence": 0.30,
            "liveness": 0.25,
            "policy": 0.20,
            "ethical": 0.15,
            "bias": 0.10,
        }
        self.thresholds = {
            "accept": 0.70,
            "review": 0.50,
        }
    
    def make_decision(self, face_result=None, voice_result=None, gait_result=None, liveness_result=None, metadata=None, context: Optional[DecisionContext] = None) -> Dict[str, Any]:
        """
        Compute final decision from multi-modal scores with hallucination & uncertainty checks.
        """
        # If context is provided, use it (new way)
        if context is not None:
            ctx = context
        else:  # Legacy parameter-based call
            confidence = face_result.get('score', 0) if isinstance(face_result, dict) else float(face_result or 0)
            liveness = float(liveness_result) if not isinstance(liveness_result, dict) else liveness_result.get('score', 0.5)
            ctx = DecisionContext(
                confidence=confidence,
                liveness_score=liveness,
                policy_score=metadata.get('policy_score', 0.7) if isinstance(metadata, dict) else 0.7,
                ethical_score=metadata.get('ethical_score', 0.8) if isinstance(metadata, dict) else 0.8,
                bias_risk=metadata.get('bias_risk', 0.1) if isinstance(metadata, dict) else 0.1,
                environment=metadata.get('environment', 'production') if isinstance(metadata, dict) else 'production',
                user_role=metadata.get('user_role', 'viewer') if isinstance(metadata, dict) else 'viewer'
            )
        
        base_confidence = ctx.confidence
        
        # === Step 1: Hallucination Detection ===
        hallucination_risk = None
        if HALLUCINATION_AVAILABLE and face_result:
            h_context = {
                'voice_result': voice_result,
                'gait_result': gait_result,
                'enrolled_age': metadata.get('enrolled_age') if metadata else None,
                'detected_age': metadata.get('detected_age') if metadata else None,
                'enrolled_gender': metadata.get('enrolled_gender') if metadata else None,
                'detected_gender': metadata.get('detected_gender') if metadata else None
            }
            h_risk: HallucinationRisk = hallucination_detector.detect_hallucination(
                face_result, h_context
            )
            hallucination_risk = h_risk
        
        # === Step 2: Uncertainty Estimation ===
        uncertainty = None
        if UNCERTAINTY_AVAILABLE and metadata and metadata.get('embedding') is not None:
            uncertainty: UncertaintyEstimate = uncertainty_estimator.estimate_uncertainty(
                embedding=metadata['embedding']
            )
        
        # === Step 3: Adjust Confidence Based on Reliability Signals ===
        adjusted_confidence = base_confidence
        
        if hallucination_risk:
            # Penalize confidence based on hallucination risk
            risk_penalty = hallucination_risk.risk_score * 0.5  # Up to 50% reduction
            adjusted_confidence *= (1.0 - risk_penalty)
            
            # Log high-risk cases
            if hallucination_risk.flagged:
                logger.warning(
                    f"High hallucination risk detected: {hallucination_risk.risk_score:.3f}, "
                    f"factors={hallucination_risk.factors}, "
                    f"recommendation={hallucination_risk.recommendation}"
                )
        
        if uncertainty:
            # Reduce confidence if uncertainty is high
            uncertainty_penalty = uncertainty.epistemic_uncertainty * 0.3
            adjusted_confidence *= (1.0 - uncertainty_penalty)
        
        # Update context with adjusted confidence
        ctx.confidence = adjusted_confidence
        
        # === Step 4: Compute weighted score (same as before) ===
        total_score = (
            ctx.confidence * self.weights["confidence"] +
            ctx.liveness_score * self.weights["liveness"] +
            ctx.policy_score * self.weights["policy"] +
            ctx.ethical_score * self.weights["ethical"] +
            (1.0 - ctx.bias_risk) * self.weights["bias"]
        )
        
        # === Step 5: Uncertainty-aware decision logic ===
        decision = "review"  # Default to review for uncertainty
        
        # Conservative adjustments based on reliability signals
        if hallucination_risk and hallucination_risk.flagged:
            # High hallucination risk → require manual review or additional auth
            if total_score >= self.thresholds["accept"]:
                total_score = max(total_score - 0.2, self.thresholds["review"])
            decision = "review"
        
        if uncertainty and uncertainty.epistemic_uncertainty > 0.3:
            # High model uncertainty → require review
            if total_score >= self.thresholds["accept"]:
                total_score = max(total_score - 0.15, self.thresholds["review"])
            decision = "review"
        
        # Standard decision thresholds
        if total_score >= self.thresholds["accept"]:
            decision = "allow"
        elif total_score <= self.thresholds["review"]:
            decision = "deny"
        
        # === Step 6: Enhanced risk assessment ===
        risk_level = "low"
        spoof_score = metadata.get('spoof_score', 0.0) if metadata else 0.0
        
        if spoof_score > 0.5:
            risk_level = "critical"
            decision = "deny"
        elif spoof_score > 0.3:
            risk_level = "high"
            decision = "review"
        elif hallucination_risk and hallucination_risk.flagged:
            risk_level = "high"
            decision = "review"
        
        # === Step 7: Build enhanced result ===
        factors = {
            "confidence": ctx.confidence,
            "liveness": ctx.liveness_score,
            "policy": ctx.policy_score,
            "ethical": ctx.ethical_score,
            "bias_risk": ctx.bias_risk,
        }
        
        result = {
            "decision": decision,
            "action": "allow" if decision == "accept" else (
                "deny" if decision == "reject" else "escalate_to_hitl"
            ),
            "total_score": round(total_score, 4),
            "thresholds": self.thresholds,
            "factors": factors,
            "xai": {
                "top_contributor": max(factors, key=lambda k: abs(factors[k] - 0.5)),
                "weight_explanation": {k: v * self.weights[k] for k, v in factors.items()},
            },
            "audit_required": decision == "review",
            # New fields
            "hallucination_risk": {
                "score": hallucination_risk.risk_score if hallucination_risk else None,
                "flagged": hallucination_risk.flagged if hallucination_risk else False,
                "factors": hallucination_risk.factors if hallucination_risk else {},
                "recommendation": hallucination_risk.recommendation if hallucination_risk else None
            },
            "uncertainty": {
                "epistemic": uncertainty.epistemic_uncertainty if uncertainty else None,
                "aleatoric": uncertainty.aleatoric_uncertainty if uncertainty else None,
                "confidence_interval": uncertainty.confidence_interval if uncertainty else None
            } if uncertainty else None,
            "base_confidence": base_confidence,
            "adjusted_confidence": adjusted_confidence
        }
        
        logger.info(
            f"Decision: {decision} (score={total_score:.3f}, "
            f"hallucination_risk={hallucination_risk.risk_score if hallucination_risk else 'N/A'}, "
            f"uncertainty={uncertainty.epistemic_uncertainty if uncertainty else 'N/A'})"
        )
        
        return result
    
    def update_weights(self, new_weights: Dict[str, float]):
        """Adjust decision weights (admin only)."""
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")
        self.weights.update(new_weights)
        logger.info(f"Decision weights updated: {self.weights}")


# Global singleton
decision_engine = DecisionEngine()
