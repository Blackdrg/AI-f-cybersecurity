import numpy as np
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

try:
    from fairlearn.metrics import (  # type: ignore
        demographic_parity_difference, 
        equalized_odds_difference,
        MetricFrame,
        selection_rate,
        false_positive_rate,
        false_negative_rate
    )
    from sklearn.metrics import accuracy_score  # type: ignore
    FAIRLEARN_AVAILABLE = True
except ImportError:
    FAIRLEARN_AVAILABLE = False
    demographic_parity_difference = None
    equalized_odds_difference = None

class BiasDetector:
    """
    Production-grade bias detection and mitigation.
    Uses Fairlearn to track performance disparities across demographics.
    """
    
    def __init__(self):
        self.min_samples_for_metrics = 5
        self.high_bias_threshold = 0.15

    def detect_bias(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect bias using Fairlearn metrics.
        Returns a detailed audit of performance across demographic groups.
        """
        if not predictions or len(predictions) < self.min_samples_for_metrics:
            return {
                'demographic_parity_difference': 0.0,
                'equalized_odds_difference': 0.0,
                'status': 'insufficient_data'
            }

        # 1. Prepare data
        y_true = []
        y_pred = []
        sensitive_features = []
        
        for p in predictions:
            # Ground truth
            y_true.append(1 if p.get('is_known') else 0)
            # Prediction (recognized if matches exist)
            y_pred.append(1 if p.get('matches') and len(p['matches']) > 0 else 0)
            # Demographics
            gender = str(p.get('gender', 'Unknown')).upper()
            age_group = self._get_age_group(p.get('age', 0))
            sensitive_features.append(f"{gender}_{age_group}")

        if not FAIRLEARN_AVAILABLE:
            return {
                'demographic_parity_difference': 0.0,
                'equalized_odds_difference': 0.0,
                'status': 'fairlearn_not_installed'
            }

        try:
            # 2. Global Metrics
            dp_diff = demographic_parity_difference(y_true, y_pred, sensitive_features=sensitive_features)
            eo_diff = equalized_odds_difference(y_true, y_pred, sensitive_features=sensitive_features)

            # 3. Granular Group Analysis
            metrics = {
                'accuracy': accuracy_score,
                'selection_rate': selection_rate,
                'fpr': false_positive_rate,
                'fnr': false_negative_rate
            }
            
            mf = MetricFrame(
                metrics=metrics,
                y_true=y_true,
                y_pred=y_pred,
                sensitive_features=sensitive_features
            )

            return {
                'demographic_parity_difference': float(dp_diff),
                'equalized_odds_difference': float(eo_diff),
                'group_metrics': mf.by_group.to_dict(),
                'status': 'analyzed'
            }
        except Exception as e:
            logger.error(f"Fairlearn analysis failed: {e}")
            return {'error': str(e), 'status': 'error'}

    def mitigate_bias(self, predictions: List[Dict[str, Any]], audit_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply post-processing bias mitigation.
        If a group is identified as having lower selection rate, boost their match scores.
        """
        if audit_report.get('status') != 'analyzed':
            return predictions

        dp_diff = audit_report.get('demographic_parity_difference', 0.0)
        
        if dp_diff > self.high_bias_threshold:
            # Find groups with lowest selection rates
            group_metrics = audit_report.get('group_metrics', {}).get('selection_rate', {})
            if not group_metrics:
                return predictions
                
            mean_rate = sum(group_metrics.values()) / len(group_metrics)
            
            for p in predictions:
                gender = str(p.get('gender', 'Unknown')).upper()
                age_group = self._get_age_group(p.get('age', 0))
                group_key = f"{gender}_{age_group}"
                
                # If this group's selection rate is significantly below average, boost scores
                group_rate = group_metrics.get(group_key, mean_rate)
                if group_rate < (mean_rate * 0.8):
                    boost_factor = 1.0 + (mean_rate - group_rate)
                    for match in p.get('matches', []):
                        match['score'] = min(1.0, match['score'] * boost_factor)
                        match['mitigation_applied'] = True

        return predictions

    def _get_age_group(self, age: int) -> str:
        if age < 18: return "Minor"
        if age < 35: return "YoungAdult"
        if age < 60: return "Adult"
        return "Senior"
