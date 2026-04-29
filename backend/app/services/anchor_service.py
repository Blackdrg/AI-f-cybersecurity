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
            # Simulate external call latency
            # In real life: response = requests.post("https://btc-anchor.io/api", json={"hash": root_hash})
            
            self.last_anchored_hash = root_hash
            self.last_anchoring_time = datetime.utcnow()
            
            logger.info(f"Successfully anchored hash {root_hash} to external ledger")
            
            return {
                "success": True,
                "anchor_id": f"sim_tx_{hashlib.sha256(root_hash.encode()).hexdigest()[:16]}",
                "timestamp": self.last_anchoring_time.isoformat(),
                "ledger": "Bitcoin (Simulated)"
            }
        except Exception as e:
            logger.error(f"External anchoring failed: {str(e)}")
            return {"success": False, "error": str(e)}

anchor_service = ExternalAnchorService()
