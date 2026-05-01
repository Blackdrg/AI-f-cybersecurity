#!/usr/bin/env python
"""Validate that all v1 modules can be imported without errors."""
import sys
import os

# Add backend to path
sys.path.insert(0, r'D:\AI-F\AI-f\backend')

try:
    print("Importing app.api.v1...")
    from app.api.v1 import admin_router, compliance_router
    print("+ admin_router:", admin_router)
    print("+ compliance_router:", compliance_router)
    
    print("\nImporting app.api.v1.admin...")
    from app.api.v1.admin import router as admin_v1_router
    print("+ admin_v1_router:", admin_v1_router)
    
    print("\nImporting app.api.v1.compliance...")
    from app.api.v1.compliance import router as compliance_v1_router
    print("+ compliance_v1_router:", compliance_v1_router)
    
    print("\nAll imports successful!")
except Exception as e:
    print(f"! Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
