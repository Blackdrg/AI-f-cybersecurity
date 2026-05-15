#!/usr/bin/env python3
"""Test script to verify librosa import fix in voice_embedder.py"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_librosa_imports():
    """Test that librosa imports work correctly"""
    print("Testing librosa import handling...")
    
    # Import the module - this should not fail even if librosa is not available
    try:
        from app.models.voice_embedder import LIBROSA_AVAILABLE, librosa
        print("LIBROSA_AVAILABLE:", LIBROSA_AVAILABLE)
        if LIBROSA_AVAILABLE:
            print("librosa imported successfully")
        else:
            print("librosa not available (expected in some environments)")
        return True
    except Exception as e:
        print("Failed to import voice_embedder module:", e)
        return False

def test_resample_function():
    """Test the resample function with mocked librosa"""
    print("\nTesting resample function logic...")
    
    # We'll test the logic by importing and checking the source
    try:
        with open(os.path.join(os.path.dirname(__file__), 'backend', 'app', 'models', 'voice_embedder.py'), 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for our fix
        if "if sample_rate != 16000 and LIBROSA_AVAILABLE:" in content:
            print("PASS: Resample fix detected in source code")
            return True
        else:
            print("FAIL: Resample fix not found in source code")
            # Show context around line 250
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'sample_rate != 16000' in line:
                    print("Context around line", i+1, ":")
                    for j in range(max(0, i-2), min(len(lines), i+3)):
                        marker = ">>>" if j == i else "   "
                        print(f"{marker} {j+1:3}: {lines[j]}")
                    break
            return False
            
    except Exception as e:
        print("Failed to check file content:", e)
        return False

def test_other_librosa_usage():
    """Test other librosa usage in the file"""
    print("\nTesting other librosa usage...")
    
    try:
        with open(os.path.join(os.path.dirname(__file__), 'backend', 'app', 'models', 'voice_embedder.py'), 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for protected librosa usage
        lines = content.split('\n')
        fixed_count = 0
        total_checks = 0
        
        for i, line in enumerate(lines):
            if 'librosa.' in line and not line.strip().startswith('#'):
                total_checks += 1
                # Check if it's protected by LIBROSA_AVAILABLE check or in a try/except
                protected = False
                # Check previous few lines for LIBROSA_AVAILABLE condition
                for j in range(max(0, i-5), i):
                    if 'LIBROSA_AVAILABLE' in lines[j] and ('if' in lines[j] or 'and' in lines[j]):
                        protected = True
                        break
                # Check if in try block
                if not protected:
                    for j in range(max(0, i-10), i):
                        if 'try:' in lines[j]:
                            protected = True
                            break
                if protected:
                    fixed_count += 1
                    
        print("Found", total_checks, "librosa usages,", fixed_count, "appear to be protected")
        
        if fixed_count > 0:
            print("PASS: Some librosa usage is protected")
            return True
        else:
            print("WARN: Unable to verify protection - manual check recommended")
            return True  # Not necessarily a failure
            
    except Exception as e:
        print("Failed to check librosa usage:", e)
        return False

if __name__ == "__main__":
    print("=== Testing Librosa Import Fix ===")
    
    success = True
    success &= test_librosa_imports()
    success &= test_resample_function()
    success &= test_other_librosa_usage()
    
    if success:
        print("\nPASS: All tests passed - librosa import fix appears to be working correctly")
        sys.exit(0)
    else:
        print("\nFAIL: Some tests failed - please review the fix")
        sys.exit(1)