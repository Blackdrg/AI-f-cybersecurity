import unittest
import numpy as np
from typing import List, Dict, Any
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.models.bias_detector import BiasDetector
from app.decision_engine import DecisionEngine

class TestModelValidation(unittest.TestCase):
    """
    Validation suite for AI/ML performance and fairness.
    """
    
    def setUp(self):
        self.bias_detector = BiasDetector()
        self.decision_engine = DecisionEngine()
        
    def test_bias_detection_logic(self):
        """Verify that bias detector correctly identifies disparities."""
        # Create a skewed dataset: 100% success for Group A, 20% for Group B
        mock_predictions = []
        
        # Group A (Male, YoungAdult) - 10 samples, all correct
        for _ in range(10):
            mock_predictions.append({
                'gender': 'M', 'age': 25, 'is_known': True, 
                'matches': [{'person_id': '1', 'score': 0.9}]
            })
            
        # Group B (Female, Senior) - 10 samples, only 2 correct
        for i in range(10):
            mock_predictions.append({
                'gender': 'F', 'age': 70, 'is_known': True, 
                'matches': [{'person_id': '2', 'score': 0.9}] if i < 2 else []
            })
            
        report = self.bias_detector.detect_bias(mock_predictions)
        
        self.assertEqual(report['status'], 'analyzed')
        self.assertGreater(report['demographic_parity_difference'], 0.5)
        print(f"[INFO] Detected Bias (DP Diff): {report['demographic_parity_difference']}")

    def test_bias_mitigation_logic(self):
        """Verify that mitigation boosts scores for underrepresented groups."""
        mock_predictions = [
            {'gender': 'F', 'age': 70, 'matches': [{'person_id': '2', 'score': 0.4}]}
        ]
        
        # Mock audit report showing low selection rate for Group B
        mock_audit = {
            'status': 'analyzed',
            'demographic_parity_difference': 0.5,
            'group_metrics': {
                'selection_rate': {'F_Senior': 0.1, 'M_YoungAdult': 0.9}
            }
        }
        
        original_score = mock_predictions[0]['matches'][0]['score']
        mitigated = self.bias_detector.mitigate_bias(mock_predictions, mock_audit)
        new_score = mitigated[0]['matches'][0]['score']
        
        self.assertGreater(new_score, original_score)
        self.assertTrue(mitigated[0]['matches'][0].get('mitigation_applied'))
        print(f"[INFO] Mitigation Score Boost: {original_score} -> {new_score}")

    def test_decision_engine_calibration(self):
        """Verify decision engine risk scoring."""
        # High score, low spoof -> ALLOW
        d1 = self.decision_engine.make_decision(
            face_result={'matches': [{'score': 0.9}]},
            liveness_result={'liveness_score': 0.9, 'is_live': True}
        )
        self.assertEqual(d1['decision'], 'allow')
        
        # High score, high spoof -> DENY
        d2 = self.decision_engine.make_decision(
            face_result={'matches': [{'score': 0.9}]},
            liveness_result={'liveness_score': 0.1, 'is_live': False}
        )
        self.assertEqual(d2['decision'], 'deny')
        
        # Marginal score -> REVIEW
        d3 = self.decision_engine.make_decision(
            face_result={'matches': [{'score': 0.55}]},
            liveness_result={'liveness_score': 0.8, 'is_live': True}
        )
        self.assertEqual(d3['decision'], 'review')

if __name__ == "__main__":
    unittest.main()
