"""
Cross-Border Privacy Routing.

Automatically routes identity processing based on jurisdiction,
ensuring compliance with regional privacy laws (GDPR, CCPA, etc.).

Features:
- Jurisdiction detection from IP/geolocation
- Regional policy enforcement
- Data residency compliance
- Automatic data routing
- Privacy law simulation
"""

import json
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
import uuid
import ipaddress


class Jurisdiction(Enum):
    """Privacy jurisdictions with different legal frameworks."""
    EU = "EU"  # GDPR
    US = "US"  # Sectoral (CCPA, HIPAA, etc.)
    UK = "UK"  # UK GDPR
    CA = "CA"  # PIPEDA
    AU = "AU"  # APP
    BR = "BR"  # LGPD
    IN = "IN"  # PDPB
    CH = "CH"  # FADP
    NONE = "NONE"  # Unknown/minimal regulation


class PrivacyLaw(Enum):
    """Privacy laws and regulations."""
    GDPR = "GDPR"  # EU General Data Protection Regulation
    UK_GDPR = "UK_GDPR"  # UK GDPR
    CCPA = "CCPA"  # California Consumer Privacy Act
    HIPAA = "HIPAA"  # US Health Insurance Portability
    PIPEDA = "PIPEDA"  # Canada
    APP = "APP"  # Australia Privacy Principles
    LGPD = "LGPD"  # Brazil General Data Protection Law
    PDPB = "PDPB"  # India Personal Data Protection Bill
    FADP = "FADP"  # Switzerland Federal Act


@dataclass
class RegionalPolicy:
    """Privacy policy for a specific jurisdiction."""
    jurisdiction: Jurisdiction
    applicable_laws: List[PrivacyLaw]
    # Data handling
    data_residency_required: bool = False
    data_minimization: bool = True
    purpose_limitation: bool = True
    storage_limitation: bool = True
    # Individual rights
    right_to_access: bool = True
    right_to_erasure: bool = True
    right_to_portability: bool = True
    right_to_object: bool = True
    # Consent
    consent_required: bool = True
    explicit_consent: bool = False
    consent_age: int = 16
    # Biometric-specific
    biometric_special_category: bool = False
    biometric_explicit_consent: bool = False
    biometric_storage_limit: Optional[int] = None  # Days
    # Cross-border transfer
    cross_border_transfer_allowed: bool = True
    adequacy_decisions: List[str] = None
    # Enforcement
    data_protection_officer_required: bool = False
    breach_notification_hours: int = 72
    max_fines_percent_gdp: float = 4.0
    
    def __post_init__(self):
        if self.adequacy_decisions is None:
            self.adequacy_decisions = []
        if self.biometric_storage_limit is None:
            # Default: 5 years for biometrics
            self.biometric_storage_limit = 5 * 365


@dataclass
class ProcessingDecision:
    """Decision on how to process identity data."""
    jurisdiction: Jurisdiction
    allowed: bool
    routing: str  # "local", "eu", "us", "blocked"
    requirements: List[str]  # Compliance requirements
    restrictions: List[str]  # Processing restrictions
    consent_required: bool
    data_residency: str  # Where data must be stored
    cross_border_allowed: bool
    retention_limit_days: Optional[int]
    anonymization_required: bool
    justification: str


