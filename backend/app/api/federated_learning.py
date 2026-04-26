from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
import uuid
import datetime
import numpy as np
from ..federated_learning import (
    federated_server,
    client_orchestrator,
    create_federated_client,
    RoundConfig
)
from ..schemas import StandardResponse
from ..security import require_auth, require_admin

router = APIRouter(prefix="/federated", tags=["federated_learning"])

@router.get("/status")
async def get_federated_status(user: dict = Depends(require_auth)):
    """Get current federated learning status."""
    return {
        "success": True,
        "data": {
            "current_round": federated_server.current_round,
            "global_model_version": f"v{federated_server.current_round}.0" if federated_server.current_round > 0 else None,
            "registered_clients": len(client_orchestrator.registered_clients),
            "pending_updates": {rid: len(u) for rid, u in federated_server.client_updates.items()},
            "round_history": federated_server.get_round_history(limit=10)
        },
        "error": None
    }

@router.post("/register")
async def register_client(
    request: Dict[str, Any],
    user: dict = Depends(require_admin)
):
    """Register a federated learning client."""
    client_id = request.get("client_id")
    capabilities = request.get("capabilities", {})
    
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")
    
    success = client_orchestrator.register_client(client_id, capabilities)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register client")
    
    return {
        "success": True,
        "data": {
            "client_id": client_id,
            "registered": True,
            "status": "idle"
        },
        "error": None
    }

@router.post("/start_round")
async def start_federated_round(
    config: Optional[Dict[str, Any]] = {},
    user: dict = Depends(require_admin)
):
    """Start a new federated learning round."""
    round_config = RoundConfig(
        round_id=f"round_{uuid.uuid4().hex[:8]}",
        min_clients=config.get("min_clients", 3),
        max_clients=config.get("max_clients", 100),
        timeout_seconds=config.get("timeout_seconds", 300),
        aggregation_method=config.get("aggregation_method", "fedavg"),
        differential_privacy=config.get("differential_privacy", True),
        noise_multiplier=config.get("noise_multiplier", 1.0),
        max_grad_norm=config.get("max_grad_norm", 1.0)
    )
    
    result = await client_orchestrator.run_round(round_config.round_id, round_config)
    
    return {
        "success": True,
        "data": result,
        "error": None
    }

@router.get("/global_model")
async def get_global_model(user: dict = Depends(require_auth)):
    """Get current global model (metadata)."""
    model = federated_server.get_global_model()
    return {
        "success": True,
        "data": {
            "model_version": f"v{federated_server.current_round}.0" if federated_server.current_round > 0 else "v0.0",
            "num_parameters": len(model),
            "parameters": {k: str(v.shape) for k, v in model.items()} if model else {}
        },
        "error": None
    }

@router.post("/client/update")
async def submit_client_update(
    update: Dict[str, Any],
    user: dict = Depends(require_admin)
):
    """Submit federated learning update from a client."""
    from ...federated_learning import ClientUpdate
    
    # Convert gradient lists to numpy arrays for internal processing
    raw_gradients = update.get("gradients", {})
    gradients = {k: np.array(v) for k, v in raw_gradients.items()}
    
    client_update = ClientUpdate(
        client_id=update.get("client_id", "unknown"),
        round_id=update.get("round_id", "default"),
        gradients=gradients,
        num_samples=update.get("num_samples", 1),
        timestamp=update.get("timestamp", datetime.datetime.utcnow().isoformat()),
        model_version=update.get("model_version", "v1.0")
    )
    
    result = federated_server.receive_update(client_update)
    return {
        "success": True,
        "data": result,
        "error": None
    }

@router.get("/clients")
async def list_clients(user: dict = Depends(require_auth)):
    """List registered federated clients."""
    return {
        "success": True,
        "data": [
            {
                "client_id": cid,
                **info
            }
            for cid, info in client_orchestrator.registered_clients.items()
        ],
        "error": None
    }

@router.post("/aggregate/{round_id}")
async def force_aggregate(round_id: str, user: dict = Depends(require_admin)):
    """Force aggregation for a round."""
    config = RoundConfig(round_id=round_id)
    result = federated_server.aggregate_round(round_id, config)
    if result is None:
        raise HTTPException(status_code=400, detail="Insufficient updates to aggregate")
    return {
        "success": True,
        "data": result,
        "error": None
    }
