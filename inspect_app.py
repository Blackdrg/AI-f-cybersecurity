#!/usr/bin/env python
"""Inspect the FastAPI app to verify v1 routes are registered."""
import sys
sys.path.insert(0, r'D:\AI-F\AI-f\backend')

# We need to set required environment variables before importing main
import os
os.environ.setdefault('JWT_SECRET', 'test-secret')
os.environ.setdefault('DB_PASSWORD', 'test')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')

try:
    # This will initialize the app but may fail due to DB connections etc.
    # We just want to see if routes are added.
    from app.main import app
    
    print("Registered routes:")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(route.methods) if route.methods else 'ALL'
            print(f"  {methods:20} {route.path}")
        else:
            print(f"  {route}")
    
    # Check specifically for v1 routes
    v1_admin_routes = [r for r in app.routes if hasattr(r, 'path') and '/api/v1/admin' in r.path]
    v1_compliance_routes = [r for r in app.routes if hasattr(r, 'path') and '/api/v1/compliance' in r.path]
    
    print(f"\nv1/admin routes: {len(v1_admin_routes)}")
    for r in v1_admin_routes:
        print(f"  {', '.join(r.methods):20} {r.path}")
    
    print(f"\nv1/compliance routes: {len(v1_compliance_routes)}")
    for r in v1_compliance_routes:
        print(f"  {', '.join(r.methods):20} {r.path}")
        
except Exception as e:
    print(f"Error during import: {e}")
    import traceback
    traceback.print_exc()
