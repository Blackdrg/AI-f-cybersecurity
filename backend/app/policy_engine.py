from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json
import os
from geoip2.database import Reader as GeoIPReader
from geoip2.errors import AddressNotFoundError
from .security.anomaly_detector import anomaly_detector


def parse_user_agent(user_agent_string: str) -> str:
    """
    Parse User-Agent string to determine device type.
    
    Returns:
        "desktop", "mobile", "tablet", or "unknown"
    """
    if not user_agent_string:
        return "unknown"
    
    ua = user_agent_string.lower()
    
    # Mobile patterns
    mobile_patterns = [
        "android", "iphone", "ipod", "blackberry", "windows phone",
        "opera mini", "mobile", "silk/"
    ]
    for pattern in mobile_patterns:
        if pattern in ua:
            return "mobile"
    
    # Tablet patterns
    tablet_patterns = ["ipad", "tablet", "playbook"]
    for pattern in tablet_patterns:
        if pattern in ua:
            return "tablet"
    
    # Desktop patterns (Windows, macOS, Linux)
    desktop_patterns = ["windows", "macintosh", "linux x86_64", "x11"]
    for pattern in desktop_patterns:
        if pattern in ua:
            return "desktop"
    
    return "unknown"

# Optional: GeoIP support
try:
    GEOIP_ENABLED = True
    GEOIP_PATH = os.getenv("GEOIP_DATABASE_PATH", "/app/data/GeoLite2-City.mmdb")
    geoip_reader = GeoIPReader(GEOIP_PATH) if os.path.exists(GEOIP_PATH) else None
except ImportError:
    GEOIP_ENABLED = False
    geoip_reader = None
except Exception:
    geoip_reader = None


class PolicyEffect(Enum):
    ALLOW = "allow"
    DENY = "deny"
    AUDIT = "audit"  # Allow but log heavily


class SubjectType(Enum):
    USER = "user"
    OPERATOR = "operator"
    ADMIN = "admin"
    SERVICE = "service"
    EDGE_DEVICE = "edge_device"


class ResourceType(Enum):
    ENROLL = "enroll"
    RECOGNIZE = "recognize"
    STREAM = "stream"
    ADMIN = "admin"
    MODEL = "model"
    FEDERATED = "federated"
    AUDIT = "audit"
    CONSENT = "consent"


class ConditionType(Enum):
    TIME_OF_DAY = "time_of_day"
    DAY_OF_WEEK = "day_of_week"
    IP_RANGE = "ip_range"
    GEO_LOCATION = "geo_location"
    DEVICE_TYPE = "device_type"
    AUTH_METHOD = "auth_method"
    RISK_LEVEL = "risk_level"
    PURPOSE = "purpose"


@dataclass
class PolicyRule:
    """A policy rule."""
    rule_id: str
    name: str
    effect: PolicyEffect
    
    # Who (subject)
    subjects: List[str] = field(default_factory=list)  # subject IDs or patterns
    subject_types: List[SubjectType] = field(default_factory=list)
    
    # What (resource)
    resources: List[ResourceType] = field(default_factory=list)
    
    # Conditions
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Limits
    rate_limit: Optional[int] = None  # per minute
    daily_limit: Optional[int] = None
    
    # Metadata
    priority: int = 0
    enabled: bool = True
    description: str = ""


@dataclass
class PolicyDecision:
    """Policy decision result."""
    effect: PolicyEffect
    allowed: bool
    reason: str
    matched_rule: Optional[str]
    conditions_met: List[str] = field(default_factory=list)
    conditions_failed: List[str] = field(default_factory=list)
    rate_limit_remaining: Optional[int] = None


@dataclass
class UsageRecord:
    """Track usage for ratelimiting."""
    user_id: str
    resource: ResourceType
    count: int = 0
    last_reset: str = ""


