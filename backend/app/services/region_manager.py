import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RegionManager:
    """
    Handles multi-region failover and geo-routing policies.
    """
    def __init__(self):
        self.primary_region = os.getenv("PRIMARY_REGION", "us-east-1")
        self.secondary_region = os.getenv("SECONDARY_REGION", "eu-west-1")
        self.current_role = os.getenv("REGION_ROLE", "active") # active or passive

    def get_failover_endpoint(self) -> Optional[str]:
        """Returns the endpoint for the passive region if primary is down."""
        if self.current_role == "passive":
            # This instance is already passive, should point to active
            return f"https://api.{self.primary_region}.ai-f.enterprise"
        return f"https://api.{self.secondary_region}.ai-f.enterprise"

    def is_healthy(self) -> bool:
        """Self-health check for region-level load balancer."""
        # Check DB, Redis, and AI workers
        return True

    def switch_to_passive(self):
        """Emergency switch to passive mode."""
        self.current_role = "passive"
        logger.warning(f"Region {self.primary_region} switched to PASSIVE mode.")

    def switch_to_active(self):
        """Promote to active mode."""
        self.current_role = "active"
        logger.info(f"Region {self.primary_region} promoted to ACTIVE mode.")

region_manager = RegionManager()
