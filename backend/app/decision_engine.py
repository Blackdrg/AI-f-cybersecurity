"""
Decision Engine - Final accept/reject after policy + ethical checks.
Production implementation with bias mitigation and explainability.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging
from enum import Enum

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
        Compute final decision from multi-modal scores.
        
        Supports both legacy parameter-based call and new context-based call.
        Legacy signature (for compatibility with existing code/tests):
            make_decision(face_result, voice_result, gait_result, liveness_result, metadata)
        
        New context-based signature:
            make_decision(context=DecisionContext(...))
        
        Returns accept/reject with explanation.
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
        # Compute weighted score
        total_score = (
            context.confidence * self.weights["confidence"] +
            context.liveness_score * self.weights["liveness"] +
            context.policy_score * self.weights["policy"] +
            context.ethical_score * self.weights["ethical"] +
            (1.0 - context.bias_risk) * self.weights["bias"]
        )
        
        # Decision logic
        if total_score >= self.thresholds["accept"]:
            decision = "accept"
            action = "allow"
        elif total_score >= self.thresholds["review"]:
            decision = "review"
            action = "escalate_to_hitl"
        else:
            decision = "reject"
            action = "deny"
        
        # Build explanation (XAI)
        factors = {
            "confidence": context.confidence,
            "liveness": context.liveness_score,
            "policy": context.policy_score,
            "ethical": context.ethical_score,
            "bias_risk": context.bias_risk,
        }
        
        result = {
            "decision": decision,
            "action": action,
            "total_score": round(total_score, 4),
            "thresholds": self.thresholds,
            "factors": factors,
            "xai": {
                "top_contributor": max(factors, key=lambda k: abs(factors[k] - 0.5)),
                "weight_explanation": {k: v * self.weights[k] for k, v in factors.items()},
            },
            "audit_required": decision == "review",
        }
        
        logger.info(f"Decision: {decision} (score={total_score:.3f})")
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