class GeoIPResolver:
    """
    Resolve IP address to jurisdiction.
    
    In production, use MaxMind GeoIP2 or similar.
    Here: simulation with CIDR ranges.
    """
    
    # Simulated IP ranges (in production, use real GeoIP database)
    EU_RANGES = [
        "80.0.0.0/8",    # Simplified EU range
        "81.0.0.0/8",
        "82.0.0.0/8",
        "83.0.0.0/8",
        "84.0.0.0/8",
        "85.0.0.0/8",
        "86.0.0.0/8",
        "87.0.0.0/8",
        "88.0.0.0/8",
        "89.0.0.0/8",
        "90.0.0.0/8",
        "91.0.0.0/8",
    ]
    
    US_RANGES = [
        "7.0.0.0/8",
        "8.0.0.0/8",
        "9.0.0.0/8",
        "10.0.0.0/8",
        "24.0.0.0/8",
        "25.0.0.0/8",
        "26.0.0.0/8",
        "27.0.0.0/8",
        "54.0.0.0/8",
        "63.0.0.0/8",
        "64.0.0.0/8",
        "65.0.0.0/8",
        "66.0.0.0/8",
        "67.0.0.0/8",
        "72.0.0.0/8",
        "73.0.0.0/8",
        "74.0.0.0/8",
        "75.0.0.0/8",
        "76.0.0.0/8",
        "77.0.0.0/8",
        "96.0.0.0/8",
        "97.0.0.0/8",
        "98.0.0.0/8",
        "99.0.0.0/8",
        "128.0.0.0/8",
        "129.0.0.0/8",
        "130.0.0.0/8",
        "131.0.0.0/8",
        "132.0.0.0/8",
        "133.0.0.0/8",
        "134.0.0.0/8",
        "135.0.0.0/8",
        "136.0.0.0/8",
        "137.0.0.0/8",
        "138.0.0.0/8",
        "139.0.0.0/8",
        "140.0.0.0/8",
        "141.0.0.0/8",
        "142.0.0.0/8",
        "143.0.0.0/8",
        "144.0.0.0/8",
        "145.0.0.0/8",
        "146.0.0.0/8",
        "147.0.0.0/8",
        "148.0.0.0/8",
        "149.0.0.0/8",
        "150.0.0.0/8",
        "151.0.0.0/8",
        "152.0.0.0/8",
        "153.0.0.0/8",
        "154.0.0.0/8",
        "155.0.0.0/8",
        "156.0.0.0/8",
        "157.0.0.0/8",
        "158.0.0.0/8",
        "159.0.0.0/8",
        "160.0.0.0/8",
        "161.0.0.0/8",
        "162.0.0.0/8",
        "163.0.0.0/8",
        "164.0.0.0/8",
        "165.0.0.0/8",
        "166.0.0.0/8",
        "167.0.0.0/8",
        "168.0.0.0/8",
        "169.0.0.0/8",
        "170.0.0.0/8",
        "171.0.0.0/8",
        "172.0.0.0/8",
        "173.0.0.0/8",
        "174.0.0.0/8",
        "175.0.0.0/8",
        "176.0.0.0/8",
        "177.0.0.0/8",
        "178.0.0.0/8",
        "179.0.0.0/8",
        "180.0.0.0/8",
        "181.0.0.0/8",
        "182.0.0.0/8",
        "183.0.0.0/8",
        "184.0.0.0/8",
        "185.0.0.0/8",
        "186.0.0.0/8",
        "187.0.0.0/8",
        "188.0.0.0/8",
        "189.0.0.0/8",
        "190.0.0.0/8",
        "191.0.0.0/8",
        "192.0.0.0/8",
        "193.0.0.0/8",
        "194.0.0.0/8",
        "195.0.0.0/8",
        "196.0.0.0/8",
        "197.0.0.0/8",
        "198.0.0.0/8",
        "199.0.0.0/8",
        "200.0.0.0/8",
        "201.0.0.0/8",
        "202.0.0.0/8",
        "203.0.0.0/8",
        "204.0.0.0/8",
        "205.0.0.0/8",
        "206.0.0.0/8",
        "207.0.0.0/8",
        "208.0.0.0/8",
        "209.0.0.0/8",
        "210.0.0.0/8",
        "211.0.0.0/8",
        "212.0.0.0/8",
        "213.0.0.0/8",
        "214.0.0.0/8",
        "215.0.0.0/8",
        "216.0.0.0/8",
        "217.0.0.0/8",
        "218.0.0.0/8",
        "219.0.0.0/8",
        "220.0.0.0/8",
        "221.0.0.0/8",
        "222.0.0.0/8",
        "223.0.0.0/8",
    ]
    
    UK_RANGES = [
        "77.0.0.0/8",
        "78.0.0.0/8",
    ]
    
    @staticmethod
    def resolve(ip: str) -> Jurisdiction:
        """
        Resolve IP address to jurisdiction.
        
        Args:
            ip: IP address string
        
        Returns:
            Jurisdiction
        """
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            for cidr in GeoIPResolver.EU_RANGES:
                if ip_obj in ipaddress.ip_network(cidr):
                    return Jurisdiction.EU
            
            for cidr in GeoIPResolver.UK_RANGES:
                if ip_obj in ipaddress.ip_network(cidr):
                    return Jurisdiction.UK
            
            for cidr in GeoIPResolver.US_RANGES:
                if ip_obj in ipaddress.ip_network(cidr):
                    return Jurisdiction.US
            
            # Default fallback based on first octet
            first_octet = int(ip.split('.')[0])
            if first_octet < 128:
                return Jurisdiction.EU  # Assume rest is EU for demo
            
            return Jurisdiction.NONE
        
        except Exception:
            return Jurisdiction.NONE


