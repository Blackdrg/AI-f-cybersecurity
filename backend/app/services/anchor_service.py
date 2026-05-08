import hashlib
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ExternalAnchorService:
    """
    Simulates external hash anchoring to a public ledger (e.g., Bitcoin/Ethereum).
    In a real production environment, this would call a blockchain API or a 
    trusted timestamping service.
    """
    
    def __init__(self):
        self.last_anchored_hash = None
        self.last_anchoring_time = None
    
    async def anchor_root_hash(self, root_hash: str):
        """
        Anchor the current chain root hash to an external source.
        """
        try:
            # Check for configured anchoring service URL
            anchor_url = os.getenv("ANCHOR_SERVICE_URL")
            if anchor_url:
                # Use external service
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        anchor_url,
                        json={"hash": root_hash, "timestamp": datetime.utcnow().isoformat()},
                        timeout=10.0
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return {
                        "success": True,
                        "anchor_id": data.get("tx_id") or data.get("anchor_id", "unknown"),
                        "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
                        "ledger": data.get("ledger", "custom")
                    }
            else:
                # Simulate external call latency
                logger.info(f"Simulated anchoring of hash {root_hash} (no ANCHOR_SERVICE_URL configured)")
                return {
                    "success": True,
                    "anchor_id": f"sim_tx_{hashlib.sha256(root_hash.encode()).hexdigest()[:16]}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "ledger": "Simulated"
                }
        except Exception as e:
            logger.error(f"External anchoring failed: {str(e)}")
            return {"success": False, "error": str(e)}

anchor_service = ExternalAnchorService()
