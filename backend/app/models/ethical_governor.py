from typing import Dict, Any, List
import re


class EthicalGovernor:
    def __init__(self):
        # Rules for ethical AI use
        self.forbidden_patterns = [
            r'child|minor|underage',
            r'violence|weapon|harm',
            r'illegal|criminal',
            r'discrimination|hate',
        ]
        self.max_age = 100  # Max age for enrollment
        self.min_age = 18   # Min age for enrollment

    def check_request(self, request_data: Dict[str, Any], user_role: str = 'user') -> Dict[str, Any]:
        """
        Check if request complies with ethical guidelines.
        Returns {'approved': bool, 'reason': str}
        """
        # Age checks
        age = request_data.get('age')
        if age and (age < self.min_age or age > self.max_age):
            return {'approved': False, 'reason': f'Age {age} not allowed for enrollment'}

        # Content checks (e.g., metadata)
        metadata = request_data.get('metadata', {})
        for key, value in metadata.items():
            if isinstance(value, str):
                for pattern in self.forbidden_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        return {'approved': False, 'reason': f'Forbidden content detected in {key}'}

        # Role-based restrictions
        if user_role not in ['admin', 'operator', 'user']:
            return {'approved': False, 'reason': 'Invalid user role'}

        # Bulk operations limit
        if 'bulk' in request_data and len(request_data['bulk']) > 100:
            return {'approved': False, 'reason': 'Bulk operation too large'}

        return {'approved': True, 'reason': 'Approved'}

    def audit_decision(self, decision: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Log ethical decisions for audit.
        """
        # In production, log to secure audit system
        print(f"Ethical audit: {decision} in context {context}")
