import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DecisionStrategy(Enum):
    CONSERVATIVE = "conservative"  # High threshold
    BALANCED = "balanced"  # Standard
    AGGRESSIVE = "aggressive"  # Lower threshold, more matches
    VERIFY_REQUIRED = "verify_required"  # Require additional verification


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class IdentityClaim:
    """A claim about someone's identity."""
    person_id: Optional[str]
    name: Optional[str]
    confidence: float
    source: str  # face, voice, gait, manual
    timestamp: str


@dataclass
class DecisionResult:
    """Decision engine result."""
    decision: str  # allow, deny, review, challenge
    risk_level: RiskLevel
    risk_score: float
    confidence: float
    factors: List[Dict]
    requires_verification: bool
    verification_type: Optional[str]
    next_actions: List[str]


@dataclass
class FusionConfig:
    """Configuration for confidence fusion."""
    strategy: DecisionStrategy = DecisionStrategy.BALANCED
    face_weight: float = 0.5
    voice_weight: float = 0.2
    gait_weight: float = 0.2
    min_face_confidence: float = 0.4
    min_voice_confidence: float = 0.3
    min_gait_confidence: float = 0.3
    require_multi_modal: bool = False
    enable_liveness_check: bool = True
    spoof_reject_threshold: float = 0.5


class ConfidenceFusion:
    """Fuse confidence from multiple modalities."""
    
    def __init__(self, config: FusionConfig):
        self.config = config
    
    def fuse(
        self,
        face_result: Optional[Dict] = None,
        voice_result: Optional[Dict] = None,
        gait_result: Optional[Dict] = None
    ) -> Tuple[float, Dict]:
        """Fuse confidence from multiple sources."""
        scores = {}
        factors = []
        
        # Face contribution
        if face_result:
            face_score = face_result.get("score", 0.0)
            face_conf = face_result.get("confidence", 1.0)
            scores["face"] = face_score * self.config.face_weight
            factors.append({
                "source": "face",
                "raw_score": face_score,
                "confidence": face_conf,
                "weighted": scores["face"]
            })
        
        # Voice contribution
        if voice_result:
            voice_score = voice_result.get("score", 0.0)
            voice_conf = voice_result.get("confidence", 1.0)
            scores["voice"] = voice_score * self.config.voice_weight
            factors.append({
                "source": "voice",
                "raw_score": voice_score,
                "confidence": voice_conf,
                "weighted": scores["voice"]
            })
        
        # Gait contribution
        if gait_result:
            gait_score = gait_result.get("score", 0.0)
            gait_conf = gait_result.get("confidence", 1.0)
            scores["gait"] = gait_score * self.config.gait_weight
            factors.append({
                "source": "gait",
                "raw_score": gait_score,
                "confidence": gait_conf,
                "weighted": scores["gait"]
            })
        
        # Calculate fused confidence
        total_weight = sum(
            self.config.face_weight if "face" in scores else 0,
            self.config.voice_weight if "voice" in scores else 0,
            self.config.gait_weight if "gait" in scores else 0
        )
        
        fused_confidence = sum(scores.values()) / total_weight if total_weight > 0 else 0
        
        # Adjust by source confidence
        min_source_conf = min([f["confidence"] for f in factors]) if factors else 1.0
        adjusted_confidence = fused_confidence * min_source_conf
        
        return adjusted_confidence, {
            "fused": fused_confidence,
            "adjusted": adjusted_confidence,
            "factors": factors,
            "modalities_used": list(scores.keys())
        }


