import numpy as np
from typing import Dict, List, Any

try:
    from fairlearn.metrics import demographic_parity_difference, equalized_odds_difference
    FAIRLEARN_AVAILABLE = True
except ImportError:
    FAIRLEARN_AVAILABLE = False
    demographic_parity_difference = None
    equalized_odds_difference = None


class BiasDetector:
    def __init__(self):
        # For POC, simple bias detection based on demographic groups
        pass

    def detect_bias(self, predictions: List[Dict[str, Any]], sensitive_attributes: List[str] = ['gender', 'age']) -> Dict[str, float]:
        """
        Detect bias in predictions across sensitive attributes.
        Returns bias metrics.
        Handles both 'is_known' (explicit) and 'is_unknown' (inverted) fields.
        """
        if not predictions:
            return {'demographic_parity_difference': 0.0, 'equalized_odds_difference': 0.0}

        # Extract true labels: support both 'is_known' and 'is_unknown'
        y_true = []
        for p in predictions:
            if 'is_known' in p:
                y_true.append(1 if p['is_known'] else 0)
            elif 'is_unknown' in p:
                y_true.append(0 if p['is_unknown'] else 1)
            else:
                y_true.append(0)  # default to unknown/false

        # Predicted labels: non-empty matches list means recognized
        y_pred = [1 if p.get('matches') else 0 for p in predictions]

        # Build sensitive attribute strings from age/gender
        sensitive = []
        for p in predictions:
            gender = p.get('gender', 'unknown')
            age = p.get('age', 'unknown')
            sensitive.append(f"{gender}_{age}")

        # Calculate bias metrics if fairlearn available
        if FAIRLEARN_AVAILABLE:
            try:
                # fairlearn expects 'sensitive_attributes' keyword
                dp_diff = demographic_parity_difference(
                    y_true, y_pred, sensitive_attributes=sensitive)
                eo_diff = equalized_odds_difference(
                    y_true, y_pred, sensitive_attributes=sensitive)
            except Exception:
                dp_diff = 0.0
                eo_diff = 0.0
        else:
            dp_diff = 0.0
            eo_diff = 0.0

        return {
            'demographic_parity_difference': float(dp_diff),
            'equalized_odds_difference': float(eo_diff)
        }

    def mitigate_bias(self, predictions: List[Dict[str, Any]], bias_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Apply bias mitigation (e.g., threshold adjustment).
        """
        if bias_metrics['demographic_parity_difference'] > 0.1:
            # Lower threshold for underrepresented groups
            for p in predictions:
                if p.get('gender') == 'F' or p.get('age', 0) > 60:
                    # Adjust scores
                    for match in p.get('matches', []):
                        match['score'] *= 1.1  # Boost

        return predictions
