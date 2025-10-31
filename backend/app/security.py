from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from typing import Optional

try:
    from ..models.ethical_governor import EthicalGovernor
    ETHICAL_GOVERNOR_AVAILABLE = True
except ImportError:
    ETHICAL_GOVERNOR_AVAILABLE = False
    EthicalGovernor = None

security = HTTPBearer()
ethical_governor = EthicalGovernor() if ETHICAL_GOVERNOR_AVAILABLE else None


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, os.getenv(
            'JWT_SECRET', 'secret'), algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_admin(user: dict = Depends(verify_token)):
    if user.get('role') not in ['admin', 'operator']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admin/Operator access required")
    return user


def require_operator(user: dict = Depends(verify_token)):
    if user.get('role') not in ['admin', 'operator']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Operator access required")
    return user


def require_auth(user: dict = Depends(verify_token)):
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


def create_token(user_id: str, role: str = 'user') -> str:
    import datetime
    if role not in ['admin', 'operator', 'user']:
        raise ValueError("Invalid role")
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, os.getenv('JWT_SECRET', 'secret'), algorithm='HS256')


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
            payload = jwt.decode(token, os.getenv(
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
