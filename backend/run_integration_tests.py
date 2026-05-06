#!/usr/bin/env python3
"""
Integration test runner for AI-f backend.

This script runs all integration tests with proper environment setup.
It requires real external services (Postgres, Redis, models) to be running.

Usage:
    python run_integration_tests.py [--skip-slow] [--markers MARKERS]

Options:
    --skip-slow      Skip slow integration tests
    --markers MARKERS Additional pytest markers to include
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    # Get the backend directory
    backend_dir = Path(__file__).parent.parent / "backend"
    os.chdir(backend_dir)
    
    print("=" * 60)
    print("AI-f Backend - Integration Test Suite")
    print("=" * 60)
    print()
    
    # Check prerequisites
    print("Checking prerequisites...")
    checks = []
    
    # Check DATABASE_URL
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        print(f"  ✓ DATABASE_URL: {db_url}")
        checks.append(True)
    else:
        print("  ✗ DATABASE_URL not set - some tests will be skipped")
        checks.append(False)
    
    # Check Redis
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    print(f"  REDIS_URL: {redis_url}")
    
    # Check model path
    model_path = os.environ.get('MODEL_PATH', 'backend/models/onnx_bundle')
    print(f"  MODEL_PATH: {model_path}")
    
    print()
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/integration/",
        "-v",
        "--tb=short",
        "--capture=no",
        "-p", "no:cacheprovider",
    ]
    
    # Add markers
    cmd.extend(["-m", "integration"])
    
    # Parse arguments
    skip_slow = "--skip-slow" in sys.argv
    if skip_slow:
        cmd[-1] = "integration and not slow_integration"
        sys.argv.remove("--skip-slow")
    
    # Add coverage if requested
    if "--coverage" in sys.argv:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=xml:coverage-integration.xml",
            "--cov-fail-under=80"
        ])
        sys.argv.remove("--coverage")
    
    # Add any extra pytest args
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    # Run tests
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print()
        print("=" * 60)
        print("✅ All integration tests passed!")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("❌ Some integration tests failed!")
        print("=" * 60)
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
