import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import os


@dataclass
class ModelMetrics:
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    far: float = 0.0  # False Accept Rate
    frr: float = 0.0  # False Reject Rate
    eer: float = 0.0  # Equal Error Rate
    sample_size: int = 0
    eval_time: str = ""


@dataclass
class EnvironmentProfile:
    environment_id: str
    lighting_conditions: str  # bright, moderate, low, mixed
    camera_quality: str  # high, medium, low
    avg_face_distance: float = 0.0
    face_angle_variance: float = 0.0
    motion_blur: float = 0.0
    calibration_score: float = 0.0
    last_calibrated: str = ""
    model_version: str = ""


class ModelCalibrator:
    """Production ML calibration system for environment-specific tuning."""
    
    def __init__(self, models_dir: str = "/app/models"):
        self.models_dir = models_dir
        self.calibration_cache = {}
        self.environment_profiles = {}
        
    def create_environment_profile(
        self,
        environment_id: str,
        lighting: str,
        camera_quality: str,
        avg_distance: float,
        angle_variance: float,
        motion_blur: float
    ) -> EnvironmentProfile:
        """Create an environment profile for calibration."""
        profile = EnvironmentProfile(
            environment_id=environment_id,
            lighting_conditions=lighting,
            camera_quality=camera_quality,
            avg_face_distance=avg_distance,
            face_angle_variance=angle_variance,
            motion_blur=motion_blur,
            calibration_score=0.5,
            last_calibrated=datetime.utcnow().isoformat(),
            model_version="v1.0"
        )
        self.environment_profiles[environment_id] = profile
        return profile
    
    def detect_environment(self, frame) -> str:
        """Auto-detect environment conditions from a sample frame."""
        # Calculate brightness
        brightness = np.mean(frame)
        
        # Estimate lighting condition
        if brightness > 180:
            lighting = "bright"
        elif brightness > 100:
            lighting = "moderate"
        elif brightness > 50:
            lighting = "low"
        else:
            lighting = "very_low"
        
        # Calculate motion blur using Laplacian variance
        import cv2
        laplacian = cv2.Laplacian(frame, cv2.CV_64F)
        blur = laplacian.var()
        
        if blur > 500:
            camera_quality = "high"
        elif blur > 200:
            camera_quality = "medium"
        else:
            camera_quality = "low"
        
        return f"{lighting}_{camera_quality}"
    
    def calibrate_for_environment(
        self,
        environment_id: str,
        sample_embeddings: np.ndarray,
        sample_labels: np.ndarray,
        thresholdAdjustment: float = 0.0
    ) -> Tuple[float, ModelMetrics]:
        """Calibrate threshold based on environment samples."""
        if len(sample_embeddings) < 10:
            return 0.4, ModelMetrics()
        
        # Calculate metrics across different thresholds
        thresholds = np.arange(0.2, 0.8, 0.05)
        best_threshold = 0.4
        best_eer = 1.0
        
        for thresh in thresholds:
            metrics = self._evaluate_samples(
                sample_embeddings, sample_labels, thresh + thresholdAdjustment
            )
            if abs(metrics.eer - 0.01) < abs(best_eer - 0.01):
                best_eer = metrics.eer
                best_threshold = thresh
        
        # Update profile
        if environment_id in self.environment_profiles:
            self.environment_profiles[environment_id].calibration_score = 1.0 - best_eer
            self.environment_profiles[environment_id].last_calibrated = datetime.utcnow().isoformat()
        
        return best_threshold, ModelMetrics(
            accuracy=1.0 - best_eer,
            eer=best_eer,
            sample_size=len(sample_embeddings),
            eval_time=datetime.utcnow().isoformat()
        )
    
    def calibrate_scores_platt(self, raw_scores: np.ndarray, labels: np.ndarray) -> Tuple[float, float]:
        """
        Calibrate scores using Platt scaling (Logistic Regression on scores).
        Returns (A, B) such that P(y=1|x) = 1 / (1 + exp(A*f(x) + B))
        """
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression()
        lr.fit(raw_scores.reshape(-1, 1), labels)
        return lr.coef_[0][0], lr.intercept_[0]

    def calibrate_scores_isotonic(self, raw_scores: np.ndarray, labels: np.ndarray):
        """
        Calibrate scores using Isotonic Regression.
        Best for non-parametric calibration.
        """
        from sklearn.isotonic import IsotonicRegression
        ir = IsotonicRegression(out_of_bounds='clip')
        ir.fit(raw_scores, labels)
        return ir

    def get_calibrated_probability(self, raw_score: float, method: str = "platt", params: Any = None) -> float:
        """Get calibrated probability from raw score."""
        if method == "platt" and params:
            A, B = params
            return 1.0 / (1.0 + np.exp(A * raw_score + B))
        elif method == "isotonic" and params:
            ir = params
            return float(ir.transform([raw_score])[0])
        else:
            # Fallback to sigmoid
            return 1.0 / (1.0 + np.exp(-raw_score))

    def _evaluate_samples(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
        threshold: float
    ) -> ModelMetrics:
        """Evaluate sample embeddings against threshold."""
        # Simplified: assumes embeddings are matched labels
        correct = 0
        false_accepts = 0
        false_rejects = 0
        
        for i, emb in enumerate(embeddings):
            score = np.dot(emb, emb)  # Simplified - use actual matching
            if score > threshold:
                if labels[i] == 1:
                    correct += 1
                else:
                    false_accepts += 1
            else:
                if labels[i] == 0:
                    correct += 1
                else:
                    false_rejects += 1
        
        total = len(embeddings)
        far = false_accepts / max(total - sum(labels), 1)
        frr = false_rejects / max(sum(labels), 1)
        eer = (far + frr) / 2
        
        return ModelMetrics(
            accuracy=correct / total if total > 0 else 0,
            precision=correct / max((correct + false_accepts), 1),
            recall=correct / max((correct + false_rejects), 1),
            far=far,
            frr=frr,
            eer=eer,
            sample_size=total
        )


