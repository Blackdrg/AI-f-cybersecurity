import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib
import asyncio
import random


try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None


@dataclass
class ClientUpdate:
    client_id: str
    round_id: str
    gradients: Dict[str, np.ndarray]
    num_samples: int
    timestamp: str
    model_version: str


@dataclass
class RoundConfig:
    round_id: str
    min_clients: int = 3
    max_clients: int = 100
    timeout_seconds: int = 300
    aggregation_method: str = "fedavg"  # fedavg, fedprox
    differential_privacy: bool = True
    noise_multiplier: float = 1.0
    max_grad_norm: float = 1.0


class SecureAggregation:
    """Secure aggregation for federated learning."""
    
    def __init__(self, noise_multiplier: float = 1.0):
        self.noise_multiplier = noise_multiplier
        
    def add_noise(self, gradients: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Add Gaussian noise for differential privacy."""
        if not TORCH_AVAILABLE:
            return gradients
        
        noisy_grads = {}
        
        for name, grad in gradients.items():
            # Calculate sensitivity
            sens = np.linalg.norm(grad) if grad.size > 0 else 0
            
            if sens > 0:
                # Scale noise to privacy budget
                sigma = self.noise_multiplier * sens
                noise = np.random.normal(0, sigma, grad.shape).astype(grad.dtype)
                noisy_grads[name] = grad + noise
            else:
                noisy_grads[name] = grad
        
        return noisy_grads
    
    def clip_gradients(
        self,
        gradients: Dict[str, np.ndarray],
        max_norm: float
    ) -> Dict[str, np.ndarray]:
        """Clip gradients by norm."""
        clipped = {}
        
        for name, grad in gradients.items():
            norm = np.linalg.norm(grad) if grad.size > 0 else 0
            
            if norm > max_norm:
                clipped[name] = grad * (max_norm / norm)
            else:
                clipped[name] = grad
        
        return clipped
    
    def secure_average(
        self,
        updates: List[ClientUpdate],
        config: RoundConfig
    ) -> Dict[str, np.ndarray]:
        """Compute secure aggregated gradients."""
        if not updates:
            return {}
        
        # Clip first
        clipped_updates = []
        for update in updates:
            clipped = self.clip_gradients(
                update.gradients,
                config.max_grad_norm
            )
            clipped_updates.append((update.num_samples, clipped))
        
        # Weighted average by sample count
        total_samples = sum(u.num_samples for u in updates)
        
        aggregated = {}
        param_names = clipped_updates[0][1].keys()
        
        for name in param_names:
            weighted_sum = np.zeros_like(
                clipped_updates[0][1][name],
                dtype=np.float32
            )
            
            for num_samples, grads in clipped_updates:
                weight = num_samples / total_samples
                weighted_sum += weight * grads[name]
            
            aggregated[name] = weighted_sum
        
        # Add noise for differential privacy
        if config.differential_privacy:
            aggregated = self.add_noise(aggregated)
        
        return aggregated


class FederatedClient:
    """Federated learning client (runs on edge devices)."""
    
    def __init__(
        self,
        client_id: str,
        model_path: str = "/app/models"
    ):
        self.client_id = client_id
        self.model_path = model_path
        self.local_model = None
        self.model_version = "v1.0"
        
    def load_model(self, version: str) -> None:
        """Load model for local training."""
        self.model_version = version
        # Would load model weights here
        pass
    
    def train_local(
        self,
        data: List[np.ndarray],
        labels: List[int],
        epochs: int = 5
    ) -> Dict[str, np.ndarray]:
        """Train model locally on edge data."""
        if not TORCH_AVAILABLE:
            return {}
        
        # Placeholder - would train actual model
        # In production, this runs on edge device
        
        # Generate mock gradients for demo
        gradients = {
            f"layer_{i}": np.random.randn(512, 512).astype(np.float32)
            for i in range(4)
        }
        
        return gradients
    
    def compute_gradients(
        self,
        data: List[np.ndarray],
        labels: List[int],
        global_model: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """Compute gradients against global model."""
        # Placeholder - would compute actual gradients
        gradients = {
            f"layer_{i}": np.random.randn(512, 512).astype(np.float32)
            for i in range(4)
        }
        
        return gradients
    
    def get_model_update(
        self,
        round_config: RoundConfig
    ) -> ClientUpdate:
        """Get model update for current round."""
        # Would load cached gradients from training
        gradients = {
            f"layer_{i}": np.random.randn(512, 512).astype(np.float32)
            for i in range(4)
        }
        
        return ClientUpdate(
            client_id=self.client_id,
            round_id=round_config.round_id,
            gradients=gradients,
            num_samples=random.randint(10, 1000),
            timestamp=datetime.utcnow().isoformat(),
            model_version=self.model_version
        )


class FederatedServer:
    """Federated learning server orchestration."""
    
    def __init__(self):
        self.current_round = 0
        self.global_model: Dict[str, np.ndarray] = {}
        self.client_updates: Dict[str, List[ClientUpdate]] = {}
        self.secure_agg = SecureAggregation()
        self.round_history: List[Dict] = []
        
    def start_round(self, config: RoundConfig) -> Dict:
        """Start a new federated round."""
        self.current_round += 1
        self.client_updates[config.round_id] = []
        
        return {
            "round_id": config.round_id,
            "round_number": self.current_round,
            "min_clients": config.min_clients,
            "timeout": config.timeout_seconds,
            "global_model_version": f"v{self.current_round}.0"
        }
    
    def receive_update(
        self,
        update: ClientUpdate
    ) -> Dict:
        """Receive client update."""
        round_updates = self.client_updates.get(update.round_id, [])
        round_updates.append(update)
        self.client_updates[update.round_id] = round_updates
        
        return {
            "status": "received",
            "total_updates": len(round_updates)
        }
    
    def aggregate_round(
        self,
        round_id: str,
        config: RoundConfig
    ) -> Optional[Dict]:
        """Aggregate updates and update global model."""
        updates = self.client_updates.get(round_id, [])
        
        if len(updates) < config.min_clients:
            return None
        
        # Secure aggregation
        new_model = self.secure_agg.secure_average(updates, config)
        
        # Update global model
        if config.aggregation_method == "fedavg":
            # Federated averaging
            self.global_model = new_model
        
        # Record round
        round_result = {
            "round_id": round_id,
            "num_clients": len(updates),
            "timestamp": datetime.utcnow().isoformat(),
            "avg_samples_per_client": np.mean([u.num_samples for u in updates])
        }
        self.round_history.append(round_result)
        
        # Clean up
        del self.client_updates[round_id]
        
        return {
            "status": "completed",
            "round_id": round_id,
            "new_model_version": f"v{self.current_round}.0",
            "clients_participated": len(updates)
        }
    
    def get_global_model(self) -> Dict[str, np.ndarray]:
        """Get current global model."""
        return self.global_model
    
    def export_model_for_client(
        self,
        client_id: str,
        format: str = "pytorch"
    ) -> bytes:
        """Export model for client download."""
        # Would serialize model
        return b"model_data"
    
    def get_round_history(
        self,
        limit: int = 10
    ) -> List[Dict]:
        """Get training history."""
        return self.round_history[-limit:]


class ClientOrchestrator:
    """Orchestrates communication with federated clients."""
    
    def __init__(self, server: FederatedServer):
        self.server = server
        self.registered_clients: Dict[str, Dict] = {}
        self.client_tasks: Dict[str, asyncio.Task] = {}
        
    def register_client(
        self,
        client_id: str,
        capabilities: Dict
    ) -> bool:
        """Register a client for federated learning."""
        self.registered_clients[client_id] = {
            "registered_at": datetime.utcnow().isoformat(),
            "capabilities": capabilities,
            "status": "idle"
        }
        return True
    
    def select_clients(
        self,
        round_id: str,
        config: RoundConfig
    ) -> List[str]:
        """Select clients for a round."""
        # Select based on capabilities and random sampling
        available = [
            cid for cid, c in self.registered_clients.items()
            if c["status"] == "idle"
        ]
        
        selected = random.sample(
            available,
            min(config.max_clients, len(available))
        )
        
        # Update status
        for cid in selected:
            self.registered_clients[cid]["status"] = "selected"
        
        return selected
    
    async def run_round(
        self,
        round_id: str,
        config: RoundConfig
    ) -> Dict:
        """Run a federated round across selected clients."""
        selected = self.select_clients(round_id, config)
        
        # Start round on server
        self.server.start_round(config)
        
        # Simulate client updates (in production, this would be async RPC)
        for client_id in selected:
            update = ClientUpdate(
                client_id=client_id,
                round_id=round_id,
                gradients={f"layer_{i}": np.random.randn(512, 512).astype(np.float32) for i in range(4)},
                num_samples=random.randint(10, 1000),
                timestamp=datetime.utcnow().isoformat(),
                model_version="v1.0"
            )
            self.server.receive_update(update)
        
        # Aggregate
        result = self.server.aggregate_round(round_id, config)
        
        # Reset client status
        for cid in selected:
            self.registered_clients[cid]["status"] = "idle"
        
        return result or {"status": "insufficient_clients"}


# Global instances
federated_server = FederatedServer()
client_orchestrator = ClientOrchestrator(federated_server)


def create_federated_client(client_id: str) -> FederatedClient:
    """Create a federated learning client."""
    return FederatedClient(client_id)