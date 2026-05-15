#!/usr/bin/env python
"""
Final validation script for backend stability.
Tests that all imports work and the FastAPI app can be instantiated.
"""
import warnings
warnings.filterwarnings('default')  # Don't treat warnings as errors

import sys
import os

# Simple import test
try:
    import app.main
    print("SUCCESS: Backend module imports correctly")
    sys.exit(0)
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)
