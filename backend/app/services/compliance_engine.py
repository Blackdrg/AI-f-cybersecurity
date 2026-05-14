"""
Compliance & Enterprise Readiness Module
SOC2, ISO 27001, FIPS validation, data retention, security documentation.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ComplianceFramework(Enum):
    """Supported compliance frameworks."""
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    FIPS140_2 = "FIPS140-2"
    FIPS140_3 = "FIPS140-3"
    GDPR = "GDPR"
    CCPA = "CCPA"
    HIPAA = "HIPAA"
    FEDRAMP = "FedRAMP"
    PCI_DSS = "PCI-DSS"


class ControlStatus(Enum):
    """Status of a compliance control."""
    IMPLEMENTED = "implemented"
    IN_PROGRESS = "in_progress"
    PLANNED = "planned"
    NOT_APPLICABLE = "not_applicable"
    GAP = "gap"


@dataclass
class ComplianceControl:
    """Single compliance control item."""
    control_id: str
    framework: str
    description: str
    status: str
    evidence: Optional[str] = None
    last_reviewed: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "framework": self.framework,
            "description": self.description,
            "status": self.status,
            "evidence": self.evidence,
            "last_reviewed": self.last_reviewed,
            "owner": self.owner,
            "notes": self.notes
        }


class ComplianceEngine:
    """Engine for managing compliance controls and audit readiness."""

    def __init__(self):
        self.controls: Dict[str, ComplianceControl] = {}
        self._load_default_controls()

    def _load_default_controls(self):
        """Load default compliance controls for all frameworks."""
        # SOC2 Trust Service Criteria
        soc2_controls = [
            ComplianceControl(
                control_id="SOC2-CC1.1",
                framework="SOC2",
                description="COSO Principle 1: Demonstrate commitment to integrity and ethical values",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="Code of conduct document, employee training records",
                owner="Legal/Compliance"
            ),
            ComplianceControl(
                control_id="SOC2-CC1.2",
                framework="SOC2",
                description="COSO Principle 2: Board exercises oversight responsibility",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="Board meeting minutes, governance documentation",
                owner="Executive Team"
            ),
            ComplianceControl(
                control_id="SOC2-CC3.1",
                framework="SOC2",
                description="COSO Principle 7: Identify and analyze risks",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="Risk assessment framework, threat modeling documentation",
                owner="Security Team"
            ),
            ComplianceControl(
                control_id="SOC2-CC5.1",
                framework="SOC2",
                description="COSO Principle 13: Evaluate and communicate deficiencies",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="Incident response procedures, audit log system",
                owner="Security Team"
            ),
            ComplianceControl(
                control_id="SOC2-CC6.1",
                framework="SOC2",
                description="Logical and physical access controls",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="RBAC implementation, encryption at rest and in transit, MFA",
                owner="Engineering"
            ),
            ComplianceControl(
                control_id="SOC2-CC6.2",
                framework="SOC2",
                description="Prior to issuing system credentials, register and authorize new users",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="User provisioning via Okta, automated onboarding workflows",
                owner="Engineering"
            ),
            ComplianceControl(
                control_id="SOC2-CC7.1",
                framework="SOC2",
                description="Detect and monitor for security anomalies",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="SIEM integration (Splunk, Sentinel), anomaly detection, alerting system",
                owner="Security Operations"
            ),
            ComplianceControl(
                control_id="SOC2-CC7.2",
                framework="SOC2",
                description="Monitor system components for anomalies indicating malicious acts",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="db_monitor.py with Prometheus metrics, real-time alerting",
                owner="Security Operations"
            ),
            ComplianceControl(
                control_id="SOC2-CC7.3",
                framework="SOC2",
                description="Evaluate security events and determine if they are incidents",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="SOAR engine, incident response playbooks, alert rules engine",
                owner="Incident Response Team"
            ),
            ComplianceControl(
                control_id="SOC2-CC7.4",
                framework="SOC2",
                description="Respond to identified security incidents",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="IncidentResponseEngine with automated playbooks, connector engine",
                owner="Incident Response Team"
            ),
            ComplianceControl(
                control_id="SOC2-CC7.5",
                framework="SOC2",
                description="Identify, analyze, and recover from security incidents",
                status=ControlStatus.IN_PROGRESS.value,
                evidence="Recovery procedures documented, backup infrastructure in place",
                owner="Incident Response Team"
            ),
            ComplianceControl(
                control_id="SOC2-CC8.1",
                framework="SOC2",
                description="Authorize, design, develop, configure, document, test, approve, and implement changes",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="CI/CD pipeline, code review process, change management documentation",
                owner="Engineering"
            ),
            ComplianceControl(
                control_id="SOC2-CC9.1",
                framework="SOC2",
                description="Mitigate risk from business disruptions through controls like backup and recovery",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="PITR configuration, database replication, backup procedures",
                owner="Infrastructure Team"
            ),
        ]

        # ISO 27001:2022 Controls (key subset)
        iso27001_controls = [
            ComplianceControl(
                control_id="ISO27001-A.5.1",
                framework="ISO27001",
                description="Policies for information security",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="Information security policy document",
                owner="CISO"
            ),
            ComplianceControl(
                control_id="ISO27001-A.5.2",
                framework="ISO27001",
                description="Information security roles and responsibilities",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="RACI matrix, org chart with security roles",
                owner="HR/Security"
            ),
            ComplianceControl(
                control_id="ISO27001-A.6.1",
                framework="ISO27001",
                description="Screening of personnel",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="Background check procedures, Okta identity verification",
                owner="HR"
            ),
            ComplianceControl(
                control_id="ISO27001-A.8.1",
                framework="ISO27001",
                description="User endpoint devices security",
                status=ControlStatus.IN_PROGRESS.value,
                evidence="MDM enrollment policy, device encryption requirements",
                owner="IT Security"
            ),
            ComplianceControl(
                control_id="ISO27001-A.8.2",
                framework="ISO27001",
                description="Privileged access rights management",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="RBAC, MFA, session management, API key rotation",
                owner="Engineering"
            ),
            ComplianceControl(
                control_id="ISO27001-A.8.3",
                framework="ISO27001",
                description="Information access restriction",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="Tenant isolation, encryption, access controls",
                owner="Engineering"
            ),
            ComplianceControl(
                control_id="ISO27001-A.8.24",
                framework="ISO27001",
                description="Use of cryptography",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="AES-256-GCM encryption, PQC support, key rotation",
                owner="Engineering"
            ),
            ComplianceControl(
                control_id="ISO27001-A.8.25",
                framework="ISO27001",
                description="Secure development lifecycle",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="SDLC documentation, code reviews, SAST/DAST tools",
                owner="Engineering"
            ),
            ComplianceControl(
                control_id="ISO27001-A.8.28",
                framework="ISO27001",
                description="Secure coding practices",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="Coding standards, static analysis, security training",
                owner="Engineering"
            ),
            ComplianceControl(
                control_id="ISO27001-A.5.24",
                framework="ISO27001",
                description="Information security incident management planning",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="SOAR engine, incident response runbooks, escalation procedures",
                owner="CISO"
            ),
            ComplianceControl(
                control_id="ISO27001-A.5.26",
                framework="ISO27001",
                description="Response to information security incidents",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="IncidentResponseEngine, automated playbooks, escalation",
                owner="Incident Response Team"
            ),
            ComplianceControl(
                control_id="ISO27001-A.5.29",
                framework="ISO27001",
                description="Information security during disruption",
                status=ControlStatus.IN_PROGRESS.value,
                evidence="DB replication, failover, 72h uptime testing, BCP",
                owner="Infrastructure Team"
            ),
            ComplianceControl(
                control_id="ISO27001-A.5.31",
                framework="ISO27001",
                description="Legal, statutory, regulatory and contractual requirements",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="GDPR/CCPA compliance module, audit trail system",
                owner="Legal/Compliance"
            ),
        ]

        # FIPS 140-2/3 Controls
        fips_controls = [
            ComplianceControl(
                control_id="FIPS-140-2-VAL",
                framework="FIPS140-2",
                description="Cryptographic module validation (FIPS 140-2)",
                status=ControlStatus.GAP.value,
                evidence="Requires FIPS-validated crypto module (CMVP certificate)",
                owner="Security Team",
                notes="OpenSSL FIPS module or AWS CloudHSM recommended"
            ),
            ComplianceControl(
                control_id="FIPS-140-3-VAL",
                framework="FIPS140-3",
                description="Cryptographic module validation (FIPS 140-3)",
                status=ControlStatus.PLANNED.value,
                evidence="Migration plan to FIPS 140-3 validated modules",
                owner="Security Team",
                notes="FIPS 140-3 transition deadline: 2026-04-01"
            ),
            ComplianceControl(
                control_id="FIPS-ALG-USE",
                framework="FIPS140-2",
                description="Use of FIPS-approved algorithms",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="AES-256-GCM for encryption, SHA-256/384/512 for hashing",
                owner="Engineering"
            ),
            ComplianceControl(
                control_id="FIPS-PQC-READY",
                framework="FIPS140-3",
                description="Post-quantum cryptography readiness",
                status=ControlStatus.IN_PROGRESS.value,
                evidence="PQC module with Kyber and Dilithium, NIST PQC standardization",
                owner="Security Team"
            ),
        ]

        # Data Retention Controls
        data_retention_controls = [
            ComplianceControl(
                control_id="DATA-RETENTION-01",
                framework="ALL",
                description="Data retention policy enforcement",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="enforce_data_retention Celery task, configurable retention periods",
                owner="Compliance Team"
            ),
            ComplianceControl(
                control_id="DATA-RETENTION-02",
                framework="GDPR",
                description="Right to erasure (Article 17)",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="GDPR deletion endpoint, audit chain removal, anonymization",
                owner="Compliance Team"
            ),
            ComplianceControl(
                control_id="DATA-RETENTION-03",
                framework="CCPA",
                description="Right to deletion (CCPA Section 1798.105)",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="CCPA deletion workflow, DSAR processing pipeline",
                owner="Compliance Team"
            ),
            ComplianceControl(
                control_id="DATA-RETENTION-04",
                framework="SOC2",
                description="Data classification and handling",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="Data classification schema, PII detection, encryption at rest",
                owner="Security Team"
            ),
            ComplianceControl(
                control_id="DATA-RETENTION-05",
                framework="ALL",
                description="Automated data lifecycle management",
                status=ControlStatus.IMPLEMENTED.value,
                evidence="Celery beat tasks for retention enforcement, IOC expiration",
                owner="Engineering"
            ),
        ]

        all_controls = soc2_controls + iso27001_controls + fips_controls + data_retention_controls

        for control in all_controls:
            self.controls[control.control_id] = control

    def get_controls_by_framework(self, framework: str) -> List[ComplianceControl]:
        """Get all controls for a specific framework."""
        return [
            c for c in self.controls.values()
            if c.framework == framework
        ]

    def get_control(self, control_id: str) -> Optional[ComplianceControl]:
        """Get a specific control by ID."""
        return self.controls.get(control_id)

    def update_control_status(self, control_id: str, status: str,
                               evidence: str = None, notes: str = None):
        """Update the status of a compliance control."""
        if control_id in self.controls:
            self.controls[control_id].status = status
            if evidence:
                self.controls[control_id].evidence = evidence
            if notes:
                self.controls[control_id].notes = notes
            self.controls[control_id].last_reviewed = datetime.utcnow().isoformat()

    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get summary statistics for compliance posture."""
        summary = {}
        for framework in [f.value for f in ComplianceFramework]:
            controls = self.get_controls_by_framework(framework)
            if not controls:
                continue
            status_counts = {}
            for status in ControlStatus:
                status_counts[status.value] = sum(
                    1 for c in controls if c.status == status.value
                )
            summary[framework] = {
                "total_controls": len(controls),
                "status_breakdown": status_counts,
                "implementable_score": (
                    (status_counts.get("implemented", 0) +
                     status_counts.get("in_progress", 0) * 0.5) /
                    len(controls) * 100
                )
            }
        return summary

    def get_gaps(self) -> List[ComplianceControl]:
        """Get all controls with GAP status."""
        return [c for c in self.controls.values() if c.status == ControlStatus.GAP.value]

    def generate_audit_report(self, framework: str = "SOC2") -> Dict[str, Any]:
        """Generate audit-ready report for a specific framework."""
        controls = self.get_controls_by_framework(framework)
        return {
            "framework": framework,
            "report_generated": datetime.utcnow().isoformat(),
            "total_controls": len(controls),
            "controls": [c.to_dict() for c in controls],
            "summary": {
                "implemented": sum(1 for c in controls if c.status == "implemented"),
                "in_progress": sum(1 for c in controls if c.status == "in_progress"),
                "planned": sum(1 for c in controls if c.status == "planned"),
                "gaps": sum(1 for c in controls if c.status == "gap"),
            }
        }


