import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import threading


@dataclass
class EvaluationEntry:
    """Single evaluation entry."""
    timestamp: str
    query_id: str
    
    # Input
    person_id: Optional[str]  # Ground truth
    predicted_id: Optional[str]
    
    # Scores
    identity_score: float
    face_score: float
    voice_score: float
    gait_score: float
    spoof_score: float
    
    # Decision
    decision: str
    
    # Context
    environment: str
    lighting: str
    camera_id: Optional[str]
    processing_time_ms: float


@dataclass
class DriftAlert:
    """Performance drift alert."""
    alert_type: str  # accuracy_drop, latency_increase, error_rate_increase
    metric: str
    previous_value: float
    current_value: float
    change_percent: float
    severity: str  # low, medium, high, critical
    timestamp: str
    recommended_action: str


class ContinuousEvaluation:
    """Continuous evaluation pipeline."""
    
    def __init__(
        self,
        window_size: int = 1000,
        alert_threshold: float = 0.05
    ):
        self.window_size = window_size
        self.alert_threshold = alert_threshold
        
        self.evaluations: List[EvaluationEntry] = []
        self.lock = threading.Lock()
        
        # Baseline metrics (first 1000 evaluations)
        self.baseline: Dict[str, float] = {}
        self.baseline_established = False
        
        # Alerts
        self.alerts: List[DriftAlert] = []
        self.max_alerts = 100
    
    def log_evaluation(
        self,
        query_id: str,
        predicted_id: Optional[str],
        ground_truth: Optional[str],
        scores: Dict[str, float],
        decision: str,
        metadata: Dict
    ) -> None:
        """Log an evaluation."""
        entry = EvaluationEntry(
            timestamp=datetime.utcnow().isoformat(),
            query_id=query_id,
            person_id=ground_truth,
            predicted_id=predicted_id,
            identity_score=scores.get("identity_score", 0.0),
            face_score=scores.get("face_score", 0.0),
            voice_score=scores.get("voice_score", 0.0),
            gait_score=scores.get("gait_score", 0.0),
            spoof_score=scores.get("spoof_score", 0.0),
            decision=decision,
            environment=metadata.get("environment", "unknown"),
            lighting=metadata.get("lighting", "unknown"),
            camera_id=metadata.get("camera_id"),
            processing_time_ms=metadata.get("processing_time_ms", 0.0)
        )
        
        with self.lock:
            self.evaluations.append(entry)
            
            # Keep window size
            if len(self.evaluations) > self.window_size * 2:
                self.evaluations = self.evaluations[-self.window_size:]
            
            # Establish baseline after enough data
            if not self.baseline_established and len(self.evaluations) >= self.window_size:
                self._establish_baseline()
    
    def _establish_baseline(self) -> None:
        """Establish baseline metrics."""
        if len(self.evaluations) < self.window_size:
            return
        
        recent = self.evaluations[-self.window_size:]
        
        # Calculate accuracy (when ground truth available)
        with_gt = [e for e in recent if e.person_id is not None]
        
        if with_gt:
            correct = sum(
                1 for e in with_gt
                if e.predicted_id == e.person_id
            )
            self.baseline["accuracy"] = correct / len(with_gt)
        else:
            self.baseline["accuracy"] = 0.0
        
        self.baseline["avg_identity_score"] = np.mean([
            e.identity_score for e in recent
        ])
        
        self.baseline["avg_face_score"] = np.mean([
            e.face_score for e in recent
        ])
        
        self.baseline["avg_spoof_score"] = np.mean([
            e.spoof_score for e in recent
        ])
        
        self.baseline["avg_processing_time"] = np.mean([
            e.processing_time_ms for e in recent
        ])
        
        self.baseline_established = True
        
        print(f"Baseline established: {self.baseline}")
    
    def check_drift(self) -> List[DriftAlert]:
        """Check for performance drift."""
        if not self.baseline_established:
            return []
        
        if len(self.evaluations) < 100:
            return []
        
        recent = self.evaluations[-100:]
        alerts = []
        
        with_gt = [e for e in recent if e.person_id is not None]
        
        # Check accuracy drift
        if with_gt:
            correct = sum(
                1 for e in with_gt
                if e.predicted_id == e.person_id
            )
            current_accuracy = correct / len(with_gt)
            
            if self.baseline.get("accuracy", 0) > 0:
                change = (current_accuracy - self.baseline["accuracy"]) / self.baseline["accuracy"]
                
                if abs(change) > self.alert_threshold:
                    alerts.append(DriftAlert(
                        alert_type="accuracy_drop" if change < 0 else "accuracy_increase",
                        metric="accuracy",
                        previous_value=self.baseline["accuracy"],
                        current_value=current_accuracy,
                        change_percent=change * 100,
                        severity=self._severity_from_change(change),
                        timestamp=datetime.utcnow().isoformat(),
                        recommended_action="review_threshold" if change < 0 else "consider_lower_threshold"
                    ))
        
        # Check latency drift
        current_latency = np.mean([e.processing_time_ms for e in recent])
        
        if self.baseline.get("avg_processing_time", 0) > 0:
            latency_change = (
                current_latency - self.baseline["avg_processing_time"]
            ) / self.baseline["avg_processing_time"]
            
            if latency_change > self.alert_threshold:
                alerts.append(DriftAlert(
                    alert_type="latency_increase",
                    metric="processing_time_ms",
                    previous_value=self.baseline["avg_processing_time"],
                    current_value=current_latency,
                    change_percent=latency_change * 100,
                    severity=self._severity_from_change(latency_change),
                    timestamp=datetime.utcnow().isoformat(),
                    recommended_action="scale_infrastructure"
                ))
        
        # Check by environment
        env_metrics = self._aggregate_by("environment")
        for env, metrics in env_metrics.items():
            if metrics.get("accuracy") and self.baseline.get("accuracy"):
                env_change = (
                    metrics["accuracy"] - self.baseline["accuracy"]
                ) / self.baseline["accuracy"]
                
                if abs(env_change) > self.alert_threshold * 2:
                    alerts.append(DriftAlert(
                        alert_type="accuracy_drop" if env_change < 0 else "accuracy_increase",
                        metric=f"accuracy_by_environment_{env}",
                        previous_value=self.baseline["accuracy"],
                        current_value=metrics["accuracy"],
                        change_percent=env_change * 100,
                        severity="medium",
                        timestamp=datetime.utcnow().isoformat(),
                        recommended_action=f"recalibrate_environment_{env}"
                    ))
        
        # Store alerts
        self.alerts.extend(alerts)
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        return alerts
    
    def _severity_from_change(self, change: float) -> str:
        """Determine severity from change percentage."""
        abs_change = abs(change)
        
        if abs_change > 0.3:
            return "critical"
        elif abs_change > 0.15:
            return "high"
        elif abs_change > 0.05:
            return "medium"
        else:
            return "low"
    
    def _aggregate_by(self, field: str) -> Dict:
        """Aggregate metrics by field."""
        groups = {}
        
        for e in self.evaluations[-1000:]:
            value = getattr(e, field, "unknown")
            
            if value not in groups:
                groups[value] = {"total": 0, "correct": 0, "scores": []}
            
            groups[value]["total"] += 1
            groups[value]["scores"].append(e.identity_score)
            
            if e.person_id and e.predicted_id == e.person_id:
                groups[value]["correct"] += 1
        
        return {
            k: {
                "accuracy": v["correct"] / v["total"] if v["total"] > 0 else 0,
                "avg_score": np.mean(v["scores"])
            }
            for k, v in groups.items()
        }
    
    def get_report(self, period: str = "24h") -> Dict:
        """Generate evaluation report."""
        # Determine window based on period
        if period == "1h":
            window = 3600
        elif period == "24h":
            window = 86400
        elif period == "7d":
            window = 604800
        else:
            window = 3600
        
        cutoff = datetime.utcnow() - timedelta(seconds=window)
        
        recent = [
            e for e in self.evaluations
            if datetime.fromisoformat(e.timestamp) > cutoff
        ]
        
        if not recent:
            return {"status": "no_data", "period": period}
        
        with_gt = [e for e in recent if e.person_id is not None]
        
        if with_gt:
            correct = sum(1 for e in with_gt if e.predicted_id == e.person_id)
            accuracy = correct / len(with_gt)
        else:
            accuracy = None
        
        return {
            "period": period,
            "total_evaluations": len(recent),
            "with_ground_truth": len(with_gt),
            "accuracy": accuracy,
            "avg_identity_score": np.mean([e.identity_score for e in recent]),
            "avg_processing_time_ms": np.mean([e.processing_time_ms for e in recent]),
            "by_environment": self._aggregate_by("environment"),
            "by_lighting": self._aggregate_by("lighting"),
            "baseline_established": self.baseline_established,
            "baseline": self.baseline,
            "recent_alerts": [
                {
                    "type": a.alert_type,
                    "severity": a.severity,
                    "timestamp": a.timestamp
                }
                for a in self.alerts[-10:]
            ]
        }
    
    def get_false_positives(
        self,
        limit: int = 100
    ) -> List[Dict]:
        """Get recent false positives for analysis."""
        return [
            {
                "timestamp": e.timestamp,
                "query_id": e.query_id,
                "predicted": e.predicted_id,
                "actual": e.person_id,
                "score": e.identity_score
            }
            for e in self.evaluations[-500:]
            if e.predicted_id and e.person_id and e.predicted_id != e.person_id
        ][:limit]
    
    def get_false_negatives(
        self,
        limit: int = 100
    ) -> List[Dict]:
        """Get recent false negatives for analysis."""
        return [
            {
                "timestamp": e.timestamp,
                "query_id": e.query_id,
                "predicted": e.predicted_id,
                "actual": e.person_id,
                "score": e.identity_score
            }
            for e in self.evaluations[-500:]
            if e.decision in ["deny", "review"] and e.person_id
            and e.predicted_id != e.person_id
        ][:limit]


# Global evaluation pipeline
evaluation_pipeline = ContinuousEvaluation()


def get_evaluation_pipeline() -> ContinuousEvaluation:
    """Get the global evaluation pipeline."""
    return evaluation_pipeline