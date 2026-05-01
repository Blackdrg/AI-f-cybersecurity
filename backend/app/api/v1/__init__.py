"""
API v1 subpackage.

This package contains version 1 of the API endpoints for:
- Admin: System administration, person management, metrics, analytics, model OTA
- Compliance: GDPR/BIPA compliance endpoints (data export, deletion, DSAR status)
"""

from .admin import router as admin_router
from .compliance import router as compliance_router

__all__ = ["admin_router", "compliance_router"]
