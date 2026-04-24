"""
Zero-Knowledge Proof Audit Trails.

Implements privacy-preserving audit logging using ZKP.
Proves that decisions were made correctly without revealing
sensitive data or decision logic.

Supports:
- ZKP of decision correctness
- Privacy-preserving audit logs
- Selective disclosure of audit data
- Compliance verification without data exposure
"""

import hashlib
import json
import base64
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
import uuid

import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PrivateFormat, NoEncryption
import numpy as np


class AuditEventType(Enum):
    """Types of audit events."""
    ENROLLMENT = "enrollment"
    RECOGNITION = "recognition"
    REVOCATION = "revocation"
    MATCHING = "matching"
    POLICY_EVALUATION = "policy_evaluation"
    BIAS_CHECK = "bias_check"
    DEEPFAKE_DETECTION = "deepfake_detection"
    CONSENT = "consent"
    ACCESS_DENIED = "access_denied"
    ETHICAL_VIOLATION = "ethical_violation"


class ProofType(Enum):
    """Types of zero-knowledge proofs."""
    ZK_SNR = "zk_schnorr"  # Schnorr protocol
    ZK_RANGE = "zk_range"  # Range proof
    ZK_SET_MEMBERSHIP = "zk_set_membership"  # Set membership
    ZK_COMPARISON = "zk_comparison"  # Comparison proof
    SIMULATED = "simulated"  # Simulation mode


@dataclass
class ZKPAuditProof:
    """Zero-knowledge proof for audit trail."""
    proof_type: ProofType
    statement_hash: str  # Hash of the statement being proved
    witness_hash: str  # Hash of witness (not revealed)
    proof_data: Dict[str, Any]  # Proof data
    public_inputs: Dict[str, Any]  # Public inputs to verification
    timestamp: str
    verifier_did: Optional[str] = None


@dataclass
class AuditEvent:
    """
    Privacy-preserving audit event.
    
    Contains actual event data (encrypted/sanitized) and
    ZKP proving the event was processed correctly.
    """
    event_id: str
    event_type: AuditEventType
    timestamp: str
    actor_id: str  # Who performed the action
    subject_id: Optional[str]  # Who/what was affected
    resource_id: Optional[str]  # What resource was involved
    decision: Optional[str]  # Outcome (allow/deny/review)
    confidence: Optional[float]  # Confidence score (sanitized)
    risk_score: Optional[float]  # Risk score (sanitized)
    metadata: Dict[str, Any]  # Sanitized metadata
    zk_proof: Optional[ZKPAuditProof]  # Proof of correct processing
    encrypted_data: Optional[Dict[str, Any]]  # Encrypted sensitive data
    hash_chain_link: Optional[str]  # Link to previous event (tamper-evidence)
    previous_hash: Optional[str]  # Previous event hash
    event_hash: str  # Hash of this event