class PrivacyPolicyEngine:
    """
    Privacy policy engine for jurisdiction-aware processing.
    """
    
    # Regional policies
    REGIONAL_POLICIES = {
        Jurisdiction.EU: RegionalPolicy(
            jurisdiction=Jurisdiction.EU,
            applicable_laws=[PrivacyLaw.GDPR],
            data_residency_required=True,
            biometric_special_category=True,
            biometric_explicit_consent=True,
            biometric_storage_limit=5 * 365,  # 5 years max
            consent_required=True,
            explicit_consent=True,
            consent_age=16,
            right_to_erasure=True,
            right_to_portability=True,
            right_to_object=True,
            cross_border_transfer_allowed=False,  # Requires adequacy
            adequacy_decisions=["UK", "CH", "NO", "IS", "LI", "JP"],
            data_protection_officer_required=True,
            breach_notification_hours=72,
            max_fines_percent_gdp=4.0,
        ),
        Jurisdiction.UK: RegionalPolicy(
            jurisdiction=Jurisdiction.UK,
            applicable_laws=[PrivacyLaw.UK_GDPR],
            data_residency_required=False,  # Post-Brexit
            biometric_special_category=True,
            biometric_explicit_consent=True,
            biometric_storage_limit=5 * 365,
            consent_required=True,
            explicit_consent=True,
            consent_age=13,  # UK lower age
            right_to_erasure=True,
            right_to_portability=True,
            right_to_object=True,
            cross_border_transfer_allowed=True,
            adequacy_decisions=["EU", "CH", "NO", "IS", "LI", "JP"],
            data_protection_officer_required=False,  # Depends on scale
            breach_notification_hours=72,
            max_fines_percent_gdp=4.0,
        ),
        Jurisdiction.US: RegionalPolicy(
            jurisdiction=Jurisdiction.US,
            applicable_laws=[PrivacyLaw.CCPA, PrivacyLaw.HIPAA],
            data_residency_required=False,
            biometric_special_category=False,  # Not federally special
            biometric_explicit_consent=False,
            biometric_storage_limit=None,  # No federal limit
            consent_required=False,  # Opt-out in many states
            explicit_consent=False,
            consent_age=13,  # COPPA
            right_to_erasure=True,  # CCPA
            right_to_portability=True,  # CCPA
            right_to_object=False,  # No GDPR-style objection
            cross_border_transfer_allowed=True,
            adequacy_decisions=[],  # US adequacy limited
            data_protection_officer_required=False,
            breach_notification_hours=720,  # 30 days in some states
            max_fines_percent_gdp=0.0,  # No GDP-based fines
        ),
        Jurisdiction.CA: RegionalPolicy(
            jurisdiction=Jurisdiction.CA,
            applicable_laws=[PrivacyLaw.PIPEDA],
            data_residency_required=False,
            biometric_special_category=True,
            biometric_explicit_consent=True,
            biometric_storage_limit=5 * 365,
            consent_required=True,
            explicit_consent=False,
            consent_age=13,
            right_to_erasure=True,
            right_to_portability=True,
            right_to_object=True,
            cross_border_transfer_allowed=True,
            adequacy_decisions=["EU"],  # EU considers Canada adequate
            data_protection_officer_required=False,
            breach_notification_hours=72,
            max_fines_percent_gdp=0.0,
        ),
        Jurisdiction.CH: RegionalPolicy(
            jurisdiction=Jurisdiction.CH,
            applicable_laws=[PrivacyLaw.FADP],
            data_residency_required=False,
            biometric_special_category=True,
            biometric_explicit_consent=True,
            biometric_storage_limit=5 * 365,
            consent_required=True,
            explicit_consent=False,
            consent_age=14,
            right_to_erasure=True,
            right_to_portability=True,
            right_to_object=True,
            cross_border_transfer_allowed=True,
            adequacy_decisions=["EU"],  # EU considers Switzerland adequate
            data_protection_officer_required=False,
            breach_notification_hours=72,
            max_fines_percent_gdp=0.0,
        ),
        Jurisdiction.NONE: RegionalPolicy(
            jurisdiction=Jurisdiction.NONE,
            applicable_laws=[],
            data_residency_required=False,
            biometric_special_category=False,
            biometric_explicit_consent=False,
            biometric_storage_limit=None,
            consent_required=False,
            explicit_consent=False,
            consent_age=0,
            right_to_erasure=False,
            right_to_portability=False,
            right_to_object=False,
            cross_border_transfer_allowed=True,
            adequacy_decisions=[],
            data_protection_officer_required=False,
            breach_notification_hours=999999,
            max_fines_percent_gdp=0.0,
        ),
    }
    
    def __init__(self, system_region: Jurisdiction = Jurisdiction.EU):
        self.system_region = system_region
        self.processing_log = []
    
    def determine_jurisdiction(
        self,
        ip_address: Optional[str] = None,
        user_location: Optional[str] = None
    ) -> Jurisdiction:
        """
        Determine jurisdiction based on IP or location.
        
        Args:
            ip_address: Client IP address
            user_location: Explicit location (country code)
        
        Returns:
            Determined jurisdiction
        """
        if user_location:
            try:
                return Jurisdiction(user_location.upper())
            except ValueError:
                pass
        
        if ip_address:
            return GeoIPResolver.resolve(ip_address)
        
        return Jurisdiction.NONE
    
    def evaluate_processing(
        self,
        data_type: str,
        jurisdiction: Jurisdiction,
        purpose: str,
        consent_given: bool = False,
        user_age: Optional[int] = None,
        data_categories: Optional[List[str]] = None
    ) -> ProcessingDecision:
        """
        Evaluate if processing is allowed under regional law.
        
        Args:
            data_type: Type of data (e.g., "biometric", "personal")
            jurisdiction: Subject's jurisdiction
            purpose: Processing purpose
            consent_given: Whether consent was obtained
            user_age: Subject's age
            data_categories: Specific data categories
        
        Returns:
            Processing decision with requirements
        """
        policy = self.REGIONAL_POLICIES.get(
            jurisdiction,
            self.REGIONAL_POLICIES[Jurisdiction.NONE]
        )
        
        requirements = []
        restrictions = []
        
        # Check consent
        consent_ok = True
        if policy.consent_required and not consent_given:
            consent_ok = False
            requirements.append("explicit_consent_required")
        
        if policy.explicit_consent and consent_given:
            # Verify it's explicit (not implied)
            requirements.append("explicit_consent_verification")
        
        # Check age
        age_ok = True
        if user_age is not None and user_age < policy.consent_age:
            age_ok = False
            requirements.append(f"parental_consent_required_{policy.consent_age}+")
        
        # Check biometric special category
        biometric_ok = True
        if data_type == "biometric" and policy.biometric_special_category:
            requirements.append("biometric_special_category_handling")
            if policy.biometric_explicit_consent and not consent_given:
                biometric_ok = False
            
            if policy.biometric_storage_limit:
                restrictions.append(
                    f"max_storage_{policy.biometric_storage_limit}_days"
                )
        
        # Data residency
        data_residency = "local"
        if policy.data_residency_required:
            data_residency = jurisdiction.value
            restrictions.append("data_must_reside_in_region")
        
        # Cross-border transfer
        cross_border = policy.cross_border_transfer_allowed
        if not cross_border and self.system_region != jurisdiction:
            restrictions.append("cross_border_transfer_blocked")
        
        # Purpose limitation
        if policy.purpose_limitation:
            restrictions.append("purpose_must_be_specified_and_limited")
        
        # Storage limitation
        if policy.storage_limitation:
            restrictions.append("data_retention_limited")
        
        # Anonymization
        anonymization = False
        if data_type == "biometric" and not biometric_ok:
            anonymization = True
            requirements.append("anonymization_required")
        
        # Determine if allowed
        allowed = (
            consent_ok
            and age_ok
            and biometric_ok
            and (cross_border or self.system_region == jurisdiction)
        )
        
        justification = self._build_justification(
            policy,
            consent_ok,
            age_ok,
            biometric_ok,
            allowed
        )
        
        return ProcessingDecision(
            jurisdiction=jurisdiction,
            allowed=allowed,
            routing=data_residency,
            requirements=requirements,
            restrictions=restrictions,
            consent_required=policy.consent_required,
            data_residency=data_residency,
            cross_border_allowed=cross_border,
            retention_limit_days=policy.biometric_storage_limit,
            anonymization_required=anonymization,
            justification=justification
        )
    
    def _build_justification(
        self,
        policy: RegionalPolicy,
        consent_ok: bool,
        age_ok: bool,
        biometric_ok: bool,
        allowed: bool
    ) -> str:
        """Build human-readable justification."""
        reasons = []
        
        if not allowed:
            if not consent_ok:
                reasons.append("consent_required")
            if not age_ok:
                reasons.append("age_restriction")
            if not biometric_ok:
                reasons.append("biometric_processing_restricted")
        else:
            reasons.append("compliant")
        
        return f"Jurisdiction {policy.jurisdiction.value}: {', '.join(reasons)}"
    
    def route_processing(
        self,
        data_type: str,
        ip_address: str,
        purpose: str,
        consent_given: bool = False
    ) -> ProcessingDecision:
        """
        Automatically route processing based on jurisdiction.
        
        Args:
            data_type: Type of data
            ip_address: Client IP
            purpose: Processing purpose
            consent_given: Consent status
        
        Returns:
            Processing decision with routing
        """
        jurisdiction = self.determine_jurisdiction(ip_address=ip_address)
        
        return self.evaluate_processing(
            data_type=data_type,
            jurisdiction=jurisdiction,
            purpose=purpose,
            consent_given=consent_given
        )
    
    def simulate_regulatory_change(
        self,
        new_law: PrivacyLaw,
        jurisdiction: Jurisdiction,
        effective_date: str
    ) -> Dict[str, Any]:
        """
        Simulate impact of regulatory change.
        
        Args:
            new_law: New privacy law
            jurisdiction: Affected jurisdiction
            effective_date: When it takes effect
        
        Returns:
            Impact assessment
        """
        current_policy = self.REGIONAL_POLICIES[jurisdiction]
        
        # Simulate stricter requirements
        if new_law == PrivacyLaw.GDPR and jurisdiction == Jurisdiction.EU:
            simulated = RegionalPolicy(
                jurisdiction=jurisdiction,
                applicable_laws=[new_law],
                data_residency_required=True,
                biometric_special_category=True,
                biometric_explicit_consent=True,
                biometric_storage_limit=3 * 365,  # Reduced from 5 years
                consent_required=True,
                explicit_consent=True,
                consent_age=16,
                right_to_erasure=True,
                right_to_portability=True,
                right_to_object=True,
                cross_border_transfer_allowed=False,
                adequacy_decisions=["UK", "CH"],  # Reduced
                data_protection_officer_required=True,
                breach_notification_hours=48,  # Tighter
                max_fines_percent_gdp=6.0,  # Increased
            )
        else:
            # Generic stricter policy
            simulated = RegionalPolicy(
                jurisdiction=jurisdiction,
                applicable_laws=[new_law],
                data_residency_required=current_policy.data_residency_required,
                biometric_special_category=True,
                biometric_explicit_consent=True,
                biometric_storage_limit=max(
                    1 * 365,
                    current_policy.biometric_storage_limit or 365
                ) - (365 if current_policy.biometric_storage_limit else 0),
                consent_required=True,
                explicit_consent=True,
                consent_age=current_policy.consent_age,
                right_to_erasure=True,
                right_to_portability=True,
                right_to_object=True,
                cross_border_transfer_allowed=False,
                adequacy_decisions=[],
                data_protection_officer_required=True,
                breach_notification_hours=24,
                max_fines_percent_gdp=current_policy.max_fines_percent_gdp + 2.0,
            )
        
        # Assess impact
        impact = {
            "law": new_law.value,
            "jurisdiction": jurisdiction.value,
            "effective_date": effective_date,
            "changes": {
                "storage_limit_reduced": simulated.biometric_storage_limit < \
                    (current_policy.biometric_storage_limit or 9999),
                "consent_stricter": simulated.explicit_consent and \
                    not current_policy.explicit_consent,
                "cross_border_blocked": not simulated.cross_border_transfer_allowed and \
                    current_policy.cross_border_transfer_allowed,
                "fines_increased": simulated.max_fines_percent_gdp > \
                    current_policy.max_fines_percent_gdp,
                "breach_notification_tighter": simulated.breach_notification_hours < \
                    current_policy.breach_notification_hours,
            },
            "simulated_policy": asdict(simulated),
            "current_policy": asdict(current_policy),
            "systems_affected": self._assess_systems_affected(
                current_policy, simulated
            ),
            "recommended_actions": self._get_recommended_actions(
                current_policy, simulated
            )
        }
        
        return impact
    
    def _assess_systems_affected(
        self,
        current: RegionalPolicy,
        simulated: RegionalPolicy
    ) -> List[str]:
        """Assess which systems would be affected."""
        affected = []
        
        if simulated.biometric_storage_limit < (current.biometric_storage_limit or 9999):
            affected.append("biometric_storage_cleanup_required")
        
        if not simulated.cross_border_transfer_allowed and \
           current.cross_border_transfer_allowed:
            affected.append("cross_border_processing_blocked")
        
        if simulated.explicit_consent and not current.explicit_consent:
            affected.append("consent_flow_update_required")
        
        if simulated.breach_notification_hours < current.breach_notification_hours:
            affected.append("incident_response_update_required")
        
        return affected
    
    def _get_recommended_actions(
        self,
        current: RegionalPolicy,
        simulated: RegionalPolicy
    ) -> List[str]:
        """Get recommended compliance actions."""
        actions = []
        
        if simulated.biometric_storage_limit < (current.biometric_storage_limit or 9999):
            actions.append("Review and purge old biometric data")
        
        if not simulated.cross_border_transfer_allowed:
            actions.append("Implement local data processing infrastructure")
        
        if simulated.explicit_consent:
            actions.append("Update consent collection to explicit opt-in")
        
        if simulated.breach_notification_hours < current.breach_notification_hours:
            actions.append("Accelerate incident detection and response capabilities")
        
        actions.append("Conduct Data Protection Impact Assessment (DPIA)")
        actions.append("Update privacy policy and user notices")
        actions.append("Train staff on new requirements")
        
        return actions
    
    def log_processing(
        self,
        decision: ProcessingDecision,
        data_type: str,
        ip_address: str,
        purpose: str
    ) -> Dict[str, Any]:
        """
        Log a processing decision for audit trail.
        
        Args:
            decision: Processing decision
            data_type: Type of data processed
            ip_address: Source IP
            purpose: Processing purpose
        
        Returns:
            Log entry
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_type": data_type,
            "ip_address": ip_address,
            "jurisdiction": decision.jurisdiction.value,
            "purpose": purpose,
            "allowed": decision.allowed,
            "routing": decision.routing,
            "requirements": decision.requirements,
            "restrictions": decision.restrictions,
            "anonymization_required": decision.anonymization_required,
            "retention_limit_days": decision.retention_limit_days
        }
        
        self.processing_log.append(entry)
        return entry
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processing decisions."""
        if not self.processing_log:
            return {"total_processed": 0}
        
        by_jurisdiction = {}
        for entry in self.processing_log:
            j = entry["jurisdiction"]
            if j not in by_jurisdiction:
                by_jurisdiction[j] = {
                    "total": 0,
                    "allowed": 0,
                    "blocked": 0,
                    "anonymized": 0
                }
            by_jurisdiction[j]["total"] += 1
            if entry["allowed"]:
                by_jurisdiction[j]["allowed"] += 1
            else:
                by_jurisdiction[j]["blocked"] += 1
            if entry["anonymization_required"]:
                by_jurisdiction[j]["anonymized"] += 1
        
        return {
            "total_processed": len(self.processing_log),
            "by_jurisdiction": by_jurisdiction,
            "time_range": {
                "start": self.processing_log[0]["timestamp"],
                "end": self.processing_log[-1]["timestamp"]
            }
        }


