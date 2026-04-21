from fastapi import APIRouter, HTTPException, Depends
from ..db.db_client import get_db
from ..schemas import FederatedUpdate
from ..security import require_admin
import uuid
import json

router = APIRouter()


@router.post("/federated/update")
async def receive_federated_update(update: FederatedUpdate, user: dict = Depends(require_admin)):
    db = await get_db()
    update_id = str(uuid.uuid4())
    
    async with db.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO federated_updates (update_id, device_id, model_gradients, num_samples, timestamp)
            VALUES ($1, $2, $3, $4, $5)
        """, update_id, update.device_id, json.dumps(update.model_gradients), update.num_samples, update.timestamp)

        # Aggregate gradients (simple average for POC)
        total = await conn.fetchval("SELECT COUNT(*) FROM federated_updates WHERE device_id = $1", update.device_id)
        if total >= 5:  # Aggregate every 5 updates
            await aggregate_gradients(conn, update.device_id)

    return {"message": "Federated update received", "update_id": update_id}


async def aggregate_gradients(conn, device_id):
    updates = await conn.fetch("SELECT model_gradients, num_samples FROM federated_updates WHERE device_id = $1 ORDER BY timestamp DESC LIMIT 5", device_id)
    if not updates:
        return
    # Simple aggregation: average gradients
    aggregated = {}
    total_samples = sum(u['num_samples'] for u in updates)
    for key in updates[0]['model_gradients'].keys():
        aggregated[key] = sum(u['model_gradients'][key] * u['num_samples']
                              for u in updates) / total_samples

    # Update central model (placeholder: log aggregated gradients)
    await conn.execute("""
        INSERT INTO audit_log (action, details)
        VALUES ('federated_aggregate', $1)
    """, {'device_id': device_id, 'aggregated_gradients': aggregated})

    # Clear old updates
    await conn.execute("DELETE FROM federated_updates WHERE device_id = $1", device_id)