class ZKProofGenerator:
    """
    Generates zero-knowledge proofs for audit statements.
    
    Simulates ZKP protocols (in production, use libsnark, bellman, etc.)
    """
    
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self._generate_keypair()
    
    def _generate_keypair(self):
        """Generate key pair for signing proofs."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        self.private_key = private_key
        self.public_key = private_key.public_key()
    
    def generate_schnorr_proof(
        self,
        statement: str,
        witness: str,
        public_input: str
    ) -> Dict[str, Any]:
        """
        Generate Schnorr-type ZKP.
        
        Proves knowledge of witness without revealing it.
        
        Args:
            statement: Statement to prove (e.g., "score > threshold")
            witness: Secret witness (e.g., actual score)
            public_input: Public input for verification
        
        Returns:
            ZKP proof data
        """
        # In production: use actual Schnorr protocol
        # Here: simulate with hash-based commitment
        
        commitment = hashlib.sha256(
            f"{statement}{witness}{public_input}".encode()
        ).hexdigest()
        
        # "Proof" is a hash that commits to witness
        proof = hashlib.sha256(
            f"{commitment}{witness}{uuid.uuid4()}".encode()
        ).hexdigest()
        
        return {
            "type": "schnorr_simulated",
            "commitment": commitment,
            "proof": proof,
            "public_input": public_input,
            "statement_hash": hashlib.sha256(statement.encode()).hexdigest()
        }
    
    def generate_range_proof(
        self,
        value: float,
        min_val: float,
        max_val: float
    ) -> Dict[str, Any]:
        """
        Generate range proof (value is in [min, max]).
        
        Proves value is in range without revealing value.
        
        Args:
            value: Secret value
            min_val: Minimum allowed
            max_val: Maximum allowed
        
        Returns:
            Range proof
        """
        # Simulation: commit to value and range
        assert min_val <= value <= max_val, "Value out of range"
        
        value_hash = hashlib.sha256(str(value).encode()).hexdigest()
        range_hash = hashlib.sha256(
            f"{min_val}:{max_val}".encode()
        ).hexdigest()
        
        proof = hashlib.sha256(
            f"{value_hash}{range_hash}{uuid.uuid4()}".encode()
        ).hexdigest()
        
        return {
            "type": "range_proof_simulated",
            "value_hash": value_hash,
            "range_hash": range_hash,
            "proof": proof,
            "range": {"min": min_val, "max": max_val}
        }
    
    def generate_set_membership_proof(
        self,
        element: str,
        set_hash: str
    ) -> Dict[str, Any]:
        """
        Prove element is in set (by hash) without revealing element.
        
        Args:
            element: Element to prove membership for
            set_hash: Hash of the set
        
        Returns:
            Set membership proof
        """
        element_hash = hashlib.sha256(element.encode()).hexdigest()
        proof = hashlib.sha256(
            f"{element_hash}{set_hash}{uuid.uuid4()}".encode()
        ).hexdigest()
        
        return {
            "type": "set_membership_simulated",
            "element_hash": element_hash,
            "set_hash": set_hash,
            "proof": proof
        }
    
    def generate_comparison_proof(
        self,
        value_a: float,
        value_b: float,
        relation: str  # ">", "<", "==", ">=", "<="
    ) -> Dict[str, Any]:
        """
        Prove comparison relation without revealing values.
        
        Args:
            value_a: First value
            value_b: Second value
            relation: Comparison relation
        
        Returns:
            Comparison proof
        """
        # Verify relation holds
        if relation == ">":
            assert value_a > value_b
        elif relation == "<":
            assert value_a < value_b
        elif relation == "==":
            assert value_a == value_b
        elif relation == ">=":
            assert value_a >= value_b
        elif relation == "<=":
            assert value_a <= value_b
        
        hash_a = hashlib.sha256(str(value_a).encode()).hexdigest()
        hash_b = hashlib.sha256(str(value_b).encode()).hexdigest()
        proof = hashlib.sha256(
            f"{hash_a}{hash_b}{relation}{uuid.uuid4()}".encode()
        ).hexdigest()
        
        return {
            "type": "comparison_simulated",
            "hash_a": hash_a,
            "hash_b": hash_b,
            "relation": relation,
            "proof": proof
        }
    
    def generate_decision_proof(
        self,
        decision: str,
        confidence: float,
        threshold: float,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate ZKP that decision was made correctly.
        
        Proves: If confidence >= threshold, then decision = "allow"
                If confidence < threshold, then decision = "deny"
        
        Without revealing actual confidence or threshold.
        
        Args:
            decision: Actual decision made
            confidence: Confidence score (secret)
            threshold: Decision threshold (secret)
            metadata: Additional metadata
        
        Returns:
            ZKP proof
        """
        # Prove confidence is in valid range [0, 1]
        range_proof = self.generate_range_proof(confidence, 0.0, 1.0)
        
        # Prove threshold is in valid range [0, 1]
        threshold_proof = self.generate_range_proof(threshold, 0.0, 1.0)
        
        # Prove decision logic
        if decision == "allow":
            # Prove confidence >= threshold
            comp_proof = self.generate_comparison_proof(
                confidence, threshold, ">="
            )
        else:
            # Prove confidence < threshold
            comp_proof = self.generate_comparison_proof(
                confidence, threshold, "<"
            )
        
        # Combine proofs
        combined_proof = hashlib.sha256(
            f"{range_proof['proof']}{threshold_proof['proof']}{comp_proof['proof']}".encode()
        ).hexdigest()
        
        return {
            "proof_type": "decision_logic",
            "decision": decision,
            "range_proof": range_proof,
            "threshold_proof": threshold_proof,
            "comparison_proof": comp_proof,
            "combined_proof": combined_proof,
            "metadata_hash": hashlib.sha256(
                json.dumps(metadata, sort_keys=True).encode()
            ).hexdigest()
        }
    
    def sign_proof(
        self,
        proof_data: Dict[str, Any]
    ) -> str:
        """
        Sign proof data with issuer key.
        
        Args:
            proof_data: Proof data to sign
        
        Returns:
            Signature
        """
        if not self.private_key:
            raise ValueError("No private key available")
        
        message = json.dumps(proof_data, sort_keys=True).encode()
        signature = self.private_key.sign(
            message,
            ec.ECDSA(hashes.SHA256())
        )
        
        return base64.b64encode(signature).decode()


