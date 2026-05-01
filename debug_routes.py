#!/usr/bin/env python
"""Debug: List all routes registered on admin_v1 and compliance_v1 routers."""
import sys
sys.path.insert(0, r'D:\AI-F\AI-f\backend')

try:
    from app.api.v1.admin import router as admin_v1_router
    from app.api.v1.compliance import router as compliance_v1_router
    
    print("=== Admin v1 Routes ===")
    for route in admin_v1_router.routes:
        print(f"  {list(route.methods)[0] if route.methods else 'ALL':6} {route.path}")
    
    print(f"\nTotal admin v1 routes: {len(admin_v1_router.routes)}")
    
    print("\n=== Compliance v1 Routes ===")
    for route in compliance_v1_router.routes:
        print(f"  {list(route.methods)[0] if route.methods else 'ALL':6} {route.path}")
    
    print(f"\nTotal compliance v1 routes: {len(compliance_v1_router.routes)}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