# Convenience functions
def check_processing_allowed(
    ip_address: str,
    data_type: str,
    purpose: str,
    consent_given: bool = False,
    user_age: Optional[int] = None,
    system_region: Jurisdiction = Jurisdiction.EU
) -> ProcessingDecision:
    """
    Check if processing is allowed for a request.
    
    Args:
        ip_address: Client IP
        data_type: Type of data
        purpose: Processing purpose
        consent_given: Consent status
        user_age: User age
        system_region: System's region
    
    Returns:
        Processing decision
    """
    engine = PrivacyPolicyEngine(system_region=system_region)
    return engine.route_processing(
        data_type=data_type,
        ip_address=ip_address,
        purpose=purpose,
        consent_given=consent_given
    )


def simulate_regulatory_impact(
    new_law: PrivacyLaw,
    jurisdiction: Jurisdiction
) -> Dict[str, Any]:
    """
    Simulate impact of a new privacy law.
    
    Args:
        new_law: New privacy law
        jurisdiction: Affected jurisdiction
    
    Returns:
        Impact assessment
    """
    engine = PrivacyPolicyEngine()
    return engine.simulate_regulatory_change(
        new_law=new_law,
        jurisdiction=jurisdiction,
        effective_date=datetime.now(timezone.utc).isoformat()
    )