class RiskScorer:
    """Risk scoring for identity decisions."""
    
    def __init__(self):
        self.risk_factors = {}
    
    def calculate_risk(
        self,
        identity_claims: List[IdentityClaim],
        spoof_scores: List[float],
        metadata: Dict
    ) -> Tuple[float, Dict]:
        """Calculate risk score."""
        risk_score = 0.0
        risk_factors = []
        
        # Factor 1: Confidence variance
        if len(identity_claims) > 1:
            confidences = [c.confidence for c in identity_claims]
            var = np.var(confidences)
            if var > 0.1:
                risk_score += 0.3
                risk_factors.append({
                    "factor": "confidence_variance",
                    "value": var,
                    "risk": "high"
                })
        
        # Factor 2: Spoof detection
        if spoof_scores:
            max_spoof = max(spoof_scores)
            if max_spoof > 0.5:
                risk_score += 0.4
                risk_factors.append({
                    "factor": "spoof_detected",
                    "value": max_spoof,
                    "risk": "critical"
                })
            elif max_spoof > 0.3:
                risk_score += 0.2
                risk_factors.append({
                    "factor": "spoof_suspected",
                    "value": max_spoof,
                    "risk": "medium"
                })
        
        # Factor 3: New identity
        if identity_claims and not identity_claims[0].person_id:
            risk_score += 0.2
            risk_factors.append({
                "factor": "unknown_identity",
                "risk": "medium"
            })
        
        # Factor 4: Source mismatch
        sources = set(c.source for c in identity_claims)
        if len(sources) == 1:
            risk_score += 0.1
            risk_factors.append({
                "factor": "single_source",
                "risk": "low"
            })
        
        # Factor 5: Metadata signals
        if metadata.get("unusual_location"):
            risk_score += 0.2
            risk_factors.append({
                "factor": "unusual_location",
                "risk": "medium"
            })
        
        if metadata.get("rapid_attempts"):
            risk_score += 0.3
            risk_factors.append({
                "factor": "rapid_attempts",
                "risk": "high"
            })
        
        # Determine risk level
        if risk_score > 0.7:
            level = RiskLevel.CRITICAL
        elif risk_score > 0.4:
            level = RiskLevel.HIGH
        elif risk_score > 0.2:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        
        return min(risk_score, 1.0), {
            "risk_level": level.value,
            "risk_score": risk_score,
            "factors": risk_factors
        }