class DataRetentionPolicy:
    """Manages data retention policies for compliance."""

    DEFAULT_POLICIES = {
        "recognition_events": {"retention_days": 365, "anonymize_on_delete": True},
        "enrollment_data": {"retention_days": 730, "anonymize_on_delete": True},
        "audit_logs": {"retention_days": 2555, "anonymize_on_delete": False},  # 7 years
        "biometric_templates": {"retention_days": 730, "anonymize_on_delete": True},
        "threat_intel": {"retention_days": 180, "anonymize_on_delete": False},
        "sessions": {"retention_days": 30, "anonymize_on_delete": True},
        "temp_files": {"retention_days": 7, "anonymize_on_delete": True},
    }

    def __init__(self):
        self.policies = dict(self.DEFAULT_POLICIES)
        self._load_custom_policies()

    def _load_custom_policies(self):
        """Load custom retention policies from environment."""
        for data_type, policy in self.policies.items():
            env_key = f"RETENTION_{data_type.upper()}_DAYS"
            if env_key in os.environ:
                policy["retention_days"] = int(os.environ[env_key])

    def get_policy(self, data_type: str) -> Dict[str, Any]:
        """Get retention policy for a data type."""
        return self.policies.get(data_type, {
            "retention_days": 365,
            "anonymize_on_delete": True
        })

    def get_expiry_date(self, data_type: str, created_at: datetime = None) -> datetime:
        """Calculate expiry date for data."""
        policy = self.get_policy(data_type)
        days = policy["retention_days"]
        if created_at is None:
            created_at = datetime.utcnow()
        return created_at + timedelta(days=days)

    def get_all_expiry_dates(self) -> Dict[str, Dict[str, Any]]:
        """Get all expiry dates for compliance dashboard."""
        result = {}
        for data_type, policy in self.policies.items():
            result[data_type] = {
                "retention_days": policy["retention_days"],
                "anonymize_on_delete": policy["anonymize_on_delete"],
                "sample_expiry": self.get_expiry_date(data_type).isoformat()
            }
        return result


