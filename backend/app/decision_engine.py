"""
Decision Engine - Final accept/reject after policy + ethical checks.
Production implementation with bias mitigation and explainability.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


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
    
    def make_decision(self, context: DecisionContext) -> Dict[str, Any]:
        """
        Compute final decision from multi-modal scores.
        Returns accept/reject with explanation.
        """
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
