from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import StandardResponse
from ..db.db_client import get_db
import httpx
import logging
from ..security import require_org_admin

router = APIRouter()

@router.post("/{org_id}/rules")
async def create_rule(org_id: str, rule: dict, current_user=Depends(require_org_admin)):
    """Create a new alert rule for the organization."""
    db = await get_db()
    # In a real implementation, we would validate the rule structure
    rule_id = await db.pool.fetchval("""
        INSERT INTO alert_rules (org_id, name, condition, actions)
        VALUES ($1, $2, $3, $4)
        RETURNING rule_id
    """, org_id, rule.get('name'), rule.get('condition'), rule.get('actions'))
    return {"rule_id": str(rule_id)}

@router.get("/{org_id}/alerts")
async def list_alerts(org_id: str, current_user=Depends(require_org_admin)):
    """List fired alerts for the organization."""
    db = await get_db()
    alerts = await db.pool.fetch("""
        SELECT a.*, r.name as rule_name, e.timestamp as event_timestamp
        FROM alerts a
        JOIN alert_rules r ON a.rule_id = r.rule_id
        JOIN recognition_events e ON a.event_id = e.event_id
        WHERE r.org_id = $1
        ORDER BY a.created_at DESC
    """, org_id)
    return [dict(a) for a in alerts]

async def process_event_rules(event_id: str, org_id: str, person_id: str, camera_id: str):
    """Background task to check rules against a new recognition event."""
    db = await get_db()
    rules = await db.pool.fetch("SELECT * FROM alert_rules WHERE org_id = $1 AND is_active = TRUE", org_id)
    
    for rule in rules:
        condition = rule['condition']
        # Simple example logic: if person is unknown and rule says alert on unknown
        is_unknown = person_id is None
        if condition.get('person_type') == 'unknown' and is_unknown:
            # Fire alert
            await db.pool.execute("""
                INSERT INTO alerts (rule_id, event_id)
                VALUES ($1, $2)
            """, rule['rule_id'], event_id)
            
            # Execute actions (webhooks, email placeholders)
            for action in actions:
                if action['type'] == 'webhook':
                    try:
                        async with httpx.AsyncClient() as client:
                            await client.post(action['url'], json={
                                "alert": rule['name'],
                                "event_id": str(event_id),
                                "timestamp": str(datetime.utcnow())
                            }, timeout=5.0)
                    except Exception as e:
                        logging.error(f"Failed to send webhook for rule {rule['rule_id']}: {e}")