class EvaluationPipeline:
    """Continuous evaluation for model performance."""
    
    def __init__(self):
        self.eval_history: List[Dict] = []
        self.drift_detection_threshold = 0.05
        
    def log_inference_result(
        self,
        query_embedding: np.ndarray,
        predicted_id: str,
        ground_truth: Optional[str],
        metadata: Dict
    ) -> None:
        """Log inference for later evaluation."""
        is_correct = predicted_id == ground_truth if ground_truth else None
        
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "predicted_id": predicted_id,
            "ground_truth": ground_truth,
            "correct": is_correct,
            "environment": metadata.get("environment", "unknown"),
            "lighting": metadata.get("lighting", "unknown"),
            "face_quality": metadata.get("face_quality", 0.0),
            "spoof_score": metadata.get("spoof_score", 0.0),
            "processing_time_ms": metadata.get("processing_time_ms", 0.0)
        }
        self.eval_history.append(result)
        
        # Check for drift every 1000 inferences
        if len(self.eval_history) % 1000 == 0:
            self._check_drift()
    
    def _check_drift(self) -> Optional[Dict]:
        """Detect performance drift."""
        recent = self.eval_history[-1000:]
        
        # Calculate accuracy by environment
        env_accuracy = {}
        for r in recent:
            env = r.get("environment", "unknown")
            if env not in env_accuracy:
                env_accuracy[env] = {"correct": 0, "total": 0}
            
            if r.get("correct") is not None:
                env_accuracy[env]["total"] += 1
                if r["correct"]:
                    env_accuracy[env]["correct"] += 1
        
        # Calculate drift
        drift_alerts = []
        for env, stats in env_accuracy.items():
            acc = stats["correct"] / max(stats["total"], 1)
            
            # Check baseline
            baseline_envs = [e for e in self.eval_history if e.get("environment") == env]
            if len(baseline_envs) > 100:
                baseline = sum(1 for e in baseline_envs[-100:] if e.get("correct")) / 100
                if abs(acc - baseline) > self.drift_detection_threshold:
                    drift_alerts.append({
                        "environment": env,
                        "baseline_accuracy": baseline,
                        "current_accuracy": acc,
                        "drift": acc - baseline
                    })
        
        return drift_alerts if drift_alerts else None
    
    def generate_report(self, period_days: int = 7) -> Dict:
        """Generate evaluation report."""
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        recent = [
            r for r in self.eval_history
            if datetime.fromisoformat(r["timestamp"]) > cutoff
        ]
        
        if not recent:
            return {"status": "no_data", "message": "No evaluations in period"}
        
        total = len(recent)
        correct = sum(1 for r in recent if r.get("correct") is True)
        known = sum(1 for r in recent if r.get("correct") is not None)
        
        return {
            "period_days": period_days,
            "total_inferences": total,
            "inferences_with_ground_truth": known,
            "overall_accuracy": correct / known if known > 0 else None,
            "by_environment": self._aggregate_by("environment", recent),
            "by_lighting": self._aggregate_by("lighting", recent),
            "avg_processing_time_ms": np.mean([
                r["processing_time_ms"] for r in recent
            ]) if recent else 0,
            "spoof_detection_rate": sum(1 for r in recent if r.get("spoof_score", 0) > 0.5) / total
        }
    
    def _aggregate_by(self, field: str, data: List[Dict]) -> Dict:
        """Aggregate metrics by field."""
        groups = {}
        for r in data:
            val = r.get(field, "unknown")
            if val not in groups:
                groups[val] = {"correct": 0, "total": 0}
            groups[val]["total"] += 1
            if r.get("correct") is True:
                groups[val]["correct"] += 1
        
        return {
            k: {"accuracy": v["correct"] / v["total"], "count": v["total"]}
            for k, v in groups.items()
        }


class ModelVersionManager:
    """Manage model versioning and rollout."""
    
    def __init__(self, models_dir: str = "/app/models"):
        self.models_dir = models_dir
        self.versions: Dict[str, Dict] = {}
        self.active_version = "v1.0"
        
    def register_version(
        self,
        version: str,
        metrics: ModelMetrics,
        environment: str,
        changelog: List[str]
    ) -> None:
        """Register a new model version."""
        self.versions[version] = {
            "version": version,
            "metrics": vars(metrics),
            "environment": environment,
            "changelog": changelog,
            "registered_at": datetime.utcnow().isoformat(),
            "status": "staging"
        }
    
    def promote_to_production(self, version: str) -> bool:
        """Promote a version to production."""
        if version not in self.versions:
            return False
        
        # Keep old version in rollback
        self.versions[self.active_version]["status"] = "rollback"
        
        self.versions[version]["status"] = "production"
        self.versions[version]["promoted_at"] = datetime.utcnow().isoformat()
        self.active_version = version
        
        return True
    
    def rollback(self) -> Optional[str]:
        """Rollback to previous version."""
        for version, info in self.versions.items():
            if info["status"] == "rollback":
                self.promote_to_production(version)
                return version
        return None


# Global instances
calibrator = ModelCalibrator()
evaluation_pipeline = EvaluationPipeline()
version_manager = ModelVersionManager()