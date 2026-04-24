from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib


class Region(Enum):
    """Global regions with different regulations."""
    US = "us"
    EU = "eu"  # GDPR
    UK = "uk"  # UK GDPR
    CA = "ca"  # PIPEDA
    CN = "cn"  # Personal Information Protection Law
    JP = "jp"  # APPI
    AU = "au"  # Privacy Act
    BRAZIL = "br"  # LGPD
    IN = "in"  # DPDP


class Purpose(Enum):
    """Permitted purposes for processing."""
    AUTHENTICATION = "authentication"
    ACCESS_CONTROL = "access_control"
    ATTENDANCE = "attendance"
    SURVEILLANCE = "surveillance"  # Requires special notice
    DEMOGRAPHICS = "demographics"  # Aggregate only
    SECURITY = "security"
    HEALTH = "health"  # HIPAA context
    RESEARCH = "research"  # IRB approval required


class BiometricType(Enum):
    """Types of biometric data."""
    FACE = "face"
    VOICE = "voice"
    GAIT = "gait"
    FINGERPRINT = "fingerprint"
    IRIS = "iris"


@dataclass
class PurposeConstraint:
    """Purpose limitation for a specific use case."""
    purpose: Purpose
    required_legal_basis: str  # consent, legitimate_interest, legal_obligation
    requires_explicit_notice: bool = False
    requires_impact_assessment: bool = False
    data_retention_days: int = 365
    allows_cross_border: bool = True
    min_age: int = 13  # For parental consent


@dataclass
class ConsentRecord:
    """GDPR-compliant consent record."""
    consent_id: str
    user_id: str
    purpose: str
    biometric_types: List[BiometricType]
    granted: bool
    granted_at: str
    expires_at: Optional[str]
    purpose_limitation: str
    region: Region
    withdrawal_method: str
    version: str


@dataclass
class ProcessingActivity:
    """Record of processing activity for audit."""
    activity_id: str
    user_id: str
    purpose: Purpose
    biometric_type: BiometricType
    legal_basis: str
    timestamp: str
    region: Region
    data_categories: List[str]
    recipient_categories: Optional[List[str]]
    transfer_mechanism: Optional[str]  # SCC, adequacy
    retention_period_days: int
    access_log: List[Dict]


