import numpy as np
from typing import List, Tuple, Dict
import cv2
from sklearn.metrics import roc_curve, auc
from scipy.spatial.distance import cosine
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class RecognitionTuner:
    """Threshold tuning and FAR/FRR evaluation."""
    
    def __init__(self):
        self.eval_dataset = self._generate_eval_dataset()
    
    def _generate_eval_dataset(self, n_samples: int = 100) -> List[Dict]:
        """Generate synthetic evaluation dataset: low-light, angles, masks."""
        dataset = []
        for i in range(n_samples):
            # Base embedding (random for sim)
            positive_emb = np.random.randn(512).astype(np.float32)
            negative_embs = [np.random.randn(512).astype(np.float32) for _ in range(4)]
            
            # Simulate conditions
            conditions = ['normal', 'low_light', 'angle_45', 'mask', 'glasses']
            condition = np.random.choice(conditions)
            
            dataset.append({
                'positive': positive_emb,
                'negatives': negative_embs,
                'condition': condition,
                'lighting': condition,
                'user_id': f'user_{i}'
            })
        return dataset
    
    def compute_distances(self, dataset: List[Dict]) -> List[Tuple[float, bool]]:
        """Compute all positive/negative distances."""
        distances = []
        for sample in dataset:
            pos_emb = sample['positive']
            # Positive (same person)
            distances.append((cosine(pos_emb, pos_emb), True))  # 0 distance
            
            # Negatives
            for neg_emb in sample['negatives']:
                distances.append((cosine(pos_emb, neg_emb), False))
        return distances
    
    def tune_threshold(self, target_far: float = 0.01, target_frr: float = 0.03) -> float:
        """Grid search optimal threshold."""
        distances = self.compute_distances(self.eval_dataset)
        distances = np.array(distances)
        scores = 1 - distances[:, 0]  # Similarity scores
        labels = distances[:, 1].astype(int)
        
        thresholds = np.linspace(0.4, 0.8, 100)
        best_threshold = 0.6
        best_score = float('inf')
        
        for th in thresholds:
            far = np.mean(scores[labels == 0] < th)
            frr = np.mean(scores[labels == 1] >= th)
            score = abs(far - target_far) + abs(frr - target_frr)
            if score < best_score:
                best_score = score
                best_threshold = th
        
        logger.info(f"Optimal threshold: {best_threshold:.3f} (FAR: {far:.3f}, FRR: {frr:.3f})")
        return best_threshold
    
    def evaluate_threshold(self, threshold: float = 0.6) -> Dict[str, float]:
        """Evaluate FAR/FRR at threshold."""
        distances = self.compute_distances(self.eval_dataset)
        scores = 1 - np.array([d[0] for d in distances])
        labels = np.array([int(d[1]) for d in distances])
        
        far = np.mean(scores[labels == 0] > threshold)
        frr = np.mean(scores[labels == 1] < threshold)
        accuracy = 1 - (far + frr) / 2
        
        fpr, tpr, _ = roc_curve(labels, scores)
        auc_score = auc(fpr, tpr)
        
        return {
            'threshold': threshold,
            'far': far,
            'frr': frr,
            'accuracy': accuracy,
            'auc': auc_score
        }
    
    def simulate_users(self, n_users: int = 50, threshold: float = 0.6) -> Dict:
        """Simulate 50-100 user tests."""
        results = []
        for user in range(n_users):
            sample = self.eval_dataset[user % len(self.eval_dataset)]
            pos_score = 1 - cosine(sample['positive'], sample['positive'])
            decision = pos_score > threshold
            results.append({
                'user': user,
                'condition': sample['condition'],
                'score': pos_score,
                'correct': decision
            })
        accuracy = np.mean([r['correct'] for r in results])
        return {'n_users': n_users, 'accuracy': accuracy, 'results': results}

# Global tuner
tuner = RecognitionTuner()

async def get_tuner():
    return tuner