class SecurityDocumentation:
    """Generates and manages security documentation."""

    @staticmethod
    def get_documentation_index() -> Dict[str, str]:
        """Get index of all security documentation."""
        return {
            "architecture_overview": "docs/security/architecture.md",
            "threat_model": "docs/security/threat_model.md",
            "data_flow_diagram": "docs/security/data_flow.md",
            "access_control": "docs/security/access_control.md",
            "encryption_standards": "docs/security/encryption.md",
            "incident_response": "docs/security/incident_response.md",
            "compliance_matrix": "docs/security/compliance_matrix.md",
            "privacy_policy": "docs/security/privacy_policy.md",
            "api_security": "docs/security/api_security.md",
            "audit_procedures": "docs/security/audit_procedures.md",
        }

    @staticmethod
    def get_incident_response_runbook() -> Dict[str, Any]:
        """Return incident response runbook."""
        return {
            "version": "2.0",
            "last_updated": datetime.utcnow().isoformat(),
            "phases": {
                "1_detection": {
                    "description": "Threat detection and initial triage",
                    "actions": [
                        "Alert received from monitoring/alerting system",
                        "Verify alert is not false positive",
                        "Classify severity level",
                        "Assign to incident response team"
                    ],
                    "sla": "15 minutes"
                },
                "2_containment": {
                    "description": "Contain the incident scope",
                    "actions": [
                        "Isolate affected systems",
                        "Block malicious IPs/domains",
                        "Disable compromised accounts",
                        "Preserve forensic evidence"
                    ],
                    "sla": "1 hour"
                },
                "3_eradication": {
                    "description": "Remove threat from environment",
                    "actions": [
                        "Identify root cause",
                        "Remove malware/backdoors",
                        "Patch vulnerabilities",
                        "Validate cleanup"
                    ],
                    "sla": "4 hours"
                },
                "4_recovery": {
                    "description": "Restore normal operations",
                    "actions": [
                        "Restore from clean backups",
                        "Re-enable systems incrementally",
                        "Monitor for recurrence",
                        "Validate system integrity"
                    ],
                    "sla": "8 hours"
                },
                "5_lessons_learned": {
                    "description": "Post-incident review and improvement",
                    "actions": [
                        "Conduct post-mortem meeting",
                        "Document findings and recommendations",
                        "Update procedures and playbooks",
                        "Implement preventive measures"
                    ],
                    "sla": "48 hours"
                }
            },
            "escalation_contacts": {
                "security_team": os.getenv("SECURITY_TEAM_CONTACT", "security@company.com"),
                "ciso": os.getenv("CISO_CONTACT", "ciso@company.com"),
                "legal": os.getenv("LEGAL_CONTACT", "legal@company.com"),
                "external_ir": os.getenv("EXTERNAL_IR_CONTACT", None)
            }
        }