class PolicyEngine:
    """
    Policy Engine - Enterprise access control
    
    Determines:
    - Who can recognize whom?
    - Under what conditions?
    - With what limits?
    """
    
    def __init__(self):
        self.rules: List[PolicyRule] = []
        self.default_effect = PolicyEffect.DENY
        
        # Usage tracking
        self.usage: Dict[str, Dict[str, List[UsageRecord]]] = {}
        self.usage_lock = None
        
        # Initialize default policies
        self._init_default_policies()
    
    def _init_default_policies(self):
        """Initialize default enterprise policies."""
        
        # Rule 1: Only admins can enroll new people
        self.rules.append(PolicyRule(
            rule_id="admin_enroll_only",
            name="Admin Enroll Only",
            effect=PolicyEffect.ALLOW,
            subject_types=[SubjectType.ADMIN],
            resources=[ResourceType.ENROLL],
            priority=100,
            description="Only admins can enroll new faces"
        ))
        
        # Rule 2: Authenticated users can recognize
        self.rules.append(PolicyRule(
            rule_id="user_recognize",
            name="User Recognize",
            effect=PolicyEffect.ALLOW,
            subject_types=[SubjectType.USER, SubjectType.OPERATOR, SubjectType.ADMIN],
            resources=[ResourceType.RECOGNIZE],
            rate_limit=100,
            daily_limit=10000,
            priority=50,
            description="Authenticated users can recognize with rate limits"
        ))
        
        # Rule 3: Operators can use streams
        self.rules.append(PolicyRule(
            rule_id="operator_stream",
            name="Operator Stream Access",
            effect=PolicyEffect.ALLOW,
            subject_types=[SubjectType.OPERATOR, SubjectType.ADMIN],
            resources=[ResourceType.STREAM],
            rate_limit=10,
            priority=80,
            description="Operators can access real-time streams"
        ))
        
        # Rule 4: Audit all admin actions
        self.rules.append(PolicyRule(
            rule_id="admin_audit",
            name="Admin Audit",
            effect=PolicyEffect.AUDIT,
            subject_types=[SubjectType.ADMIN],
            resources=[ResourceType.ADMIN, ResourceType.MODEL],
            priority=200,
            description="All admin actions must be audited"
        ))
        
        # Rule 5: Service accounts for federated learning
        self.rules.append(PolicyRule(
            rule_id="service_federated",
            name="Service Federated",
            effect=PolicyEffect.ALLOW,
            subject_types=[SubjectType.SERVICE],
            resources=[ResourceType.FEDERATED],
            priority=70,
            description="Service accounts can participate in federated learning"
        ))
        
        # Rule 6: Geo-restricted access (example: only US/CA allowed)
        self.rules.append(PolicyRule(
            rule_id="geo_restrict_north_america",
            name="Geographic Access Control",
            effect=PolicyEffect.ALLOW,
            subject_types=[SubjectType.USER, SubjectType.OPERATOR, SubjectType.ADMIN],
            resources=[ResourceType.RECOGNIZE, ResourceType.ENROLL],
            conditions={"geo_country": ["US", "CA"]},
            priority=90,
            description="Recognition and enrollment restricted to US and Canada"
        ))
        
        # Rule 7: Time-based access (business hours only for external APIs)
        self.rules.append(PolicyRule(
            rule_id="business_hours_only",
            name="Business Hours Restriction",
            effect=PolicyEffect.ALLOW,
            subject_types=[SubjectType.USER],
            resources=[ResourceType.RECOGNIZE],
            conditions={"time_of_day": ("08:00", "18:00")},
            priority=40,
            description="Public recognition only during business hours (8am-6pm)"
        ))
        
        # Rule 8: Device-type restriction (desktop only for admin functions)
        self.rules.append(PolicyRule(
            rule_id="admin_desktop_only",
            name="Admin Desktop Only",
            effect=PolicyEffect.ALLOW,
            subject_types=[SubjectType.ADMIN],
            resources=[ResourceType.ADMIN],
            conditions={"device_type": ["desktop", "laptop"]},
            priority=110,
            description="Admin actions must originate from desktop/laptop (not mobile)"
        ))
        
        # Rule 9: High-risk operations require MFA
        # (enforced separately in middleware, but documented here)
        
        # Sort by priority (higher first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def add_rule(self, rule: PolicyRule) -> None:
        """Add a policy rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a policy rule."""
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                self.rules.pop(i)
                return True
        return False
    
    def evaluate(
        self,
        subject_id: str,
        subject_type: SubjectType,
        resource: ResourceType,
        context: Optional[Dict] = None
    ) -> PolicyDecision:
        """Evaluate policy for subject + resource."""
        context = context or {}
        
        # 1. Anomaly Detection Integration
        ip_addr = context.get("ip_range", "unknown")
        anomaly_results = anomaly_detector.track_request(subject_id, ip_addr)
        
        if anomaly_results["is_anomaly"]:
            return PolicyDecision(
                effect=PolicyEffect.DENY,
                allowed=False,
                reason=f"Anomaly Detected: {', '.join(anomaly_results['reasons'])}",
                matched_rule="anomaly_protection_gate"
            )
        
        # Add risk score to context for further rule evaluation
        context["risk_level"] = "high" if anomaly_detector.get_risk_score(subject_id) > 0.7 else "low"
        
        # Check each rule (sorted by priority)
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # Check if rule applies to this resource
            if resource not in rule.resources:
                continue
            
            # Check subject
            if rule.subject_types and subject_type not in rule.subject_types:
                if subject_id not in rule.subjects:
                    continue
            
            # Check conditions
            conditions_met, conditions_failed = self._evaluate_conditions(
                rule.conditions, context
            )
            
            if conditions_met:
                # Check rate limits
                rate_check = self._check_rate_limit(
                    subject_id, resource, rule.rate_limit, rule.daily_limit
                )
                
                if not rate_check["allowed"]:
                    return PolicyDecision(
                        effect=PolicyEffect.DENY,
                        allowed=False,
                        reason=f"Rate limit exceeded: {rate_check['reason']}",
                        matched_rule=rule.rule_id
                    )
                
                return PolicyDecision(
                    effect=rule.effect,
                    allowed=rule.effect == PolicyEffect.ALLOW,
                    reason=rule.description,
                    matched_rule=rule.rule_id,
                    conditions_met=conditions_met,
                    conditions_failed=conditions_failed,
                    rate_limit_remaining=rate_check.get("remaining")
                )
        
        # No rule matched - apply default
        return PolicyDecision(
            effect=self.default_effect,
            allowed=self.default_effect == PolicyEffect.ALLOW,
            reason="No matching policy rule",
            matched_rule=None
        )
    
    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        context: Dict
    ) -> Tuple[List[str], List[str]]:
        """Evaluate rule conditions."""
        met = []
        failed = []
        
        for cond_type, expected in conditions.items():
            actual = context.get(cond_type)
            
            if cond_type == "time_of_day":
                # expected: ("09:00", "17:00")
                if actual:
                    hour = datetime.now().hour
                    start, end = expected
                    start_h = int(start.split(":")[0])
                    end_h = int(end.split(":")[0])
                    
                    if start_h <= hour < end_h:
                        met.append(cond_type)
                    else:
                        failed.append(cond_type)
            
            elif cond_type == "day_of_week":
                if actual in expected:
                    met.append(cond_type)
                else:
                    failed.append(cond_type)
            
            elif cond_type == "risk_level":
                # expected: ["low", "medium"]
                if actual in expected:
                    met.append(cond_type)
                else:
                    failed.append(cond_type)
            
            elif cond_type == "device_type":
                # actual: device type string (desktop/mobile/tablet)
                if actual in expected:
                    met.append(cond_type)
                else:
                    failed.append(cond_type)
            
            elif cond_type == "user_agent":
                # expected: substring pattern (case-insensitive)
                if actual and expected.lower() in actual.lower():
                    met.append(cond_type)
                else:
                    failed.append(cond_type)
            
            elif cond_type == "purpose":
                if actual == expected:
                    met.append(cond_type)
                else:
                    failed.append(cond_type)
            
            else:
                # Unknown condition type - assume met
                met.append(cond_type)
        
        return met, failed
    
    def _check_ip_in_range(self, ip: str, spec: Dict) -> bool:
        """Check if IP is within allowed range."""
        try:
            import ipaddress
            
            if "cidr" in spec:
                network = ipaddress.ip_network(spec["cidr"], strict=False)
                return ipaddress.ip_address(ip) in network
            
            elif "range" in spec:
                start, end = spec["range"]
                start_ip = ipaddress.ip_address(start)
                end_ip = ipaddress.ip_address(end)
                ip_val = ipaddress.ip_address(ip)
                return start_ip <= ip_val <= end_ip
            
            return False
        except Exception:
            return False
    
    def _get_geo_from_ip(self, ip: str) -> Optional[Dict]:
        """Get geo-location data from IP address."""
        if not GEOIP_ENABLED or not geoip_reader:
            return None
        
        try:
            response = geoip_reader.city(ip)
            return {
                "country": response.country.iso_code,
                "region": response.subdivisions.most_specific.iso_code if response.subdivisions else None,
                "city": response.city.name,
                "latitude": response.location.latitude,
                "longitude": response.location.longitude
            }
        except AddressNotFoundError:
            return None
        except Exception:
            return None
    
    def _check_geo_match(self, geo_data: Optional[Dict], expected: Dict) -> bool:
        """Check if geo data matches expected constraints."""
        if not geo_data:
            return False
        
        # Country check
        if "country" in expected:
            if geo_data.get("country") != expected["country"]:
                return False
        
        # Region/state check
        if "region" in expected:
            if geo_data.get("region") != expected["region"]:
                return False
        
        # Radius check (bounding box or haversine)
        if "radius_km" in expected and "lat" in expected and "lon" in expected:
            # Haversine distance
            import math
            R = 6371  # Earth radius km
            
            lat1 = geo_data["latitude"]
            lon1 = geo_data["longitude"]
            lat2 = expected["lat"]
            lon2 = expected["lon"]
            
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat/2)**2 +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                 math.sin(dlon/2)**2)
            c = 2 * math.asin(math.sqrt(a))
            distance = R * c
            
            if distance > expected["radius_km"]:
                return False
        
        return True
    
    def _check_rate_limit(
        self,
        subject_id: str,
        resource: ResourceType,
        minute_limit: Optional[int],
        daily_limit: Optional[int]
    ) -> Dict:
        """Check rate limits."""
        now = datetime.utcnow()
        key = f"{subject_id}:{resource.value}"
        
        if key not in self.usage:
            self.usage[key] = []
        
        records = self.usage[key]
        
        # Reset if needed
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)
        
        # Filter to current window
        records = [
            r for r in records
            if datetime.fromisoformat(r.last_reset) > minute_ago
        ]
        
        minute_count = len(records)
        daily_count = len([
            r for r in self.usage[key]
            if datetime.fromisoformat(r.last_reset) > day_ago
        ])
        
        # Check limits
        if minute_limit and minute_count >= minute_limit:
            return {
                "allowed": False,
                "reason": f"Minute limit {minute_limit} exceeded"
            }
        
        if daily_limit and daily_count >= daily_limit:
            return {
                "allowed": False,
                "reason": f"Daily limit {daily_limit} exceeded"
            }
        
        # Record usage
        records.append(UsageRecord(
            user_id=subject_id,
            resource=resource,
            count=minute_count + 1,
            last_reset=now.isoformat()
        ))
        self.usage[key] = records
        
        remaining = None
        if minute_limit:
            remaining = minute_limit - minute_count - 1
        
        return {
            "allowed": True,
            "remaining": remaining
        }
    
    def get_policy_report(self) -> Dict:
        """Get policy report."""
        return {
            "total_rules": len(self.rules),
            "default_effect": self.default_effect.value,
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "effect": r.effect.value,
                    "priority": r.priority,
                    "enabled": r.enabled,
                    "resources": [res.value for res in r.resources],
                    "subject_types": [st.value for st in r.subject_types]
                }
                for r in self.rules
            ]
        }
    
    def can_enroll(
        self,
        subject_id: str,
        subject_type: SubjectType,
        target_person_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> PolicyDecision:
        """Check if subject can enroll target person."""
        # Special rule: users can only enroll themselves
        if subject_type == SubjectType.USER and target_person_id:
            if target_person_id != subject_id:
                return PolicyDecision(
                    effect=PolicyEffect.DENY,
                    allowed=False,
                    reason="Users can only enroll themselves",
                    matched_rule="user_self_enroll_only"
                )
        
        return self.evaluate(subject_id, subject_type, ResourceType.ENROLL, context)
    
    def can_recognize(
        self,
        subject_id: str,
        subject_type: SubjectType,
        target_person_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> PolicyDecision:
        """Check if subject can recognize target person."""
        # Special rule: cross-user recognition requires elevated permissions
        if target_person_id and target_person_id != subject_id:
            if subject_type not in [SubjectType.ADMIN, SubjectType.OPERATOR]:
                return PolicyDecision(
                    effect=PolicyEffect.DENY,
                    allowed=False,
                    reason="Cross-user recognition requires operator access",
                    matched_rule="cross_user_restriction"
                )
        
        return self.evaluate(subject_id, subject_type, ResourceType.RECOGNIZE, context)


# Global policy engine
policy_engine = PolicyEngine()


def get_policy_engine() -> PolicyEngine:
    """Get the global policy engine."""
    return policy_engine