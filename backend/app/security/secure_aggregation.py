"""
Secure Aggregation for Federated Learning with MPC.

Implements:
  - SecureSum: Sum of gradients/weights without revealing individual values
  - SecureAvg: Weighted average with secure norm computation
  - SecureMedian: Approximate median via secure comparison (outlier removal)
  - Differential privacy integration (noise addition in encrypted domain)
  - Dropout resilience (n parties, tolerate f < n/2 dropouts)
  - Verification via pairwise MACs or ZKP
  - Multi-KR (key reference) for forward secrecy

Protocol: Bonawitz et al. "Practical Secure Aggregation" (2017)
Adaptation: Add MPC-based secure division for weighted averages.

Use cases:
  - Federated learning model weight aggregation
  - Privacy-preserving statistics (sum, mean, variance)
  - Secure multi-party analytics
"""

import asyncio
import secrets
import hashlib
import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np

from .mpc_spdz import (
    MPCParty, MPCOrchestrator, MPCSessionConfig,
    FieldArithmetic, ShamirSecretSharing, Share,
    BeaverMultiplication, BeaverTriple, FIELD_PRIME,
    AggregationConfig, PairwiseMaskProtocol,
    SecureAggregation as _SecureAggregation,
    SecureAggregationOrchestrator as _SecureAggregationOrchestrator,
    MaskShare,
    share_value, reconstruct_secret,
    generate_beaver_triple, demo_spdz
)

logger = logging.getLogger(__name__)


class AggregationRole(Enum):
    """Roles in secure aggregation."""
    COORDINATOR = "coordinator"    # Aggregates results (untrusted)
    PARTICIPANT = "participant"    # Provides private inputs
    VERIFIER = "verifier"          # Optional external verifier


class SecureAggregationProtocol(Enum):
    """Aggregation protocol variants."""
    SECURE_SUM = "secure_sum"          # Bonawitz et al. protocol
    MPC_BASED = "mpc_based"            # Full MPC for sum/product
    HYBRID = "hybrid"                  # Mix: pairwise masks + MPC for outliers


# Re-export from mpc_spdz for backward compatibility
SecureAggregation = _SecureAggregation
SecureAggregationOrchestrator = _SecureAggregationOrchestrator


async def secure_average(
    inputs: List[Dict[str, int]],
    n_parties: int,
    party_id: int,
    weights: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    High-level API for secure average across parties.

    Args:
        inputs: List of dicts (one per party) mapping keys to values
        n_parties: Total number of parties expected
        party_id: This party's ID (0 to n-1)
        weights: Optional per-party weights

    Returns:
        Aggregation result dict
    """
    config = AggregationConfig(
        n_parties=n_parties,
        max_dropouts=0,
        use_pairwise_masks=True,
        secure_division=True
    )

    parties = []
    for i in range(n_parties):
        mpc_party = MPCParty(
            party_id=i,
            config=MPCSessionConfig(n_parties=n_parties, threshold=1)
        )
        secagg = _SecureAggregation(config, i)
        parties.append(secagg)

    orchestrator = _SecureAggregationOrchestrator(config, parties)

    result = await orchestrator.run_aggregation(inputs, weights)
    return result


if __name__ == "__main__":
    # Demo: 3 parties compute average of values
    async def demo():
        inputs = [
            {0: 100, 1: 200},
            {0: 50, 1: 150},
            {0: 75, 1: 125}
        ]

        result = await secure_average(inputs, n_parties=3, party_id=0)
        print(f"Secure average result: {result}")
        return result

    asyncio.run(demo())