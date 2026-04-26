"""
FastAPI dependency for policy and ethical checks.

Provides a reusable dependency that can be added to any endpoint
to enforce PolicyEngine and EthicalGovernor rules.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Request
from ..policy_engine import get_policy_engine, SubjectType, ResourceType, PolicyEffect
from ..models.ethical_governor import check_ethical_compliance, EthicalDecision
from ..security import get_current_user
import logging

logger = logging.getLogger(__name__)


class PolicyContext:
    """Context object passed to policy decision points."""
    def __init__(
        self,
        user: Dict[str, Any],
        resource: ResourceType,
        request: Request,
        metadata: Optional[Dict] = None
    ):
        self.user = user
        self.resource = resource
        self.request = request
        self.metadata = metadata or {}
        self.client_ip = request.client.host if request.client else "unknown"


async def enforce_policy(
    context: PolicyContext,
    require_consent: bool = False,
    require_age_gate: bool = False
) -> bool:
    """
    Enforce policy and ethical checks.
    Raises HTTPException if policy denied.
    """
    policy_engine = get_policy_engine()

    # Determine subject type from user role
    role = context.user.get("role", "user")
    subject_type_map = {
        "admin": SubjectType.ADMIN,
        "operator": SubjectType.OPERATOR,
        "service": SubjectType.SERVICE,
    }
    subject_type = subject_type_map.get(role, SubjectType.USER)

    # Build context dict for condition evaluation
    eval_context = {
        "ip_range": context.client_ip,
        "risk_level": context.metadata.get("risk_level", "low"),
        "purpose": context.metadata.get("purpose", "authentication"),
        "day_of_week": datetime.utcnow().strftime("%A").lower(),
        "time_of_day": datetime.utcnow().strftime("%H:%M"),
    }

    # Evaluate policy
    decision = policy_engine.evaluate(
        subject_id=context.user.get("user_id") or context.user.get("sub"),
        subject_type=subject_type,
        resource=context.resource,
        action="use",
        context=eval_context
    )

    if not decision.allowed:
        logger.warning(
            f"Policy denied: user={context.user.get('user_id')} resource={context.resource} "
            f"reason={decision.reason}"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "policy_denied",
                "reason": decision.reason,
                "matched_rule": decision.matched_rule
            }
        )

    # Check usage limits
    if decision.rate_limit_remaining is not None and decision.rate_limit_remaining <= 0:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Rate limit exceeded for this resource"
            }
        )

    # Ethical compliance check
    if require_consent or require_age_gate:
        ethical_data = {
            "age": context.metadata.get("age"),
            "consent": context.metadata.get("consent", False),
            "user_id": context.user.get("user_id"),
            "jurisdiction": context.metadata.get("jurisdiction", "DEFAULT")
        }
        ethics_result: EthicalDecision = check_ethical_compliance(
            request_data=ethical_data,
            user_role=role,
            jurisdiction=ethical_data["jurisdiction"]
        )
        if not ethics_result.approved:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "ethical_check_failed",
                    "reason": ethics_result.explanation
                }
            )

    return True


# Convenience dependencies for common resources
async def require_enroll_policy(
    request: Request,
    user: Dict = Depends(get_current_user)
) -> bool:
    context = PolicyContext(
        user=user,
        resource=ResourceType.ENROLL,
        request=request,
        metadata={"purpose": "enrollment"}
    )
    # Only enforce policy engine (auth, rate limits). Ethical checks (age, consent)
    # are performed by the endpoint after processing biometric data.
    policy_engine = get_policy_engine()
    subject_type_map = {
        "admin": SubjectType.ADMIN,
        "operator": SubjectType.OPERATOR,
        "service": SubjectType.SERVICE,
    }
    subject_type = subject_type_map.get(user.get("role", "user"), SubjectType.USER)
    decision = policy_engine.evaluate(
        subject_id=user.get("user_id") or user.get("sub"),
        subject_type=subject_type,
        resource=ResourceType.ENROLL,
        context={
            "ip_range": context.client_ip,
            "purpose": "enrollment",
            "day_of_week": datetime.utcnow().strftime("%A").lower(),
            "time_of_day": datetime.utcnow().strftime("%H:%M")
        }
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "policy_denied",
                "reason": decision.reason,
                "matched_rule": decision.matched_rule
            }
        )
    if decision.rate_limit_remaining is not None and decision.rate_limit_remaining <= 0:
        raise HTTPException(status_code=429, detail={"error": "rate_limit_exceeded"})
    return True


async def require_recognize_policy(
    request: Request,
    user: Dict = Depends(get_current_user)
) -> bool:
    context = PolicyContext(
        user=user,
        resource=ResourceType.RECOGNIZE,
        request=request,
        metadata={"purpose": "authentication"}
    )
    return await enforce_policy(context)


async def require_admin_policy(
    request: Request,
    user: Dict = Depends(get_current_user)
) -> bool:
    context = PolicyContext(
        user=user,
        resource=ResourceType.ADMIN,
        request=request,
        metadata={"purpose": "administration"}
    )
    return await enforce_policy(context)
