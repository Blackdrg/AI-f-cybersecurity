"""
Differential Privacy Engine for Biometric Data Protection.

Provides mechanisms to add calibrated Gaussian noise to embeddings
to achieve (ε, δ)-differential privacy.
"""

import numpy as np
from typing import Union, Optional
import os


def add_gaussian_noise(
    embedding: np.ndarray,
    epsilon: float = 1.0,
    delta: float = 1e-5,
    sensitivity: float = 1.0,
    normalize_after: bool = True
) -> np.ndarray:
    """
    Add Gaussian noise to an embedding vector for differential privacy.

    Uses the Gaussian mechanism: N(0, σ^2 I) where
    σ = sensitivity * sqrt(2 * ln(1.25 / δ)) / ε.

    Args:
        embedding: Input embedding vector (1-D numpy array).
        epsilon: Privacy budget (ε). Smaller = more privacy.
        delta: Privacy parameter (δ). Typically small (e.g., 1e-5).
        sensitivity: L2 sensitivity of the function. Default 1.0
                     (assuming embeddings are L2-normalized to unit norm).
        normalize_after: If True, re-normalize the noisy embedding to unit L2 norm.

    Returns:
        Noisy embedding (same dtype and shape as input).
    """
    if embedding is None or embedding.size == 0:
        return embedding

    # Compute noise scale (sigma)
    sigma = sensitivity * np.sqrt(2 * np.log(1.25 / delta)) / epsilon

    # Generate Gaussian noise with same dtype as embedding
    noise = np.random.normal(0, sigma, embedding.shape).astype(embedding.dtype)

    noisy_embedding = embedding + noise

    if normalize_after:
        norm = np.linalg.norm(noisy_embedding)
        if norm > 0:
            noisy_embedding = (noisy_embedding / norm).astype(embedding.dtype)
        else:
            noisy_embedding = noisy_embedding.astype(embedding.dtype)
    else:
        noisy_embedding = noisy_embedding.astype(embedding.dtype)

    return noisy_embedding


class DifferentialPrivacyEngine:
    """
    Engine for managing differential privacy parameters and application.
    """

    def __init__(
        self,
        default_epsilon: float = 1.0,
        default_delta: float = 1e-5,
        sensitivity: float = 1.0
    ):
        self.default_epsilon = default_epsilon
        self.default_delta = default_delta
        self.sensitivity = sensitivity

    def add_noise(
        self,
        embedding: np.ndarray,
        epsilon: Optional[float] = None,
        delta: Optional[float] = None,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Add DP noise using configured or provided parameters.
        """
        eps = epsilon if epsilon is not None else self.default_epsilon
        dlt = delta if delta is not None else self.default_delta
        return add_gaussian_noise(
            embedding,
            epsilon=eps,
            delta=dlt,
            sensitivity=self.sensitivity,
            normalize_after=normalize
        )


# Global instance (singleton) for convenience
dp_engine = DifferentialPrivacyEngine(
    default_epsilon=float(os.getenv("DP_EPSILON", 1.0)),
    default_delta=float(os.getenv("DP_DELTA", 1e-5)),
    sensitivity=float(os.getenv("DP_SENSITIVITY", 1.0))
)
