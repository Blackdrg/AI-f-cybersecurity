import asyncio
import hashlib
import hmac
import json
import os
import sys
from typing import List, Optional
from pathlib import Path

# Add backend to sys.path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.db.db_client import get_db

async def verify_audit_chain():
    """
    Verifies the entire audit log chain.
    Each entry's hash must include the previous entry's hash.
    """
    print("=" * 60)
    print("AUDIT CHAIN INTEGRITY VERIFICATION")
    print("=" * 60)
    
    db = await get_db()
    
    # Secret key for HMAC (must match the one used during logging)
    # In a real system, this might be in a KMS or Vault
    audit_secret = os.getenv("AUDIT_CHAIN_SECRET", "default-audit-secret-change-me")
    
    async with db.pool.acquire() as conn:
        # Get all audit logs ordered by ID
        logs = await conn.fetch("SELECT id, event_type, person_id, details, timestamp, previous_hash, hash FROM audit_log ORDER BY id ASC")
        
        if not logs:
            print("[INFO] No audit logs found to verify.")
            return True
        
        print(f"[INFO] Found {len(logs)} audit log entries. Starting verification...")
        
        prev_hash = "0" * 64  # Genesis hash
        corrupted_ids = []
        
        for log in logs:
            log_id = log['id']
            stored_prev_hash = log['previous_hash']
            stored_hash = log['hash']
            
            # 1. Verify previous hash link
            if stored_prev_hash != prev_hash:
                print(f"[ERROR] Chain break at ID {log_id}: expected prev_hash {prev_hash[:10]}..., got {stored_prev_hash[:10]}...")
                corrupted_ids.append(log_id)
                prev_hash = stored_hash # Try to continue
                continue
            
            # 2. Recompute hash
            # We must use exactly the same serialization as db_client.py
            payload = {
                "id": log_id,
                "event_type": log['event_type'],
                "person_id": str(log['person_id']) if log['person_id'] else None,
                "details": log['details'], # Already a dict/JSON
                "timestamp": str(log['timestamp']),
                "previous_hash": stored_prev_hash
            }
            
            payload_str = json.dumps(payload, sort_keys=True)
            computed_hash = hmac.new(
                audit_secret.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # 3. Compare hashes
            if computed_hash != stored_hash:
                print(f"[ERROR] Hash mismatch at ID {log_id}!")
                print(f"  Computed: {computed_hash[:10]}...")
                print(f"  Stored:   {stored_hash[:10]}...")
                corrupted_ids.append(log_id)
            
            prev_hash = stored_hash
            
        print("-" * 60)
        if not corrupted_ids:
            print("[SUCCESS] Audit chain integrity verified. 100% consistent.")
            return True
        else:
            print(f"[FAILURE] Found {len(corrupted_ids)} corrupted or broken links in the audit chain.")
            print(f"Corrupted IDs: {corrupted_ids}")
            return False

if __name__ == "__main__":
    try:
        success = asyncio.run(verify_audit_chain())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[CRITICAL] Verification script failed: {e}")
        sys.exit(1)
