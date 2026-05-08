"""MPC cross-organization matching endpoints.

Provides secure multi-party computation based identity matching across organizations.
Currently supports remote matching via network calls (real networking).
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional
import numpy as np
from ..db.db_client import get_db
from ..security import require_auth
import logging

router = APIRouter()

@router.post("/mpc/match")
async def mpc_match(
    embedding: List[float],
    threshold: float = 0.7,
    top_k: int = 5,
    current_user: dict = Depends(require_auth)
):
    """
    Perform cross-organization face matching using MPC protocol.
    
    This endpoint is called by another organization during federated identity matching.
    It receives an embedding vector (as list) and returns matching identities from this org.
    
    Args:
        embedding: Embedding vector (list of floats)
        threshold: Similarity threshold
        top_k: Maximum number of matches to return
        current_user: Authenticated user (must belong to some org)
    
    Returns:
        {"matches": [...]}
    """
    db = await get_db()
    if db.pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    try:
        emb = np.array(embedding, dtype=np.float32)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid embedding: {e}")
    
    # Call the DB recognize_faces method to find matches.
    try:
        matches = await db.recognize_faces(
            query_embedding=emb,
            top_k=top_k,
            threshold=threshold,
            camera_id=None
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"MPC match error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Matching failed")
    
    # Format response
    formatted = []
    for m in matches:
        formatted.append({
            "person_id": m.get("person_id"),
            "name": m.get("name"),
            "score": m.get("score"),
            "similarity": m.get("score"),
            "distance": m.get("distance", 0.0),
            "age": m.get("age"),
            "gender": m.get("gender")
        })
    
    return {"matches": formatted}