class AuditTrail:
    """
    Privacy-preserving audit trail with ZKP.
    
    Maintains tamper-evident log of all system events.
    Each event includes ZKP proving correct processing.
    """
    
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.events: List[AuditEvent] = []
        self.proof_generator = ZKProofGenerator()
        self.last_hash = None
        self.privacy_mode = True  # Enable ZKP by default
    
    def log_event(
        self,
        event_type: AuditEventType,
        actor_id: str,
        decision: Optional[str] = None,
        confidence: Optional[float] = None,
        risk_score: Optional[float] = None,
        subject_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        sensitive_data: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Log an audit event with privacy-preserving proofs.
        
        Args:
            event_type: Type of event
            actor_id: Who performed the action
            decision: Decision outcome
            confidence: Confidence score (if applicable)
            risk_score: Risk score (if applicable)
            subject_id: Subject affected
            resource_id: Resource involved
            metadata: Additional metadata
            sensitive_data: Sensitive data (will be encrypted)
        
        Returns:
            AuditEvent with ZKP
        """
        metadata = metadata or {}
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Generate event ID
        event_id = f"audit:{uuid.uuid4()}"
        
        # Create ZK proof if privacy mode enabled
        zk_proof = None
        if self.privacy_mode and decision is not None and confidence is not None:
            # Default threshold (should come from policy)
            threshold = metadata.get("decision_threshold", 0.7)
            
            proof_data = self.proof_generator.generate_decision_proof(
                decision=decision,
                confidence=confidence,
                threshold=threshold,
                metadata=metadata
            )
            
            signature = self.proof_generator.sign_proof(proof_data)
            
            zk_proof = ZKPAuditProof(
                proof_type=ProofType.SIMULATED,
                statement_hash=proof_data["combined_proof"],
                witness_hash=proof_data.get("metadata_hash", ""),
                proof_data=proof_data,
                public_inputs={
                    "system_id": self.system_id,
                    "event_type": event_type.value,
                    "decision": decision
                },
                timestamp=timestamp,
                verifier_did=None
            )
        
        # Encrypt sensitive data
        encrypted_data = None
        if sensitive_data:
            encrypted_data = self._encrypt_sensitive_data(sensitive_data)
        
        # Create hash chain link (tamper evidence)
        event_hash_input = f"{event_id}{timestamp}{actor_id}{decision or ''}"
        if self.last_hash:
            event_hash_input += self.last_hash
        event_hash = hashlib.sha256(event_hash_input.encode()).hexdigest()
        
        # Create event
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            actor_id=actor_id,
            subject_id=subject_id,
            resource_id=resource_id,
            decision=decision,
            confidence=confidence,
            risk_score=risk_score,
            metadata=metadata,
            zk_proof=zk_proof,
            encrypted_data=encrypted_data,
            previous_hash=self.last_hash,
            event_hash=event_hash
        )
        
        # Append to chain
        self.events.append(event)
        self.last_hash = event_hash
        
        return event
    
    def _encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive data for storage."""
        # In production, use proper encryption (AES-GCM, etc.)
        # Simulation only
        data_json = json.dumps(data, sort_keys=True)
        return {
            "encrypted": True,
            "data": base64.b64encode(data_json.encode()).decode(),
            "algorithm": "AES-256-GCM (simulated)",
            "key_id": f"key:{hashlib.sha256(self.system_id.encode()).hexdigest()[:16]}"
        }
    
    def verify_event(self, event: AuditEvent) -> Dict[str, Any]:
        """
        Verify integrity and correctness of an audit event.
        
        Args:
            event: Audit event to verify
        
        Returns:
            Verification result
        """
        # Verify hash chain
        if event.previous_hash and self.events:
            prev_event = self.events[-1]
            if prev_event.event_id == event.event_id:
                # Find actual previous event
                for i, e in enumerate(self.events):
                    if e.event_id == event.event_id:
                        if i > 0:
                            prev_event = self.events[i-1]
                        break
            
            if event.previous_hash != prev_event.event_hash:
                return {
                    "verified": False,
                    "reason": "hash_chain_broken"
                }
        
        # Verify ZKP (if present)
        if event.zk_proof:
            # In production, verify actual ZKP
            # Here we verify proof structure
            proof = event.zk_proof
            if not proof.proof_data:
                return {
                    "verified": False,
                    "reason": "missing_proof_data"
                }
            
            # Verify statement hash matches
            if proof.statement_hash != proof.proof_data.get("combined_proof", ""):
                return {
                    "verified": False,
                    "reason": "statement_hash_mismatch"
                }
        
        # Verify hash
        expected_hash_input = f"{event.event_id}{event.timestamp}{event.actor_id}{event.decision or ''}"
        if event.previous_hash:
            expected_hash_input += event.previous_hash
        expected_hash = hashlib.sha256(expected_hash_input.encode()).hexdigest()
        
        if event.event_hash != expected_hash:
            return {
                "verified": False,
                "reason": "event_hash_mismatch"
            }
        
        return {
            "verified": True,
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp,
            "decision_valid": event.zk_proof is not None,
            "hash_chain_intact": True
        }
    
    def verify_chain(self) -> Dict[str, Any]:
        """Verify entire audit chain integrity."""
        results = []
        chain_valid = True
        
        for i, event in enumerate(self.events):
            result = self.verify_event(event)
            results.append({
                "event_index": i,
                "event_id": event.event_id,
                "verified": result["verified"]
            })
            if not result["verified"]:
                chain_valid = False
        
        return {
            "chain_valid": chain_valid,
            "total_events": len(self.events),
            "verified_events": sum(1 for r in results if r["verified"]),
            "events": results
        }
    
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query audit events with filters.
        
        Args:
            event_type: Filter by event type
            actor_id: Filter by actor
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)
            limit: Maximum results
        
        Returns:
            List of event summaries
        """
        filtered = self.events
        
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        
        if actor_id:
            filtered = [e for e in filtered if e.actor_id == actor_id]
        
        if start_time:
            filtered = [
                e for e in filtered
                if e.timestamp >= start_time
            ]
        
        if end_time:
            filtered = [
                e for e in filtered
                if e.timestamp <= end_time
            ]
        
        # Sort by timestamp (most recent first)
        filtered.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Return summaries
        summaries = []
        for event in filtered[:limit]:
            summary = asdict(event)
            # Remove sensitive encrypted data
            if summary.get("encrypted_data"):
                summary["encrypted_data"] = {"encrypted": True}
            summaries.append(summary)
        
        return summaries
    
    def generate_compliance_report(
        self,
        period_start: str,
        period_end: str
    ) -> Dict[str, Any]:
        """
        Generate compliance report for audit period.
        
        Args:
            period_start: Start of period (ISO format)
            period_end: End of period (ISO format)
        
        Returns:
            Compliance report
        """
        events = self.get_events(
            start_time=period_start,
            end_time=period_end,
            limit=10000
        )
        
        # Aggregate statistics
        total_events = len(events)
        by_type = {}
        by_decision = {}
        verified_count = 0
        
        for event_data in events:
            event_type = event_data.get("event_type")
            decision = event_data.get("decision")
            
            by_type[event_type] = by_type.get(event_type, 0) + 1
            
            if decision:
                by_decision[decision] = by_decision.get(decision, 0) + 1
            
            # Events with ZKP are considered verified
            if event_data.get("zk_proof"):
                verified_count += 1
        
        return {
            "report_id": f"compliance:{uuid.uuid4()}",
            "system_id": self.system_id,
            "period": {
                "start": period_start,
                "end": period_end
            },
            "summary": {
                "total_events": total_events,
                "verified_events": verified_count,
                "verification_rate": verified_count / total_events if total_events > 0 else 0
            },
            "events_by_type": by_type,
            "decisions": by_decision,
            "chain_integrity": self.verify_chain()["chain_valid"],
            "privacy_preserved": True,
            "zkp_enabled": self.privacy_mode
        }
    
    def enable_privacy_mode(self, enabled: bool = True):
        """Enable/disable privacy-preserving ZKP generation."""
        self.privacy_mode = enabled
    
    def export_audit_log(
        self,
        redact_sensitive: bool = True,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export audit log.
        
        Args:
            redact_sensitive: Remove sensitive data
            format: Export format
        
        Returns:
            Export data
        """
        export_events = []
        
        for event in self.events:
            event_dict = asdict(event)
            
            if redact_sensitive:
                # Remove or encrypt sensitive fields
                event_dict["subject_id"] = None
                event_dict["encrypted_data"] = {"redacted": True} if event_dict.get("encrypted_data") else None
            
            export_events.append(event_dict)
        
        return {
            "export_id": f"export:{uuid.uuid4()}",
            "system_id": self.system_id,
            "format": format,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "events": export_events,
            "total_count": len(export_events)
        }