class DecisionEngine:
    """Intelligence layer for identity decisions."""
    
    def __init__(
        self,
        fusion_config: Optional[FusionConfig] = None
    ):
        self.fusion_config = fusion_config or FusionConfig()
        self.fusion = ConfidenceFusion(self.fusion_config)
        self.risk_scorer = RiskScorer()
        
        # History for context
        self.decision_history: List[DecisionResult] = []
        self.context_window = 10
        
        # Strategy thresholds
        self.thresholds = {
            DecisionStrategy.CONSERVATIVE: {
                "allow": 0.85,
                "deny": 0.3,
                "review": 0.6
            },
            DecisionStrategy.BALANCED: {
                "allow": 0.7,
                "deny": 0.2,
                "review": 0.5
            },
            DecisionStrategy.AGGRESSIVE: {
                "allow": 0.5,
                "deny": 0.1,
                "review": 0.3
            }
        }
    
    def make_decision(
        self,
        face_result: Optional[Dict] = None,
        voice_result: Optional[Dict] = None,
        gait_result: Optional[Dict] = None,
        liveness_result: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> DecisionResult:
        """Make an identity decision."""
        metadata = metadata or {}
        
        # Build identity claims
        claims = []
        
        if face_result and face_result.get("matches"):
            for match in face_result["matches"][:3]:
                claims.append(IdentityClaim(
                    person_id=match.get("person_id"),
                    name=match.get("name"),
                    confidence=match.get("score", 0.0),
                    source="face",
                    timestamp=datetime.utcnow().isoformat()
                ))
        
        # Spoof scores
        spoof_scores = []
        if liveness_result:
            spoof_scores.append(liveness_result.get("spoof_score", 0.0))
        if face_result:
            spoof_scores.append(face_result.get("spoof_score", 0.0))
        
        # Calculate fused confidence
        if self.fusion_config.require_multi_modal and len(claims) > 0:
            if voice_result or gait_result:
                fused_conf, fusion_details = self.fusion.fuse(
                    face_result, voice_result, gait_result
                )
            else:
                fused_conf = claims[0].confidence if claims else 0.0
                fusion_details = {"factors": []}
        else:
            fused_conf = claims[0].confidence if claims else 0.0
            fusion_details = {"factors": []}
        
        # Calculate risk
        risk_score, risk_details = self.risk_scorer.calculate_risk(
            claims, spoof_scores, metadata
        )
        
        # Get strategy thresholds
        strgy = self.thresholds[self.fusion_config.strategy]
        
        # Determine decision
        factors = []
        factors.extend(fusion_details.get("factors", []))
        factors.extend(risk_details.get("factors", []))
        
        # Check liveness requirement
        requires_verification = False
        verification_type = None
        
        if self.fusion_config.enable_liveness_check:
            if liveness_result and liveness_result.get("spoof_score", 0) > self.fusion_config.spoof_reject_threshold:
                return DecisionResult(
                    decision="deny",
                    risk_level=RiskLevel.CRITICAL,
                    risk_score=1.0,
                    confidence=fused_conf,
                    factors=factors,
                    requires_verification=True,
                    verification_type="liveness_failed",
                    next_actions=["review_manual"]
                )
        
        # Decision logic
        if fused_conf >= strgy["allow"]:
            if risk_score < 0.3:
                decision = "allow"
            else:
                decision = "review"
        elif fused_conf <= strgy["deny"]:
            decision = "deny"
        else:
            if risk_score > 0.4:
                decision = "deny"
            elif risk_score > 0.2 or fused_conf < strgy["review"]:
                decision = "review"
            else:
                decision = "allow"
        
        # Add verification requirement for medium confidence
        requires_verification = decision == "review"
        if requires_verification:
            verification_type = "challenge_response" if not liveness_result else "manual_review"
        
        # Build next actions
        next_actions = []
        if decision == "review":
            next_actions.append("manual_review")
            next_actions.append("verify_identity")
        if decision == "allow" and risk_score > 0.2:
            next_actions.append("log_for_audit")
        if decision == "deny":
            next_actions.append("increment_failed_attempts")
            next_actions.append("potential_lockout")
        
        # Map risk level
        risk_level_map = {
            RiskLevel.LOW: RiskLevel.LOW,
            RiskLevel.MEDIUM: RiskLevel.MEDIUM,
            RiskLevel.HIGH: RiskLevel.HIGH,
            RiskLevel.CRITICAL: RiskLevel.CRITICAL
        }
        
        result = DecisionResult(
            decision=decision,
            risk_level=risk_level_map.get(risk_details["risk_level"], RiskLevel.MEDIUM),
            risk_score=risk_score,
            confidence=fused_conf,
            factors=factors,
            requires_verification=requires_verification,
            verification_type=verification_type,
            next_actions=next_actions
        )
        
        # Update history
        self.decision_history.append(result)
        if len(self.decision_history) > self.context_window:
            self.decision_history = self.decision_history[-self.context_window:]
        
        return result
    
    def get_context_for_user(
        self,
        person_id: str
    ) -> Dict:
        """Get recent context for a user."""
        recent = [
            d for d in self.decision_history[-self.context_window:]
        ]
        
        if not recent:
            return {"status": "no_history"}
        
        decisions = [d.decision for d in recent]
        allow_rate = decisions.count("allow") / len(decisions)
        deny_rate = decisions.count("deny") / len(decisions)
        
        return {
            "recent_decisions": decisions,
            "allow_rate": allow_rate,
            "deny_rate": deny_rate,
            "avg_confidence": np.mean([d.confidence for d in recent]),
            "avg_risk": np.mean([d.risk_score for d in recent])
        }


# Global instances
decision_engine = DecisionEngine()


def create_decision_engine(
    strategy: DecisionStrategy = DecisionStrategy.BALANCED,
    require_multi_modal: bool = False
) -> DecisionEngine:
    """Create configured decision engine."""
    config = FusionConfig(
        strategy=strategy,
        require_multi_modal=require_multi_modal
    )
    return DecisionEngine(config)