def get_compliance_engine() -> ComplianceEngine:
    """Get compliance engine singleton."""
    return ComplianceEngine()


def get_data_retention_policy() -> DataRetentionPolicy:
    """Get data retention policy singleton."""
    return DataRetentionPolicy()


def check_compliance_readiness() -> Dict[str, Any]:
    """Check overall compliance readiness."""
    engine = get_compliance_engine()
    policy = get_data_retention_policy()

    compliance_matrix = engine.get_compliance_summary()
    gaps = engine.get_gaps()
    retention_config = policy.get_all_expiry_dates()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "frameworks": compliance_matrix,
        "identified_gaps": [g.to_dict() for g in gaps],
        "retention_configured": retention_config,
        "readiness_score": calculate_readiness_score(compliance_matrix),
        "recommendations": generate_recommendations(gaps)
    }


def calculate_readiness_score(frameworks: Dict[str, Any]) -> float:
    """Calculate overall readiness score."""
    if not frameworks:
        return 0.0
    scores = [f.get("implementable_score", 0) for f in frameworks.values()]
    return round(sum(scores) / len(scores), 2)


def generate_recommendations(gaps: List[ComplianceControl]) -> List[str]:
    """Generate actionable recommendations based on gaps."""
    recommendations = []
    for gap in gaps:
        if "FIPS" in gap.framework:
            recommendations.append(
                f"[{gap.control_id}] Engage with cloud provider for FIPS-validated "
                f"cryptographic modules. Consider AWS CloudHSM or Azure Dedicated HSM."
            )
    if not recommendations:
        recommendations.append("No critical gaps requiring immediate action.")
    return recommendations