class LegalCompliance:
    """Legal compliance layer for face recognition."""
    
    # Purpose constraints by region
    PURPOSE_CONSTRAINTS: Dict[Region, Dict[Purpose, PurposeConstraint]] = {
        Region.EU: {
            Purpose.AUTHENTICATION: PurposeConstraint(
                purpose=Purpose.AUTHENTICATION,
                required_legal_basis="consent",
                requires_explicit_notice=True,
                requires_impact_assessment=True,
                data_retention_days=30,
                allows_cross_border=False
            ),
            Purpose.SURVEILLANCE: PurposeConstraint(
                purpose=Purpose.SURVEILLANCE,
                required_legal_basis="legitimate_interest",
                requires_explicit_notice=True,
                requires_impact_assessment=True,
                data_retention_days=30,
                allows_cross_border=False
            )
        },
        Region.US: {
            Purpose.AUTHENTICATION: PurposeConstraint(
                purpose=Purpose.AUTHENTICATION,
                required_legal_basis="consent",
                data_retention_days=365,
                allows_cross_border=True
            )
        },
        Region.CN: {
            Purpose.AUTHENTICATION: PurposeConstraint(
                purpose=Purpose.AUTHENTICATION,
                required_legal_basis="consent",
                requires_explicit_notice=True,
                data_retention_days=180,
                allows_cross_border=False
            )
        }
    }
    
    def __init__(self):
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.activities: List[ProcessingActivity] = []
        self.region_toggles: Dict[Region, Dict[str, bool]] = {}
        
        # Initialize by region
        self._init_region_toggles()
    
    def _init_region_toggles(self) -> None:
        """Initialize feature toggles by region."""
        self.region_toggles = {
            Region.EU: {
                "face_recognition": True,
                "emotion_detection": False,  # Prohibited under GDPR
                "age_estimation": True,
                "gender_detection": False,
                "voice_recognition": True,
                "gait_recognition": False,
                "liveness_detection": True,
                "public_surveillance": False
            },
            Region.US: {
                "face_recognition": True,
                "emotion_detection": True,
                "age_estimation": True,
                "gender_detection": True,
                "voice_recognition": True,
                "gait_recognition": True,
                "liveness_detection": True,
                "public_surveillance": True
            },
            Region.CN: {
                "face_recognition": True,
                "emotion_detection": True,
                "age_estimation": True,
                "gender_detection": True,
                "voice_recognition": True,
                "gait_recognition": True,
                "liveness_detection": True,
                "public_surveillance": True
            }
        }
    
    def get_available_features(self, region: Region) -> Dict[str, bool]:
        """Get feature availability for region."""
        return self.region_toggles.get(region, {})
    
    def check_purpose_allowed(
        self,
        region: Region,
        purpose: Purpose,
        user_id: str,
        biometric_type: BiometricType
    ) -> Tuple[bool, Optional[str]]:
        """Check if purpose is allowed."""
        constraints = self.PURPOSE_CONSTRAINTS.get(region, {})
        constraint = constraints.get(purpose)
        
        if not constraint:
            return True, None
        
        # Check consent
        for consent in self.consent_records.values():
            if consent.user_id == user_id:
                if consent.purpose == purpose.value:
                    if consent.granted:
                        return True, None
                    return False, "Consent not granted"
        
        return False, "No valid consent"
    
    def record_consent(
        self,
        user_id: str,
        purpose: Purpose,
        biometric_types: List[BiometricType],
        region: Region,
        granted: bool = True
    ) -> ConsentRecord:
        """Record consent per GDPR requirements."""
        consent_id = hashlib.sha256(
            f"{user_id}{purpose.value}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        constraint = self.PURPOSE_CONSTRAINTS.get(region, {}).get(purpose)
        retention = constraint.data_retention_days if constraint else 365
        
        expires_at = None
        if retention > 0:
            expires_at = (
                datetime.utcnow() + timedelta(days=retention)
            ).isoformat()
        
        record = ConsentRecord(
            consent_id=consent_id,
            user_id=user_id,
            purpose=purpose.value,
            biometric_types=biometric_types,
            granted=granted,
            granted_at=datetime.utcnow().isoformat(),
            expires_at=expires_at,
            purpose_limitation=purpose.value,
            region=region,
            withdrawal_method="api:DELETE /api/consent/{id}",
            version="v1"
        )
        
        self.consent_records[consent_id] = record
        return record
    
    def withdraw_consent(self, consent_id: str) -> bool:
        """Process consent withdrawal."""
        if consent_id in self.consent_records:
            self.consent_records[consent_id].granted = False
            self.consent_records[consent_id].granted_at = (
                datetime.utcnow().isoformat()
            )
            return True
        return False
    
    def log_processing_activity(
        self,
        user_id: str,
        purpose: Purpose,
        biometric_type: BiometricType,
        regions: List[Region],
        legal_basis: str,
        data_categories: List[str],
        recipients: Optional[List[str]] = None,
        transfer_mechanism: Optional[str] = None
    ) -> str:
        """Log processing activity for audit trail."""
        activity_id = f"act_{len(self.activities)}_{datetime.utcnow().timestamp()}"
        
        activity = ProcessingActivity(
            activity_id=activity_id,
            user_id=user_id,
            purpose=purpose,
            biometric_type=biometric_type,
            legal_basis=legal_basis,
            timestamp=datetime.utcnow().isoformat(),
            region=regions[0] if regions else Region.US,
            data_categories=data_categories,
            recipient_categories=recipients,
            transfer_mechanism=transfer_mechanism,
            retention_period_days=365,
            access_log=[]
        )
        
        self.activities.append(activity)
        return activity_id
    
    def generate_signed_audit_export(self, user_id: str) -> Dict:
        """Generates a cryptographically signed audit export for forensic use."""
        import hmac
        import hashlib
        
        audit_data = self.get_audit_trail(user_id=user_id)
        data_string = json.dumps(audit_data, sort_keys=True)
        
        # Sign with system secret
        secret = os.getenv("AUDIT_SIGNING_SECRET", "audit_secret")
        signature = hmac.new(secret.encode(), data_string.encode(), hashlib.sha256).hexdigest()
        
        return {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "audit_trail": audit_data,
            "forensic_signature": signature,
            "signature_algorithm": "HMAC-SHA256"
        }

    def get_audit_trail(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Generate audit trail for compliance."""
        results = self.activities
        
        if user_id:
            results = [a for a in results if a.user_id == user_id]
        
        if start_date:
            results = [
                a for a in results
                if a.timestamp >= start_date
            ]
        
        if end_date:
            results = [
                a for a in results
                if a.timestamp <= end_date
            ]
        
        return [
            {
                "activity_id": a.activity_id,
                "user_id": a.user_id,
                "purpose": a.purpose.value,
                "biometric_type": a.biometric_type.value,
                "legal_basis": a.legal_basis,
                "timestamp": a.timestamp,
                "region": a.region.value
            }
            for a in results
        ]
    
    def generate_data_subject_access(
        self,
        user_id: str
    ) -> Dict:
        """Generate DSAR response."""
        user_consents = [
            vars(c) for c in self.consent_records.values()
            if c.user_id == user_id
        ]
        
        user_activities = [
            vars(a) for a in self.activities
            if a.user_id == user_id
        ]
        
        return {
            "user_id": user_id,
            "consents": user_consents,
            "processing_activities": user_activities,
            "generated_at": datetime.utcnow().isoformat(),
            "data_categories": [
                "biometric_embeddings",
                "face_images",
                "voice_recordings",
                "consent_records",
                "access_logs"
            ]
        }
    
    async def process_deletion(self, user_id: str) -> bool:
        """Actually process the deletion of a user (Right to be Forgotten)."""
        from .db.db_client import get_db
        db = await get_db()
        
        # 1. Delete embeddings and person record
        success = await db.delete_person(user_id)
        
        # 2. Cleanup local compliance records
        self.consent_records = {k: v for k, v in self.consent_records.items() if v.user_id != user_id}
        self.activities = [a for a in self.activities if a.user_id != user_id]
        
        return success

    async def run_retention_cleanup(self) -> int:
        """Run periodic cleanup of expired data."""
        from .db.db_client import get_db
        db = await get_db()
        
        now = datetime.utcnow().isoformat()
        expired_consents = [c.user_id for c in self.consent_records.values() if c.expires_at and c.expires_at < now]
        
        count = 0
        for user_id in set(expired_consents):
            if await self.process_deletion(user_id):
                count += 1
        
        return count
    
    def check_cross_border_transfer(
        self,
        source_region: Region,
        target_region: Region,
        purpose: Purpose
    ) -> Tuple[bool, Optional[str]]:
        """Check if cross-border transfer is allowed."""
        source_constraints = self.PURPOSE_CONSTRAINTS.get(source_region, {})
        constraint = source_constraints.get(purpose)
        
        if constraint and not constraint.allows_cross_border:
            return False, "Cross-border transfer not permitted"
        
        # Check adequacy decisions
        adequacy = {
            (Region.EU, Region.EU): True,  # EU->EU okay
            (Region.EU, Region.US): False,  # Requires SCC
            (Region.CN, Region.CN): True,
            (Region.CN, Region.US): False,
        }
        
        key = (source_region, target_region)
        if key in adequacy and not adequacy[key]:
            return False, "Requires appropriate safeguards"
        
        return True, None
    
    def generate_impact_assessment(
        self,
        region: Region,
        purpose: Purpose,
        data_scale: int
    ) -> Dict:
        """Generate DPIA/DPIA for new processing."""
        constraint = self.PURPOSE_CONSTRAINTS.get(region, {}).get(purpose)
        
        return {
            "assessment_id": f"dia_{datetime.utcnow().timestamp()}",
            "region": region.value,
            "purpose": purpose.value,
            "requires_impact_assessment": (
                constraint.requires_impact_assessment if constraint else False
            ),
            "data_subject_scale": data_scale,
            "risk_level": "high" if data_scale > 10000 else "medium",
            "proposed_safeguards": [
                "data_encryption_at_rest",
                "encryption_in_transit",
                "access_logging",
                "retention_policies",
                "consent_management"
            ],
            "generated_at": datetime.utcnow().isoformat()
        }


# Global instance
legal_compliance = LegalCompliance()