#!/usr/bin/env python3
"""
Full test suite runner for AI-f backend.
Runs all pytest tests with coverage reporting.
"""

import subprocess
import sys
import os

def main():
    print("AI-f Backend - Full Test Suite")
    print("=" * 50)
    
    # Change to backend directory
    if os.path.exists("backend"):
        os.chdir("backend")
    print(f"Current directory: {os.getcwd()}")
    
    # Install test dependencies if needed
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-r", "requirements-dev.txt"], 
                   capture_output=True)
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-fail-under=85",
        "-m", "not slow"
    ]
    
    print("Running command:", " ".join(cmd))
    print()
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
    print(f"Return code: {result.returncode}")
    
    # Count test files
    test_files = [f for f in os.listdir("tests") if f.endswith(".py") and f.startswith("test_")]
    print(f"\nTest files found: {len(test_files)}")
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()

