from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
import logging

logger = logging.getLogger(__name__)

# FIPS 140-2 Roadmap: Set to True when HSM/KMS is integrated
FIPS_MODE = os.getenv("FIPS_MODE", "false").lower() == "true"
import grpc
from typing import Optional

try:
    from ..models.ethical_governor import EthicalGovernor
    ETHICAL_GOVERNOR_AVAILABLE = True
except ImportError:
    ETHICAL_GOVERNOR_AVAILABLE = False
    EthicalGovernor = None

security = HTTPBearer()
ethical_governor = EthicalGovernor() if ETHICAL_GOVERNOR_AVAILABLE else None


from .secrets_manager import secrets_manager

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, secrets_manager.get_secret(
            'JWT_SECRET', 'secret'), algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_admin(user: dict = Depends(verify_token)):
    if user.get('role') not in ['admin', 'super_admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admin/SuperAdmin access required")
    return user


def require_operator(user: dict = Depends(verify_token)):
    if user.get('role') not in ['admin', 'super_admin', 'operator']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Operator/Admin access required")
    return user


def require_auditor(user: dict = Depends(verify_token)):
    if user.get('role') not in ['admin', 'super_admin', 'auditor']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Auditor access required")
    return user


def require_auth(user: dict = Depends(verify_token)):
    return user


async def require_org_member(org_id: str, user: dict = Depends(verify_token)):
    """Check if user is a member of the specified organization."""
    from .db.db_client import get_db
    db = await get_db()
    orgs = await db.get_user_orgs(user["user_id"])
    for org in orgs:
        if str(org["org_id"]) == org_id:
            user["org_role"] = org["role"]
            return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")


async def require_org_admin(org_id: str, user: dict = Depends(verify_token)):
    """Check if user is an admin of the specified organization."""
    user = await require_org_member(org_id, user)
    if user["org_role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization admin access required")
    return user


async def require_org_operator(org_id: str, user: dict = Depends(verify_token)):
    """Check if user is an operator or admin of the specified organization."""
    user = await require_org_member(org_id, user)
    if user["org_role"] not in ["admin", "operator"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization operator access required")
    return user


def get_current_user(user: dict = Depends(verify_token)):
    """Get current authenticated user - alias for require_auth for SaaS features."""
    return user


def check_ethical(request_data: dict, user: dict = Depends(verify_token)):
    role = user.get('role', 'user')
    check = ethical_governor.check_request(request_data, role)
    if not check['approved']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Ethical violation: {check['reason']}")
    ethical_governor.audit_decision(
        check, {'user': user, 'request': request_data})
    return user

# Enhanced RBAC: roles - admin, operator, user


def create_token(user_id: str, role: str = 'viewer') -> str:
    import datetime
    valid_roles = ['super_admin', 'admin', 'operator', 'auditor', 'analyst', 'viewer']
    if role not in valid_roles:
        raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")
    if FIPS_MODE:
        # Note: In production with HSM, this would use a FIPS-validated provider
        logger.warning("FIPS_MODE enabled: Token generation currently using software-only fallback.")
    
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, secrets_manager.get_secret('JWT_SECRET', 'secret'), algorithm='HS256')


def require_auth_grpc(func):
    """Decorator for gRPC authentication"""

    async def wrapper(self, request, context):
        # Extract token from metadata
        metadata = dict(context.invocation_metadata())
        token = metadata.get('authorization', '').replace('Bearer ', '')

        if not token:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details('Missing authentication token')
            return

        try:
            payload = jwt.decode(token, secrets_manager.get_secret(
                'JWT_SECRET', 'secret'), algorithms=['HS256'])
            context.user = payload
            context.client_host = metadata.get('x-forwarded-for', 'unknown')
        except jwt.ExpiredSignatureError:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details('Token expired')
            return
        except jwt.InvalidTokenError:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details('Invalid token')
            return

        return await func(self, request, context)
    return wrapper


def setup_security(app):
    """Setup security middleware for FastAPI app"""
    # Add any security middleware here if needed
    pass
