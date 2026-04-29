from enum import Enum

class ErrorCode(str, Enum):
    # Authentication & Authorization
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_EXPIRED_TOKEN = "AUTH_EXPIRED_TOKEN"
    AUTH_REVOKED_TOKEN = "AUTH_REVOKED_TOKEN"
    AUTH_MISSING_CREDENTIALS = "AUTH_MISSING_CREDENTIALS"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"
    AUTH_MFA_REQUIRED = "AUTH_MFA_REQUIRED"
    
    # Recognition & Enrollment
    BIO_NO_FACE_DETECTED = "BIO_NO_FACE_DETECTED"
    BIO_MULTIPLE_FACES_DETECTED = "BIO_MULTIPLE_FACES_DETECTED"
    BIO_SPOOF_DETECTED = "BIO_SPOOF_DETECTED"
    BIO_LOW_QUALITY_IMAGE = "BIO_LOW_QUALITY_IMAGE"
    BIO_ENROLLMENT_EXISTS = "BIO_ENROLLMENT_EXISTS"
    BIO_CONSENT_REQUIRED = "BIO_CONSENT_REQUIRED"
    
    # System & Infrastructure
    SYS_DB_UNAVAILABLE = "SYS_DB_UNAVAILABLE"
    SYS_REDIS_UNAVAILABLE = "SYS_REDIS_UNAVAILABLE"
    SYS_MODEL_NOT_LOADED = "SYS_MODEL_NOT_LOADED"
    SYS_RATE_LIMIT_EXCEEDED = "SYS_RATE_LIMIT_EXCEEDED"
    SYS_USAGE_LIMIT_EXCEEDED = "SYS_USAGE_LIMIT_EXCEEDED"
    
    # Compliance & Legal
    COMP_GDPR_ERASURE_PENDING = "COMP_GDPR_ERASURE_PENDING"
    COMP_BIPA_CONSENT_MISSING = "COMP_BIPA_CONSENT_MISSING"
    COMP_GEOGRAPHIC_RESTRICTION = "COMP_GEOGRAPHIC_RESTRICTION"

class ErrorDetail:
    def __init__(self, code: ErrorCode, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self):
        return {
            "success": False,
            "code": self.code,
            "message": self.message,
            "details": self.details
        }
