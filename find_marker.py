#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug README to find exact marker line.
"""

readme_path = r"D:\AI-F\AI-f\README.md"

with open(readme_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Search for any line containing "RBAC" and print surrounding context
for i, line in enumerate(lines):
    if 'RBAC' in line and 'Frontend' in line:
        print(f"Found RBAC Frontend at line {i+1}:")
        # Print 5 lines before and 5 after
        start = max(0, i-2)
        end = min(len(lines), i+8)
        for j in range(start, end):
            marker = ">>>" if j == i else "   "
            print(f"{marker} {j+1}: {repr(lines[j])}")
        print()

# Also check for the hash symbol variation
print("\n\nChecking for variations:")
for i, line in enumerate(lines):
    if 'RBAC' in line:
        print(f"Line {i+1}: {repr(line[:80])}")
