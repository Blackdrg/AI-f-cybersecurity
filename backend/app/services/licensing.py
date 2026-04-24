import hmac
import hashlib
import json
import base64
from datetime import datetime
import os

class LicensingSystem:
    """
    On-prem license validation system with feature flags.
    """
    def __init__(self):
        self.secret = os.getenv("LICENSE_SIGNING_KEY", "license_secret")

    def validate_license(self, license_key: str) -> Dict:
        """
        Validates a signed license key.
        Format: base64(json_data).signature
        """
        try:
            parts = license_key.split('.')
            if len(parts) != 2:
                return {"valid": False, "error": "Invalid format"}
            
            data_b64, signature = parts
            data_json = base64.b64decode(data_b64).decode()
            
            # Verify signature
            expected_sig = hmac.new(self.secret.encode(), data_json.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected_sig):
                return {"valid": False, "error": "Invalid signature"}
            
            license_data = json.loads(data_json)
            
            # Check expiration
            expiry = datetime.fromisoformat(license_data["expires_at"])
            if datetime.utcnow() > expiry:
                return {"valid": False, "error": "License expired"}
            
            return {"valid": True, "data": license_data}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_feature_flags(self, license_data: Dict) -> Dict:
        """Returns enabled features based on license."""
        return license_data.get("features", {
            "max_identities": 100,
            "max_streams": 1,
            "enterprise_features": False
        })

license_system = LicensingSystem()
