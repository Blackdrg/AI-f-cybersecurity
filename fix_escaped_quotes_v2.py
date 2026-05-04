#!/usr/bin/env python3
"""Remove ALL backslash-escaped quotes from Python files."""
import re
from pathlib import Path

def fix_escaped(filepath: Path):
    content = filepath.read_text(encoding='utf-8')
    # Replace all \" with "
    # Also replace \' with ' (single quote escapes)
    new_content = content.replace('\\"', '"').replace("\\'", "'")
    if new_content != content:
        filepath.write_text(new_content, encoding='utf-8')
        print(f"Fixed: {filepath}")
    else:
        print(f"OK: {filepath}")

targets = [
    Path('backend/app/api/subscriptions.py'),
    Path('backend/app/middleware/auth.py'),
    Path('backend/app/security/vault.py'),
    Path('backend/app/services/stripe_service.py'),
]

for f in targets:
    if f.exists():
        fix_escaped(f)
    else:
        print(f"NOT FOUND: {f}")

print("Done.")
