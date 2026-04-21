import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio


class DecisionStrategy(Enum):
    CONSERVATIVE = "conservative"  # High threshold
    BALANCED = "balanced"      # Standard
    AGGRESSIVE = "aggressive" # Lower threshold


@dataclass
class IdentityMatch:
    """Single identity match result."""
    person_id: str
    name: Optional[str]
    score: float
    source: str  # face, voice, gait
    is_verified: bool = False


@dataclass
class ScoringResult:
    """Final identity scoring result."""
    primary_match: Optional[IdentityMatch]
    all_matches: List[IdentityMatch]
    identity_score: float
    
    # Component scores
    face_score: float = 0.0
    voice_score: float = 0.0
    gait_score: float = 0.0
    spoof_score: float = 0.0
    
    # Decision
    decision: str = "unknown"  # allow, deny, review
    confidence: float = 0.0
    risk_level: str = "low"
    factors: List[Dict] = field(default_factory=list)
    
    # Metadata
    processing_time_ms: float = 0.0
    timestamp: str = ""


class IdentityScoringEngine:
    """
    Core intelligence layer for identity scoring.
    
    identity_score = (
        face_confidence * 0.5 +
        voice_confidence * 0.2 +
        gait_confidence * 0.2 +
        spoof_score * 0.1
    )
    """
    
    # Default weights
    DEFAULT_WEIGHTS = {
        "face": 0.5,
        "voice": 0.2,
        "gait": 0.2,
        "spoof": 0.1
    }
    
    # Strategy-based thresholds
    THRESHOLDS = {
        DecisionStrategy.CONSERVATIVE: {
            "allow": 0.85,
            "deny": 0.25,
            "review": 0.60
        },
        DecisionStrategy.BALANCED: {
            "allow": 0.70,
            "deny": 0.20,
            "review": 0.50
        },
        DecisionStrategy.AGGRESSIVE: {
            "allow": 0.50,
            "deny": 0.10,
            "review": 0.30
        }
    }
    
    def __init__(self, strategy: DecisionStrategy = DecisionStrategy.BALANCED):
        self.strategy = strategy
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self.thresholds = self.THRESHOLDS[strategy]
        
        # Evaluation tracking
        self.evaluation_log: List[Dict] = []
        self.max_log_size = 10000
        
        # Adaptive thresholds
        self._load_adaptive_thresholds()
    
    def _load_adaptive_thresholds(self):
        """Load adaptive thresholds from evaluation history."""
        if len(self.evaluation_log) < 100:
            return
        
        # Calculate recent accuracy
        recent = self.evaluation_log[-100:]
        fp = sum(1 for e in recent if e.get("false_positive"))
        fn = sum(1 for e in recent if e.get("false_negative"))
        
        # Adjust if needed
        if fn > fp + 10:
            # Too many denials - lower threshold slightly
            self.thresholds["allow"] *= 0.95
        elif fp > fn + 5:
            # Too many accepts - raise threshold
            self.thresholds["allow"] *= 1.05
    
    def score_identity(
        self,
        face_result: Optional[Dict] = None,
        voice_result: Optional[Dict] = None,
        gait_result: Optional[Dict] = None,
        liveness_result: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> ScoringResult:
        """Calculate fused identity score."""
        start_time = datetime.utcnow()
        
        metadata = metadata or {}
        factors = []
        
        # Extract component scores
        face_score = 0.0
        face_matches = []
        
        if face_result and face_result.get("faces"):
            # Get best face match
            best_face = face_result["faces"][0] if face_result["faces"] else {}
            if best_face.get("matches"):
                match = best_face["matches"][0]
                face_matches.append(IdentityMatch(
                    person_id=match.get("person_id"),
                    name=match.get("name"),
                    score=match.get("score", 0.0),
                    source="face"
                ))
                face_score = match.get("score", 0.0)
            else:
                face_matches.append(IdentityMatch(
                    person_id=None,
                    name=None,
                    score=0.0,
                    source="face"
                ))
        
        voice_score = 0.0
        voice_matches = []
        
        if voice_result and voice_result.get("matches"):
            match = voice_result["matches"][0]
            voice_matches.append(IdentityMatch(
                person_id=match.get("person_id"),
                name=match.get("name"),
                score=match.get("score", 0.0),
                source="voice"
            ))
            voice_score = match.get("score", 0.0)
        
        gait_score = 0.0
        gait_matches = []
        
        if gait_result and gait_result.get("matches"):
            match = gait_result["matches"][0]
            gait_matches.append(IdentityMatch(
                person_id=match.get("person_id"),
                name=match.get("name"),
                score=match.get("score", 0.0),
                source="gait"
            ))
            gait_score = match.get("score", 0.0)
        
        # Spoof detection (inverted - lower is better)
        spoof_score = 1.0
        if liveness_result:
            spoof_score = liveness_result.get("spoof_score", 0.0)
        elif face_result:
            spoof_score = face_result[0].get("spoof_score", 0.0) if face_result else 0.0
        
        # Calculate identity score using weighted fusion
        identity_score = (
            face_score * self.weights["face"] +
            voice_score * self.weights["voice"] +
            gait_score * self.weights["gait"] +
            (1.0 - spoof_score) * self.weights["spoof"]
        )
        
        # Determine primary match
        all_matches = face_matches + voice_matches + gait_matches
        all_matches = [m for m in all_matches if m.person_id is not None]
        
        # If multiple sources agree, boost confidence
        person_scores: Dict[str, List[float]] = {}
        for match in all_matches:
            if match.person_id:
                if match.person_id not in person_scores:
                    person_scores[match.person_id] = []
                person_scores[match.person_id].append(match.score)
        
        # Average scores per person
        for pid, scores in person_scores.items():
            person_scores[pid] = np.mean(scores)
        
        # Find best consistent match
        primary_match = None
        if person_scores:
            best_pid = max(person_scores.keys(), key=lambda p: person_scores[p])
            primary_match = IdentityMatch(
                person_id=best_pid,
                name=next((m.name for m in all_matches if m.person_id == best_pid), None),
                score=person_scores[best_pid],
                source="fused"
            )
        
        # Detect cross-source agreement
        unique_sources = set(m.source for m in all_matches)
        if len(unique_sources) >= 2:
            factors.append({
                "factor": "multi_source_verification",
                "sources": list(unique_sources),
                "impact": 0.1
            })
            identity_score *= 1.1  # Boost for multi-source
        
        # Make decision
        decision = "review"
        if identity_score >= self.thresholds["allow"]:
            decision = "allow"
        elif identity_score <= self.thresholds["deny"]:
            decision = "deny"
        
        # Risk assessment
        risk_level = "low"
        if spoof_score > 0.5:
            risk_level = "critical"
            decision = "deny"
            factors.append({
                "factor": "spoof_detected",
                "value": spoof_score,
                "impact": 0.4
            })
        elif spoof_score > 0.3:
            risk_level = "high"
            decision = "review"
            factors.append({
                "factor": "spoof_suspected",
                "value": spoof_score,
                "impact": 0.2
            })
        
        # Check for unknown (no match)
        if not primary_match or primary_match.person_id is None:
            if risk_level != "critical":
                risk_level = "medium"
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        result = ScoringResult(
            primary_match=primary_match,
            all_matches=all_matches,
            identity_score=min(identity_score, 1.0),
            face_score=face_score,
            voice_score=voice_score,
            gait_score=gait_score,
            spoof_score=spoof_score,
            decision=decision,
            confidence=identity_score,
            risk_level=risk_level,
            factors=factors,
            processing_time_ms=processing_time,
            timestamp=start_time.isoformat()
        )
        
        # Log for evaluation
        self._log_evaluation(result, metadata)
        
        return result
    
    def _log_evaluation(self, result: ScoringResult, metadata: Dict):
        """Log result for continuous evaluation."""
        entry = {
            "timestamp": result.timestamp,
            "identity_score": result.identity_score,
            "decision": result.decision,
            "face_score": result.face_score,
            "voice_score": result.voice_score,
            "gait_score": result.gait_score,
            "spoof_score": result.spoof_score,
            "metadata": metadata
        }
        
        self.evaluation_log.append(entry)
        
        # Trim log
        if len(self.evaluation_log) > self.max_log_size:
            self.evaluation_log = self.evaluation_log[-self.max_log_size:]
    
    def get_evaluation_metrics(self) -> Dict:
        """Get evaluation metrics."""
        if not self.evaluation_log:
            return {"status": "no_data"}
        
        recent = self.evaluation_log[-1000:]
        
        decisions = [e["decision"] for e in recent]
        allows = decisions.count("allow")
        denies = decisions.count("deny")
        reviews = decisions.count("review")
        total = len(recent)
        
        return {
            "total_evaluations": total,
            "allows": allows,
            "denies": denies,
            "reviews": reviews,
            "allow_rate": allows / total if total > 0 else 0,
            "deny_rate": denies / total if total > 0 else 0,
            "avg_identity_score": np.mean([e["identity_score"] for e in recent]),
            "strategy": self.strategy.value,
            "current_thresholds": self.thresholds
        }
    
    def log_ground_truth(
        self,
        result: ScoringResult,
        correct_person_id: Optional[str]
    ) -> None:
        """Log ground truth for evaluation."""
        # Find the matching entry
        for entry in reversed(self.evaluation_log):
            if entry["timestamp"] == result.timestamp:
                entry["ground_truth"] = correct_person_id
                entry["false_positive"] = (
                    result.decision == "allow" and 
                    correct_person_id is not None and
                    result.primary_match and
                    result.primary_match.person_id != correct_person_id
                )
                entry["false_negative"] = (
                    result.decision in ["deny", "review"] and
                    correct_person_id is not None and
                    result.primary_match and
                    result.primary_match.person_id == correct_person_id
                )
                break
    
    def adjust_threshold(
        self,
        target_fp_rate: float = 0.01,
        target_fn_rate: float = 0.05
    ) -> Dict:
        """Auto-adjust thresholds based on evaluation."""
        if len(self.evaluation_log) < 100:
            return {"status": "insufficient_data"}
        
        recent = self.evaluation_log[-500:]
        
        # Count actual errors
        fp = sum(1 for e in recent if e.get("false_positive"))
        fn = sum(1 for e in recent if e.get("false_negative"))
        total = len(recent)
        
        current_fp = fp / total
        current_fn = fn / total
        
        adjustments = {}
        
        # Adjust if needed
        if current_fp > target_fp_rate:
            # Too many false accepts - raise threshold
            self.thresholds["allow"] *= 1.1
            adjustments["action"] = "raised_threshold"
        elif current_fn > target_fn_rate:
            # Too many false rejects - lower threshold
            self.thresholds["allow"] *= 0.9
            adjustments["action"] = "lowered_threshold"
        
        adjustments["previous_fp"] = current_fp
        adjustments["previous_fn"] = current_fn
        adjustments["new_allow_threshold"] = self.thresholds["allow"]
        
        return adjustments


class MultiModalFusion:
    """Additional fusion strategies."""
    
    @staticmethod
    def weighted_average(
        results: List[Dict],
        weights: List[float]
    ) -> float:
        """Weighted average fusion."""
        if not results or not weights:
            return 0.0
        
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        scores = [r.get("score", 0.0) for r in results]
        return float(np.dot(scores, weights))
    
    @staticmethod
    def max_fusion(results: List[Dict]) -> float:
        """Max score fusion."""
        if not results:
            return 0.0
        return max(r.get("score", 0.0) for r in results)
    
    @staticmethod
    def min_fusion(results: List[Dict]) -> float:
        """Min score fusion (all must agree)."""
        if not results:
            return 0.0
        return min(r.get("score", 0.0) for r in results)
    
    @staticmethod
    def geometric_fusion(results: List[Dict]) -> float:
        """Geometric mean fusion."""
        if not results:
            return 0.0
        
        scores = [r.get("score", 0.01) for r in results]
        scores = np.array(scores)
        scores = np.clip(scores, 0.01, 1.0)
        
        return float(np.exp(np.mean(np.log(scores))))


# Global scoring engine
scoring_engine = IdentityScoringEngine()


def get_scoring_engine() -> IdentityScoringEngine:
    """Get the global scoring engine."""
    return scoring_engine