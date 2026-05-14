import asyncio
import os
import sys
import uuid
import json
from datetime import datetime
from pathlib import Path

# Add backend to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.db_client import get_db

async def simulate_incident_response():
    """
    Simulates security incidents and verifies the system's response logic.
    """
    print("=" * 60)
    print("INCIDENT RESPONSE SIMULATION TEST")
    print("=" * 60)
    
    db = get_db()
    
    # 1. Simulate Brute Force Attempt
    print("\n[SCENARIO 1] Simulating MFA Brute Force...")
    user_id = "test-user-99"
    for i in range(6):
        await db.log_mfa_attempt(user_id, 'totp', False, "192.168.1.100")
        print(f"  Attempt {i+1} failed...")
    
    # Check if an incident was created
    incidents = await db.fetch("SELECT * FROM incidents WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1", user_id)
    if incidents:
        print(f"[SUCCESS] Incident detected: {incidents[0]['incident_type']} for user {user_id}")
    else:
        print("[FAILURE] No incident created for brute force simulation.")

    # 2. Simulate Audit Chain Tampering (Logical)
    print("\n[SCENARIO 2] Simulating Audit Chain Tampering...")
    # We'll insert a fake log entry without a valid hash chain
    async with db.pool.acquire() as conn:
        tampered_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO audit_log (event_id, event_type, person_id, details, previous_hash, hash)
            VALUES ($1, 'UNAUTHORIZED_TAMPER', NULL, '{"evil": true}', 'invalid_prev_hash', 'invalid_hash')
        """, tampered_id)
        print(f"  Injected tampered log entry: {tampered_id}")
        
        # Trigger the verification task manually (logic from maintenance_tasks)
        broken = await db.verify_audit_chain()
        if any(b['event_id'] == tampered_id for b in broken):
            print(f"[SUCCESS] Tampered entry detected by verification logic.")
            
            # Simulate alert dispatch
            # In a real test, we'd check Redis or a mock Slack/PagerDuty endpoint
            print("  [INFO] Critical alert 'AUDIT_CHAIN_BROKEN' would be dispatched.")
        else:
            print("[FAILURE] Tampered entry NOT detected.")
            
        # Cleanup
        await conn.execute("DELETE FROM audit_log WHERE event_id = $1", tampered_id)
        print("  Cleaned up tampered entry.")

    # 3. Simulate Data Leak Attempt (Rate Limit Trigger)
    print("\n[SCENARIO 3] Simulating High-Volume Data Export (Leak Attempt)...")
    org_id = "org-test-1"
    # Logic: Trigger a usage limit breach
    # We simulate 1000 calls in a second (logic would be in UsageLimiter middleware)
    # Here we just verify the counter and alert trigger
    await db.increment_usage(org_id, "export_api", count=1000)
    
    alerts = await db.fetch("SELECT * FROM alerts WHERE org_id = $1 AND alert_type = 'USAGE_LIMIT_EXCEEDED' ORDER BY created_at DESC LIMIT 1", org_id)
    if alerts:
        print(f"[SUCCESS] Usage alert triggered: {alerts[0]['details']}")
    else:
        print("[WARNING] Usage alert not triggered. Check UsageLimiter thresholds.")

    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(simulate_incident_response())
    except Exception as e:
        print(f"[CRITICAL] Simulation failed: {e}")
