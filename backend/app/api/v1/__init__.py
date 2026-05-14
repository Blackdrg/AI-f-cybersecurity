"""
API v1 subpackage.

This package contains version 1 of the API endpoints for:
- Admin: System administration, person management, metrics, analytics, model OTA
- Compliance: GDPR/BIPA compliance endpoints (data export, deletion, DSAR status)
- Security: Compliance controls, audit reports, security validation
- Enroll: Biometric enrollment endpoints
- Recognize: Biometric recognition endpoints
- Federated Learning: Federated model training endpoints
"""

from fastapi import APIRouter

from .admin import router as admin_router
from .compliance import router as compliance_router
from ..enroll import router as enroll_router
from ..recognize import router as recognize_router
from ..federated_learning import router as federated_learning_router

# Combine all v1 routers into a single api_router for main.py
api_router = APIRouter()
api_router.include_router(admin_router)
api_router.include_router(compliance_router)
api_router.include_router(enroll_router)
api_router.include_router(recognize_router)
api_router.include_router(federated_learning_router)

__all__ = ["admin_router", "compliance_router", "enroll_router",
           "recognize_router", "federated_learning_router", "api_router"]