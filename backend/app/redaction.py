import re
from typing import List, Dict, Any


class Redactor:
    """Handles redaction of sensitive information from enrichment results."""

    def __init__(self):
        # Define redaction patterns
        self.patterns = [
            # Social Security Numbers (US)
            (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]'),
            (r'\b\d{3}\d{2}\d{4}\b', '[SSN REDACTED]'),

            # Credit/Debit Card Numbers
            (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
             '[CARD NUMBER REDACTED]'),
            (r'\b\d{4}[\s-]?\d{6}[\s-]?\d{5}\b', '[CARD NUMBER REDACTED]'),

            # Email Addresses
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]'),

            # Phone Numbers (US format)
            (r'\b\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b', '[PHONE REDACTED]'),
            (r'\b\d{10}\b', '[PHONE REDACTED]'),

            # Bank Account Numbers (common patterns)
            # Generic account numbers
            (r'\b\d{8,17}\b', '[ACCOUNT NUMBER REDACTED]'),

            # Addresses (simplified)
            (r'\b\d+\s+[A-Za-z0-9\s,.-]+\b',
             '[ADDRESS REDACTED]'),  # Street addresses

            # Dates of Birth
            (r'\b\d{1,2}/\d{1,2}/\d{4}\b', '[DOB REDACTED]'),
            (r'\b\d{4}-\d{2}-\d{2}\b', '[DOB REDACTED]'),

            # License Numbers (simplified)
            (r'\b[A-Z]{1,2}\d{6,8}\b', '[LICENSE REDACTED]'),
        ]

    def redact_text(self, text: str) -> str:
        """Redact sensitive information from text."""
        if not text:
            return text

        redacted = text
        for pattern, replacement in self.patterns:
            redacted = re.sub(pattern, replacement,
                              redacted, flags=re.IGNORECASE)

        return redacted

    def redact_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive information from a single result."""
        redacted = result.copy()

        # Redact snippet
        if "snippet" in redacted:
            redacted["snippet"] = self.redact_text(redacted["snippet"])

        # Redact title if it contains sensitive info
        if "title" in redacted:
            redacted["title"] = self.redact_text(redacted["title"])

        # Redact raw data if present
        if "raw" in redacted and isinstance(redacted["raw"], dict):
            for key, value in redacted["raw"].items():
                if isinstance(value, str):
                    redacted["raw"][key] = self.redact_text(value)

        return redacted

    def redact_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Redact sensitive information from multiple results."""
        return [self.redact_result(result) for result in results]

    def check_for_sensitive_content(self, text: str) -> List[str]:
        """Check text for sensitive content and return list of found patterns."""
        found = []
        for pattern, replacement in self.patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                found.append(replacement.strip('[]').lower())
        return found
