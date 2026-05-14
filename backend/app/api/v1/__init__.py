"""
API v1 subpackage.

This package contains version 1 of the API endpoints for:
- Admin: System administration, person management, metrics, analytics, model OTA
- Compliance: GDPR/BIPA compliance endpoints (data export, deletion, DSAR status)
- Security: Compliance controls, audit reports, security validation
"""

from fastapi import APIRouter

from .admin import router as admin_router
from .compliance import router as compliance_router

# Combine all v1 routers into a single api_router for main.py
api_router = APIRouter()
api_router.include_router(admin_router)
api_router.include_router(compliance_router)

__all__ = ["admin_router", "compliance_router", "api_router"]