def get_regional_policy(jurisdiction: Jurisdiction) -> Dict[str, Any]:
    """
    Get privacy policy for a jurisdiction.
    
    Args:
        jurisdiction: Jurisdiction to query
    
    Returns:
        Policy details
    """
    from dataclasses import asdict
    policy = PrivacyPolicyEngine.REGIONAL_POLICIES.get(
        jurisdiction,
        PrivacyPolicyEngine.REGIONAL_POLICIES[Jurisdiction.NONE]
    )
    return asdict(policy)


def compare_jurisdictions(
    j1: Jurisdiction,
    j2: Jurisdiction
) -> Dict[str, Any]:
    """
    Compare privacy policies between two jurisdictions.
    
    Args:
        j1: First jurisdiction
        j2: Second jurisdiction
    
    Returns:
        Comparison
    """
    p1 = PrivacyPolicyEngine.REGIONAL_POLICIES[j1]
    p2 = PrivacyPolicyEngine.REGIONAL_POLICIES[j2]
    
    differences = []
    for field in p1.__dict__:
        v1 = getattr(p1, field)
        v2 = getattr(p2, field)
        if v1 != v2:
            differences.append({
                "field": field,
                f"{j1.value}": v1,
                f"{j2.value}": v2
            })
    
    return {
        "jurisdictions": {j1.value, j2.value},
        "differences": differences
    }