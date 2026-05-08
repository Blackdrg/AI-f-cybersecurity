"""Enterprise Licensing System for AI-f"""

import uuid
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum

class LicenseType(Enum):
    TRIAL = "trial"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"

class LicenseStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"

class LicenseManager:
    """Enterprise license management system."""
    
    def __init__(self):
        self.licenses = {}  # license_key -> license_data
        self.activations = {}  # license_key -> list of activation_ids
    
    def create_license(self, license_type: LicenseType, duration_days: int = 365, 
                       max_activations: int = 1, metadata: Dict = None) -> str:
        """Create a new license key."""
        license_key = self._generate_license_key()
        
        self.licenses[license_key] = {
            'type': license_type.value,
            'status': LicenseStatus.ACTIVE.value,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=duration_days)).isoformat(),
            'max_activations': max_activations,
            'activations': [],
            'metadata': metadata or {}
        }
        
        self.activations[license_key] = []
        
        return license_key
    
    def _generate_license_key(self) -> str:
        """Generate a secure license key."""
        raw = f"{uuid.uuid4()}{datetime.utcnow().timestamp()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32].upper()
    
    def validate_license(self, license_key: str) -> Dict:
        """Validate a license key."""
        if license_key not in self.licenses:
            return {'valid': False, 'error': 'Invalid license key'}
        
        license_data = self.licenses[license_key]
        
        # Check expiration
        expires_at = datetime.fromisoformat(license_data['expires_at'])
        if datetime.utcnow() > expires_at:
            license_data['status'] = LicenseStatus.EXPIRED.value
            return {'valid': False, 'error': 'License expired'}
        
        # Check status
        if license_data['status'] != LicenseStatus.ACTIVE.value:
            return {'valid': False, 'error': f"License {license_data['status']}"}
        
        return {
            'valid': True,
            'type': license_data['type'],
            'expires_at': license_data['expires_at'],
            'activations_used': len(license_data['activations']),
            'activations_remaining': license_data['max_activations'] - len(license_data['activations'])
        }
    
    def activate_license(self, license_key: str, machine_id: str) -> Dict:
        """Activate a license on a machine."""
        validation = self.validate_license(license_key)
        if not validation['valid']:
            return validation
        
        license_data = self.licenses[license_key]
        
        # Check activation count
        if len(license_data['activations']) >= license_data['max_activations']:
            return {'valid': False, 'error': 'Maximum activations reached'}
        
        # Check if already activated
        for activation in license_data['activations']:
            if activation['machine_id'] == machine_id:
                return {
                    'valid': True,
                    'activation_id': activation['id'],
                    'message': 'Already activated'
                }
        
        # Create activation
        activation_id = str(uuid.uuid4())
        activation = {
            'id': activation_id,
            'machine_id': machine_id,
            'activated_at': datetime.utcnow().isoformat(),
            'last_check': datetime.utcnow().isoformat()
        }
        
        license_data['activations'].append(activation)
        
        return {
            'valid': True,
            'activation_id': activation_id,
            'license_type': license_data['type']
        }
    
    def check_activation(self, license_key: str, activation_id: str) -> Dict:
        """Check if an activation is still valid."""
        validation = self.validate_license(license_key)
        if not validation['valid']:
            return validation
        
        license_data = self.licenses[license_key]
        
        for activation in license_data['activations']:
            if activation['id'] == activation_id:
                activation['last_check'] = datetime.utcnow().isoformat()
                return {'valid': True, 'license_type': license_data['type']}
        
        return {'valid': False, 'error': 'Activation not found'}
    
    def revoke_license(self, license_key: str) -> bool:
        """Revoke a license."""
        if license_key in self.licenses:
            self.licenses[license_key]['status'] = LicenseStatus.REVOKED.value
            return True
        return False


# Global license manager
license_manager = LicenseManager()


# Enterprise SLA definitions
SLA_DEFINITIONS = {
    'tier_1': {
        'response_time_hours': 1,
        'resolution_time_days': 1,
        'availability_target': 0.999,
        'support_channel': ['email', 'phone', 'slack']
    },
    'tier_2': {
        'response_time_hours': 4,
        'resolution_time_days': 3,
        'availability_target': 0.995,
        'support_channel': ['email', 'portal']
    },
    'tier_3': {
        'response_time_hours': 24,
        'resolution_time_days': 7,
        'availability_target': 0.99,
        'support_channel': ['email', 'portal']
    }
}


class SLAMonitor:
    """Monitor SLA compliance."""
    
    def __init__(self):
        self.metrics = {
            'uptime': [],
            'response_times': [],
            'resolution_times': []
        }
    
    def record_uptime(self, up: bool):
        """Record uptime status."""
        self.metrics['uptime'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'up': up
        })
    
    def get_sla_report(self, tier: str = 'tier_1') -> Dict:
        """Generate SLA compliance report."""
        sla = SLA_DEFINITIONS.get(tier, SLA_DEFINITIONS['tier_3'])
        
        # Calculate uptime percentage
        total_checks = len(self.metrics['uptime'])
        up_checks = len([u for u in self.metrics['uptime'] if u['up']])
        uptime_pct = up_checks / total_checks if total_checks > 0 else 1.0
        
        return {
            'sla_tier': tier,
            'availability': uptime_pct,
            'target': sla['availability_target'],
            'compliant': uptime_pct >= sla['availability_target'],
            'metrics': self.metrics
        }


# Support escalation levels
SUPPORT_LEVELS = {
    1: {'level': 'L1', 'response_hours': 24, 'handler': 'Support Agent'},
    2: {'level': 'L2', 'response_hours': 4, 'handler': 'Senior Engineer'},
    3: {'level': 'L3', 'response_hours': 1, 'handler': 'Architect'},
    4: {'level': 'L4', 'response_hours': 0.5, 'handler': 'CTO Office'}
}


if __name__ == "__main__":
    # Demo license creation
    key = license_manager.create_license(LicenseType.ENTERPRISE, 365, 10)
    print(f"Created license: {key}")
    
    result = license_manager.activate_license(key, "machine-123")
    print(f"Activation result: {result}")
    
    validation = license_manager.validate_license(key)
    print(f"Validation: {validation}")