# Convenience functions for common audit operations

def log_recognition_event(
    audit_trail: AuditTrail,
    actor_id: str,
    subject_id: str,
    confidence: float,
    decision: str,
    risk_score: float,
    metadata: Optional[Dict] = None
) -> AuditEvent:
    """Log a recognition event with ZKP."""
    return audit_trail.log_event(
        event_type=AuditEventType.RECOGNITION,
        actor_id=actor_id,
        subject_id=subject_id,
        decision=decision,
        confidence=confidence,
        risk_score=risk_score,
        metadata=metadata or {"event": "recognition"}
    )


def log_enrollment_event(
    audit_trail: AuditTrail,
    actor_id: str,
    subject_id: str,
    metadata: Optional[Dict] = None
) -> AuditEvent:
    """Log an enrollment event."""
    return audit_trail.log_event(
        event_type=AuditEventType.ENROLLMENT,
        actor_id=actor_id,
        subject_id=subject_id,
        decision="allow",
        metadata=metadata or {"event": "enrollment"}
    )


def log_policy_evaluation(
    audit_trail: AuditTrail,
    actor_id: str,
    decision: str,
    confidence: float,
    metadata: Optional[Dict] = None
) -> AuditEvent:
    """Log a policy evaluation event with ZKP."""
    return audit_trail.log_event(
        event_type=AuditEventType.POLICY_EVALUATION,
        actor_id=actor_id,
        decision=decision,
        confidence=confidence,
        metadata=metadata or {"event": "policy_evaluation"}
    )


def generate_audit_proof(
    decision: str,
    confidence: float,
    threshold: float
) -> Dict[str, Any]:
    """Generate standalone ZKP for audit."""
    generator = ZKProofGenerator()
    proof_data = generator.generate_decision_proof(
        decision=decision,
        confidence=confidence,
        threshold=threshold,
        metadata={}
    )
    signature = generator.sign_proof(proof_data)
    
    return {
        "proof": proof_data,
        "signature": signature,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
