import re
import logging
from typing import List, Dict, Any, Tuple
import hashlib

logger = logging.getLogger(__name__)

class AIFirewall:
    """
    Firewall for AI inputs and outputs to prevent injection, jailbreaking, and PII leakage.
    """
    
    # Common jailbreak patterns
    JAILBREAK_PATTERNS = [
        r"ignore all previous instructions",
        r"system override",
        r"dan mode",
        r"do anything now",
        r"jailbreak",
        r"you are now a hacker",
        r"disregard safety guidelines",
        r"forget everything you were told",
        r"act as a malicious",
        r"write code to exploit"
    ]
    
    # PII patterns (simple regex for demonstration)
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "ssn": r"\d{3}-\d{2}-\d{4}",
        "credit_card": r"\d{4}-\d{4}-\d{4}-\d{4}",
        "phone": r"\+?\d{1,3}[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
    }

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def validate_input(self, messages: List[Dict[str, str]]) -> Tuple[bool, str]:
        """Validate input messages for injection and jailbreak attempts."""
        if not self.enabled:
            return True, ""

        for msg in messages:
            content = msg.get("content", "").lower()
            
            # 1. Check for jailbreak patterns
            for pattern in self.JAILBREAK_PATTERNS:
                if re.search(pattern, content):
                    logger.warning(f"Jailbreak attempt detected: '{pattern}'")
                    return False, f"Malicious input detected (Policy: Jailbreak)"

            # 2. Check for suspicious length (DDoS-like)
            if len(content) > 10000:
                logger.warning("Input exceeds safe length limit")
                return False, "Input exceeds safe length limit"

        return True, ""

    def sanitize_output(self, response: str) -> str:
        """Filter PII from AI responses."""
        if not self.enabled:
            return response

        sanitized = response
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, sanitized)
            if matches:
                logger.warning(f"PII leak detected in AI response: {pii_type}")
                sanitized = re.sub(pattern, f"[REDACTED {pii_type.upper()}]", sanitized)

        return sanitized

    def generate_fingerprint(self, model_name: str, version: str) -> str:
        """Generate a fingerprint for the model to ensure integrity."""
        return hashlib.sha256(f"{model_name}|{version}|ai-f-secure-key".encode()).hexdigest()

ai_firewall = AIFirewall()
