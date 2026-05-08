"""
Uncertainty Estimator - AI Reliability Feature
Estimates predictive uncertainty using Monte Carlo dropout or ensemble variance.
"""
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class UncertaintyEstimate:
    """Uncertainty estimate for a prediction."""
    mean: float
    variance: float
    confidence_interval: tuple  # (lower, upper) at 95%
    epistemic_uncertainty: float  # Model uncertainty
    aleatoric_uncertainty: float  # Data uncertainty
    num_samples: int


class UncertaintyEstimator:
    """
    Estimates prediction uncertainty using multiple methods:
    1. Monte Carlo Dropout - Enable dropout at inference and sample multiple times
    2. Ensemble Variance - Average predictions from multiple models
    3. Embedding Space Density - Estimate based on distance to training distribution
    
    High uncertainty indicates potential unreliability.
    """
    
    def __init__(
        self,
        method: str = "mc_dropout",  # "mc_dropout" or "ensemble" or "density"
        num_samples: int = 30,
        dropout_rate: float = 0.2
    ):
        self.method = method
        self.num_samples = num_samples
        self.dropout_rate = dropout_rate
        self.ensemble_models = []
        self.covariance_estimator = None
        
    def estimate_uncertainty(
        self,
        embedding: np.ndarray,
        model=None
    ) -> UncertaintyEstimate:
        """
        Estimate uncertainty for a given embedding.
        
        Args:
            embedding: Face embedding vector
            model: Optional model for MC dropout (if not provided, uses density method)
        
        Returns:
            UncertaintyEstimate with detailed metrics
        """
        if self.method == "mc_dropout" and model is not None:
            return self._mc_dropout_uncertainty(embedding, model)
        elif self.method == "ensemble" and self.ensemble_models:
            return self._ensemble_uncertainty(embedding)
        else:
            return self._density_based_uncertainty(embedding)
    
    def _mc_dropout_uncertainty(
        self,
        embedding: np.ndarray,
        model
    ) -> UncertaintyEstimate:
        """
        Monte Carlo Dropout: Enable dropout during inference and run multiple times.
        Variance across predictions indicates epistemic uncertainty.
        """
        if not hasattr(model, 'enable_dropout'):
            # Model doesn't support dropout, fallback
            return self._density_based_uncertainty(embedding)
        
        predictions = []
        model.enable_dropout(self.dropout_rate)
        
        for _ in range(self.num_samples):
            pred = model.predict(embedding)
            predictions.append(pred)
        
        predictions = np.array(predictions)
        mean = np.mean(predictions)
        variance = np.var(predictions)
        
        # Calculate confidence interval
        lower = np.percentile(predictions, 2.5)
        upper = np.percentile(predictions, 97.5)
        
        # Epistemic = variance across models (here from MC samples)
        epistemic = variance
        # Aleatoric = expected data noise (approximated by mean abs deviation)
        aleatoric = np.mean(np.abs(predictions - mean))
        
        return UncertaintyEstimate(
            mean=float(mean),
            variance=float(variance),
            confidence_interval=(float(lower), float(upper)),
            epistemic_uncertainty=float(epistemic),
            aleatoric_uncertainty=float(aleatoric),
            num_samples=self.num_samples
        )
    
    def _ensemble_uncertainty(
        self,
        embedding: np.ndarray
    ) -> UncertaintyEstimate:
        """
        Ensemble method: Average predictions from multiple model variants.
        Requires ensemble_models to be populated.
        """
        if not self.ensemble_models:
            return self._density_based_uncertainty(embedding)
        
        predictions = []
        for model in self.ensemble_models:
            pred = model.predict(embedding)
            predictions.append(pred)
        
        predictions = np.array(predictions)
        mean = np.mean(predictions)
        variance = np.var(predictions)
        
        lower = np.percentile(predictions, 2.5)
        upper = np.percentile(predictions, 97.5)
        
        return UncertaintyEstimate(
            mean=float(mean),
            variance=float(variance),
            confidence_interval=(float(lower), float(upper)),
            epistemic_uncertainty=float(variance),
            aleatoric_uncertainty=0.0,
            num_samples=len(self.ensemble_models)
        )
    
    def _density_based_uncertainty(
        self,
        embedding: np.ndarray
    ) -> UncertaintyEstimate:
        """
        Density-based uncertainty: Estimate based on distance to training distribution.
        Sparse regions in embedding space indicate higher uncertainty.
        """
        if self.covariance_estimator is None:
            # No trained density model, return neutral estimate
            return UncertaintyEstimate(
                mean=0.5,
                variance=0.1,
                confidence_interval=(0.4, 0.6),
                epistemic_uncertainty=0.1,
                aleatoric_uncertainty=0.05,
                num_samples=1
            )
        
        # Compute Mahalanobis distance (inverse density)
        m_dist = self.covariance_estimator.mahalanobis(embedding.reshape(1, -1))[0]
        
        # Convert to uncertainty: higher distance = higher uncertainty
        # Using logistic function to map to [0,1]
        uncertainty = 1.0 / (1.0 + np.exp(-m_dist + 2.0))
        
        # Estimate confidence interval based on distance
        lower = max(0.0, 0.5 - uncertainty)
        upper = min(1.0, 0.5 + uncertainty)
        
        return UncertaintyEstimate(
            mean=0.5,
            variance=float(uncertainty ** 2),
            confidence_interval=(float(lower), float(upper)),
            epistemic_uncertainty=float(uncertainty),
            aleatoric_uncertainty=float(uncertainty * 0.5),
            num_samples=1
        )
    
    def fit_density_model(self, embeddings: np.ndarray) -> None:
        """
        Fit density model (Gaussian) to enrollment embeddings.
        Used for density-based uncertainty estimation.
        """
        from sklearn.covariance import EmpiricalCovariance
        
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(-1, 1)
        
        self.covariance_estimator = EmpiricalCovariance()
        self.covariance_estimator.fit(embeddings)
        logger.info("Fitted density model for uncertainty estimation")
    
    def add_ensemble_model(self, model) -> None:
        """Add a model to the ensemble."""
        self.ensemble_models.append(model)
        logger.info(f"Added model to ensemble, total: {len(self.ensemble_models)}")
    
    def clear_ensemble(self) -> None:
        """Clear all ensemble models."""
        self.ensemble_models = []


# Global singleton
uncertainty_estimator = UncertaintyEstimator()
