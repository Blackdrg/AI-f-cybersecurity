"""
Ethical Governance Engine.

Implements real-time ethical decision filtering, policy-as-code,
and regulatory compliance for AI systems.
"""

import json
import hashlib
import yaml
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
import re


class EthicalViolationLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyEffect(Enum):
    ALLOW = "allow"
    DENY = "deny"
    AUDIT = "audit"
    REQUIRE_REVIEW = "require_review"


@dataclass
class PolicyRule:
    """Policy-as-code rule."""
    rule_id: str
    name: str
    description: str
    effect: PolicyEffect
    conditions: Dict[str, Any]
    priority: int = 0
    enabled: bool = True
    jurisdiction: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class EthicalDecision:
    """Result of ethical evaluation."""
    request_id: str
    timestamp: str
    approved: bool
    effect: PolicyEffect
    matched_rules: List[str]
    violations: List[Dict[str, Any]]
    risk_score: float
    explanation: str
    requires_human_review: bool
    jurisdiction: Optional[str]
    metadata: Dict[str, Any]


class EthicalGovernor:
    """
    Enhanced ethical governance with policy-as-code support.
    """
    
    def __init__(self):
        # Policy storage
        self.policies: Dict[str, PolicyRule] = {}
        self.jurisdiction_policies: Dict[str, List[str]] = {}
        
        # Default policies
        self._init_default_policies()
        
        # Audit trail
        self.decision_log: List[EthicalDecision] = []
        
        # Regulatory configurations
        self.regulatory_modes = {
            "gdpr": self._gdpr_config(),
            "ccpa": self._ccpa_config(),
            "hipaa": self._hipaa_config(),
            "strict": self._strict_config(),
            "default": self._default_config()
        }
        
        # Active regulatory mode
        self.active_mode = "default"
    
    def _init_default_policies(self):
        """Initialize default ethical policies."""
        default_policies = [
            PolicyRule(
                rule_id="age_restriction",
                name="Age Restriction Policy",
                description="Restrict enrollment based on age",
                effect=PolicyEffect.DENY,
                conditions={
                    "field": "age",
                    "operator": "range",
                    "min": 18,
                    "max": 100
                },
                priority=100,
                tags=["age", "privacy"]
            ),
            PolicyRule(
                rule_id="minor_protection",
                name="Minor Protection Policy",
                description="Block processing of minors' biometrics",
                effect=PolicyEffect.DENY,
                conditions={
                    "field": "age",
                    "operator": "lt",
                    "value": 18
                },
                priority=200,
                tags=["minors", "protection"]
            ),
            PolicyRule(
                rule_id="content_filter",
                name="Content Filter Policy",
                description="Filter forbidden content in metadata",
                effect=PolicyEffect.DENY,
                conditions={
                    "type": "content_filter",
                    "patterns": [
                        r'child|minor|underage',
                        r'violence|weapon|harm',
                        r'illegal|criminal',
                        r'discrimination|hate'
                    ]
                },
                priority=150,
                tags=["content", "safety"]
            ),
            PolicyRule(
                rule_id="consent_required",
                name="Consent Requirement Policy",
                description="Require explicit consent for biometric processing",
                effect=PolicyEffect.DENY,
                conditions={
                    "field": "consent",
                    "operator": "equals",
                    "value": True
                },
                priority=90,
                tags=["consent", "privacy"]
            ),
            PolicyRule(
                rule_id="bulk_limit",
                name="Bulk Operation Limit",
                description="Limit bulk operations to prevent abuse",
                effect=PolicyEffect.REQUIRE_REVIEW,
                conditions={
                    "field": "bulk_size",
                    "operator": "gt",
                    "value": 100
                },
                priority=50,
                tags=["bulk", "rate_limit"]
            ),
            PolicyRule(
                rule_id="high_risk_block",
                name="High Risk Block",
                description="Block high-risk operations",
                effect=PolicyEffect.DENY,
                conditions={
                    "field": "risk_score",
                    "operator": "gt",
                    "value": 0.8
                },
                priority=95,
                tags=["risk", "security"]
            )
        ]
        
        for policy in default_policies:
            self.add_policy(policy)
    
    def _gdpr_config(self) -> Dict[str, Any]:
        return {
            "name": "GDPR",
            "jurisdiction": "EU",
            "biometric_special_category": True,
            "explicit_consent_required": True,
            "data_minimization": True,
            "right_to_erasure": True,
            "right_to_portability": True,
            "breach_notification_hours": 72,
            "age_consent": 16,
            "cross_border_restrictions": True
        }
    
    def _ccpa_config(self) -> Dict[str, Any]:
        return {
            "name": "CCPA",
            "jurisdiction": "US-CA",
            "opt_out_required": True,
            "right_to_delete": True,
            "right_to_know": True,
            "discrimination_protection": True,
            "age_consent": 13
        }
    
    def _hipaa_config(self) -> Dict[str, Any]:
        return {
            "name": "HIPAA",
            "jurisdiction": "US",
            "health_data_protection": True,
            "business_associate_agreements": True,
            "minimum_necessary": True,
            "breach_notification_days": 60
        }
    
    def _strict_config(self) -> Dict[str, Any]:
        return {
            "name": "STRICT",
            "enhanced_consent": True,
            "age_consent": 21,
            "biometric_retention_days": 90,
            "enhanced_audit": True,
            "human_review_threshold": 0.5,
            "cross_border_block": True
        }
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            "name": "DEFAULT",
            "age_consent": 18,
            "biometric_retention_days": 365,
            "consent_required": True,
            "audit_enabled": True
        }
    
    def set_regulatory_mode(self, mode: str) -> bool:
        """
        Set the active regulatory compliance mode.
        
        Args:
            mode: Regulatory mode (gdpr, ccpa, hipaa, strict, default)
        
        Returns:
            True if mode was set
        """
        if mode in self.regulatory_modes:
            self.active_mode = mode
            # Apply policies for this mode
            self._apply_regulatory_policies(mode)
            return True
        return False
    
    def _apply_regulatory_policies(self, mode: str):
        """Apply policies for a regulatory mode."""
        config = self.regulatory_modes[mode]
        
        # Remove existing jurisdiction-specific policies
        self.policies = {
            k: v for k, v in self.policies.items()
            if not v.jurisdiction or v.jurisdiction != config["jurisdiction"]
        }
        
        # Add mode-specific policies
        mode_policies = self._generate_mode_policies(config)
        for policy in mode_policies:
            self.add_policy(policy)
    
    def _generate_mode_policies(self, config: Dict[str, Any]) -> List[PolicyRule]:
        """Generate policies based on regulatory configuration."""
        policies = []
        jurisdiction = config.get("jurisdiction", "")
        
        # Age restriction policy
        if "age_consent" in config:
            policies.append(PolicyRule(
                rule_id=f"age_{jurisdiction}",
                name=f"{config['name']} Age Policy",
                description=f"Age restriction for {config['name']}",
                effect=PolicyEffect.DENY,
                conditions={
                    "field": "age",
                    "operator": "lt",
                    "value": config["age_consent"]
                },
                priority=200,
                jurisdiction=jurisdiction,
                tags=["age", jurisdiction]
            ))
        
        # Biometric consent policy
        if config.get("explicit_consent_required") or config.get("enhanced_consent"):
            policies.append(PolicyRule(
                rule_id=f"consent_{jurisdiction}",
                name=f"{config['name']} Consent Policy",
                description="Explicit consent required",
                effect=PolicyEffect.DENY,
                conditions={
                    "field": "consent_type",
                    "operator": "in",
                    "value": ["explicit", "written"]
                },
                priority=180,
                jurisdiction=jurisdiction,
                tags=["consent", jurisdiction]
            ))
        
        # Retention policy
        if "biometric_retention_days" in config:
            policies.append(PolicyRule(
                rule_id=f"retention_{jurisdiction}",
                name=f"{config['name']} Retention Policy",
                description="Biometric data retention limit",
                effect=PolicyEffect.AUDIT,
                conditions={
                    "field": "retention_days",
                    "operator": "gt",
                    "value": config["biometric_retention_days"]
                },
                priority=170,
                jurisdiction=jurisdiction,
                tags=["retention", jurisdiction]
            ))
        
        return policies
    
    def add_policy(self, policy: PolicyRule) -> bool:
        """
        Add a policy rule.
        
        Args:
            policy: Policy rule to add
        
        Returns:
            True if added successfully
        """
        self.policies[policy.rule_id] = policy
        
        # Index by jurisdiction
        if policy.jurisdiction:
            if policy.jurisdiction not in self.jurisdiction_policies:
                self.jurisdiction_policies[policy.jurisdiction] = []
            self.jurisdiction_policies[policy.jurisdiction].append(policy.rule_id)
        
        return True
    
    def remove_policy(self, rule_id: str) -> bool:
        """
        Remove a policy rule.
        
        Args:
            rule_id: ID of policy to remove
        
        Returns:
            True if removed
        """
        if rule_id in self.policies:
            policy = self.policies[rule_id]
            del self.policies[rule_id]
            
            # Remove from jurisdiction index
            if policy.jurisdiction:
                self.jurisdiction_policies[policy.jurisdiction] = [
                    pid for pid in self.jurisdiction_policies.get(policy.jurisdiction, [])
                    if pid != rule_id
                ]
            
            return True
        return False
    
    def check_request(
        self,
        request_data: Dict[str, Any],
        user_role: str = "user",
        jurisdiction: Optional[str] = None
    ) -> EthicalDecision:
        """
        Check if request complies with ethical guidelines.
        
        Args:
            request_data: Request data to evaluate
            user_role: Role of the requesting user
            jurisdiction: Applicable jurisdiction
        
        Returns:
            EthicalDecision with evaluation results
        """
        request_id = f"ethical:{hashlib.sha256(json.dumps(request_data, sort_keys=True).encode()).hexdigest()[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Get applicable policies
        applicable_policies = self._get_applicable_policies(jurisdiction)
        
        matched_rules = []
        violations = []
        risk_score = 0.0
        max_priority_effect = PolicyEffect.ALLOW
        
        for policy in applicable_policies:
            if not policy.enabled:
                continue
            
            if self._evaluate_policy(policy, request_data):
                matched_rules.append(policy.rule_id)
                risk_score += self._calculate_policy_risk(policy)
                
                if policy.priority > self._get_effect_priority(max_priority_effect):
                    max_priority_effect = policy.effect
                
                if policy.effect in [PolicyEffect.DENY, PolicyEffect.REQUIRE_REVIEW]:
                    violations.append({
                        "rule_id": policy.rule_id,
                        "rule_name": policy.name,
                        "effect": policy.effect.value,
                        "conditions": policy.conditions,
                        "priority": policy.priority
                    })
        
        # Role-based checks
        role_violation = self._check_role_restrictions(user_role, request_data)
        if role_violation:
            violations.append(role_violation)
            risk_score += 0.3
        
        # Final decision
        approved, effect, requires_review = self._determine_approval(
            max_priority_effect, violations, risk_score
        )
        
        explanation = self._generate_explanation(
            effect, matched_rules, violations, approved
        )
        
        decision = EthicalDecision(
            request_id=request_id,
            timestamp=timestamp,
            approved=approved,
            effect=effect,
            matched_rules=matched_rules,
            violations=violations,
            risk_score=min(risk_score, 1.0),
            explanation=explanation,
            requires_human_review=requires_review,
            jurisdiction=jurisdiction,
            metadata={
                "user_role": user_role,
                "policy_count": len(applicable_policies),
                "regulatory_mode": self.active_mode
            }
        )
        
        # Log decision
        self.decision_log.append(decision)
        
        return decision
    
    def _get_applicable_policies(self, jurisdiction: Optional[str]) -> List[PolicyRule]:
        """Get policies applicable to the given jurisdiction."""
        policies = list(self.policies.values())
        
        # Filter by jurisdiction if specified
        if jurisdiction:
            policies = [
                p for p in policies
                if p.jurisdiction is None or p.jurisdiction == jurisdiction
            ]
        
        # Sort by priority (highest first)
        policies.sort(key=lambda p: p.priority, reverse=True)
        
        return policies
    
    def _evaluate_policy(self, policy: PolicyRule, data: Dict[str, Any]) -> bool:
        """
        Evaluate if a policy applies to the given data.
        
        Returns True if policy conditions are met (i.e., policy should trigger).
        """
        conditions = policy.conditions
        
        # Content filter
        if conditions.get("type") == "content_filter":
            return self._evaluate_content_filter(conditions, data)
        
        # Field-based conditions
        field = conditions.get("field")
        if field and field in data:
            value = data[field]
            operator = conditions.get("operator")
            target = conditions.get("value")
            
            return self._evaluate_condition(value, operator, target)
        
        # Range conditions
        if conditions.get("operator") == "range":
            field = conditions.get("field")
            if field and field in data:
                value = data[field]
                min_val = conditions.get("min")
                max_val = conditions.get("max")
                return not (min_val <= value <= max_val)  # DENY if outside range
        
        return False
    
    def _evaluate_content_filter(self, conditions: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate content filter conditions."""
        patterns = conditions.get("patterns", [])
        
        for metadata_key, metadata_value in data.items():
            if isinstance(metadata_value, str):
                for pattern in patterns:
                    if re.search(pattern, metadata_value, re.IGNORECASE):
                        return True
        
        return False
    
    def _evaluate_condition(self, value: Any, operator: str, target: Any) -> bool:
        """Evaluate a single condition."""
        if operator == "equals":
            return value == target
        elif operator == "not_equals":
            return value != target
        elif operator == "gt":
            return value > target
        elif operator == "gte":
            return value >= target
        elif operator == "lt":
            return value < target
        elif operator == "lte":
            return value <= target
        elif operator == "in":
            return value in target
        elif operator == "not_in":
            return value not in target
        return False
    
    def _check_role_restrictions(self, user_role: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check role-based restrictions."""
        if user_role not in ["admin", "operator", "user"]:
            return {
                "rule_id": "invalid_role",
                "rule_name": "Invalid Role",
                "effect": PolicyEffect.DENY.value,
                "conditions": {"valid_roles": ["admin", "operator", "user"]},
                "priority": 100
            }
        
        # Cross-user access
        target_person = data.get("person_id")
        if target_person and target_person != data.get("user_id"):
            if user_role not in ["admin", "operator"]:
                return {
                    "rule_id": "cross_user_restriction",
                    "rule_name": "Cross-User Restriction",
                    "effect": PolicyEffect.DENY.value,
                    "conditions": {"allowed_roles": ["admin", "operator"]},
                    "priority": 80
                }
        
        return None
    
    def _calculate_policy_risk(self, policy: PolicyRule) -> float:
        """Calculate risk contribution from a policy."""
        risk_map = {
            PolicyEffect.DENY: 0.4,
            PolicyEffect.REQUIRE_REVIEW: 0.3,
            PolicyEffect.AUDIT: 0.1,
            PolicyEffect.ALLOW: 0.0
        }
        return risk_map.get(policy.effect, 0.0)
    
    def _get_effect_priority(self, effect: PolicyEffect) -> int:
        """Get numeric priority for effect."""
        priority_map = {
            PolicyEffect.DENY: 200,
            PolicyEffect.REQUIRE_REVIEW: 150,
            PolicyEffect.AUDIT: 100,
            PolicyEffect.ALLOW: 50
        }
        return priority_map.get(effect, 0)
    
    def _determine_approval(
        self,
        max_effect: PolicyEffect,
        violations: List[Dict[str, Any]],
        risk_score: float
    ) -> Tuple[bool, PolicyEffect, bool]:
        """
        Determine final approval decision.
        
        Returns:
            (approved, effect, requires_review)
        """
        if max_effect == PolicyEffect.DENY:
            return False, PolicyEffect.DENY, False
        elif max_effect == PolicyEffect.REQUIRE_REVIEW:
            return False, PolicyEffect.REQUIRE_REVIEW, True
        elif violations:
            return False, PolicyEffect.REQUIRE_REVIEW, True
        elif risk_score > 0.5:
            return True, PolicyEffect.AUDIT, True
        else:
            return True, PolicyEffect.ALLOW, False
    
    def _generate_explanation(
        self,
        effect: PolicyEffect,
        matched_rules: List[str],
        violations: List[Dict[str, Any]],
        approved: bool
    ) -> str:
        """Generate human-readable explanation."""
        if not matched_rules:
            return "No policies matched. Default approval."
        
        if effect == PolicyEffect.DENY:
            rule_names = ", ".join(v["rule_name"] for v in violations if v["effect"] == "deny")
            return f"Denied due to policy violations: {rule_names}"
        elif effect == PolicyEffect.REQUIRE_REVIEW:
            rule_names = ", ".join(v["rule_name"] for v in violations)
            return f"Requires review due to: {rule_names}"
        elif effect == PolicyEffect.AUDIT:
            return "Approved with enhanced audit logging"
        else:
            return f"Approved. Matched policies: {', '.join(matched_rules)}"
    
    def export_policies(self, format: str = "json") -> str:
        """
        Export policies in specified format.
        
        Args:
            format: Export format (json, yaml)
        
        Returns:
            Policy export string
        """
        policies_list = [
            {
                **asdict(policy),
                "effect": policy.effect.value
            }
            for policy in self.policies.values()
        ]
        
        if format == "yaml":
            return yaml.dump(policies_list, default_flow_style=False)
        else:
            return json.dumps(policies_list, indent=2)
    
    def import_policies(self, policies_data: str, format: str = "json") -> int:
        """
        Import policies from string.
        
        Args:
            policies_data: Policy data string
            format: Format (json, yaml)
        
        Returns:
            Number of policies imported
        """
        if format == "yaml":
            data = yaml.safe_load(policies_data)
        else:
            data = json.loads(policies_data)
        
        count = 0
        for item in data:
            if "effect" in item:
                item["effect"] = PolicyEffect(item["effect"])
            policy = PolicyRule(**item)
            self.add_policy(policy)
            count += 1
        
        return count
    
    def get_decisions(
        self,
        limit: int = 100,
        approved_only: bool = False,
        denied_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recent ethical decisions.
        
        Args:
            limit: Maximum number of decisions
            approved_only: Filter for approved decisions
            denied_only: Filter for denied decisions
        
        Returns:
            List of decision summaries
        """
        decisions = self.decision_log[-limit:]
        
        if approved_only:
            decisions = [d for d in decisions if d.approved]
        if denied_only:
            decisions = [d for d in decisions if not d.approved]
        
        return [asdict(d) for d in decisions]
    
    def get_policy_report(self) -> Dict[str, Any]:
        """
        Get comprehensive policy report.
        
        Returns:
            Policy report
        """
        by_effect = {}
        for policy in self.policies.values():
            effect = policy.effect.value
            by_effect[effect] = by_effect.get(effect, 0) + 1
        
        by_jurisdiction = {}
        for jurisdiction, policy_ids in self.jurisdiction_policies.items():
            by_jurisdiction[jurisdiction] = len(policy_ids)
        
        return {
            "total_policies": len(self.policies),
            "active_policies": len([p for p in self.policies.values() if p.enabled]),
            "by_effect": by_effect,
            "by_jurisdiction": by_jurisdiction,
            "regulatory_mode": self.active_mode,
            "total_decisions": len(self.decision_log),
            "recent_decisions": self.get_decisions(limit=10)
        }
    
    def simulate_regulatory_change(self, new_mode: str) -> Dict[str, Any]:
        """
        Simulate impact of regulatory change.
        
        Args:
            new_mode: New regulatory mode
        
        Returns:
            Impact assessment
        """
        if new_mode not in self.regulatory_modes:
            return {"error": f"Unknown regulatory mode: {new_mode}"}
        
        current_mode = self.active_mode
        current_config = self.regulatory_modes[current_mode]
        new_config = self.regulatory_modes[new_mode]
        
        impact = {
            "from_mode": current_mode,
            "to_mode": new_mode,
            "changes": {},
            "affected_policies": [],
            "recommendations": []
        }
        
        # Compare configurations
        for key in set(current_config.keys()) | set(new_config.keys()):
            if key not in ["name", "jurisdiction"]:
                current_val = current_config.get(key)
                new_val = new_config.get(key)
                if current_val != new_val:
                    impact["changes"][key] = {
                        "from": current_val,
                        "to": new_val
                    }
        
        # Identify affected policies
        for policy in self.policies.values():
            if policy.jurisdiction == new_config.get("jurisdiction"):
                impact["affected_policies"].append(policy.rule_id)
        
        # Generate recommendations
        if new_config.get("explicit_consent_required") and not current_config.get("explicit_consent_required"):
            impact["recommendations"].append("Update consent collection to explicit opt-in")
        
        if new_config.get("biometric_retention_days", 999) < current_config.get("biometric_retention_days", 999):
            impact["recommendations"].append("Plan for deletion of excess biometric data")
        
        if new_config.get("cross_border_restrictions") and not current_config.get("cross_border_restrictions"):
            impact["recommendations"].append("Implement local data processing infrastructure")
        
        return impact


# Example usage
def check_ethical_compliance(
    request_data: Dict[str, Any],
    user_role: str = "user",
    jurisdiction: Optional[str] = None
) -> EthicalDecision:
    """
    Check ethical compliance for a request.
    
    Args:
        request_data: Request data
        user_role: User role
        jurisdiction: Applicable jurisdiction
    
    Returns:
        Ethical decision
    """
    governor = EthicalGovernor()
    return governor.check_request(request_data, user_role, jurisdiction)


if __name__ == "__main__":
    # Example usage
    governor = EthicalGovernor()
    
    # Check a request
    decision = governor.check_request(
        request_data={
            "age": 17,
            "consent": False,
            "person_id": "test_person",
            "user_id": "test_user"
        },
        user_role="user",
        jurisdiction="EU"
    )
    
    print(f"Decision: {decision.approved}")
    print(f"Explanation: {decision.explanation}")
    print(f"Violations: {len(decision.violations)}")
