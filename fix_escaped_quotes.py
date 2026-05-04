#!/usr/bin/env python3
"""Fix escaped triple-quote artifacts in Python files."""
import re
from pathlib import Path

corrupted_pattern = re.compile(r'^\\"{3}|\\"{3}|\\"{3}$|\\"{3}$')

def fix_file(filepath: Path):
    original = filepath.read_text(encoding='utf-8')
    # Replace \"\"\" with """ throughout the file
    fixed = original.replace('\\"\\"\\"', '"""')
    # Also fix any remaining \' escaped single quotes in strings
    fixed = fixed.replace("\\'", "'")
    if fixed != original:
        filepath.write_text(fixed, encoding='utf-8')
        print(f"Fixed: {filepath}")
    else:
        print(f"Clean: {filepath}")

# Scan backend/app recursively
for pyfile in Path('backend/app').rglob('*.py'):
    fix_file(pyfile)

print("\nDone.")
