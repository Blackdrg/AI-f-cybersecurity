#!/usr/bin/env python3
# Extract the Admin & Operations block from README
with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all occurrences of the heading
import re
matches = list(re.finditer(r'^\*\*Admin & Operations \(12 endpoints\):\*\*', content, re.MULTILINE))
print(f"Found {len(matches)} occurrences at positions: {[m.start() for m in matches]}")

# For each occurrence, print the next 250 chars for context
for idx, m in enumerate(matches):
    start = m.start()
    snippet = content[start:start+600]
    print(f"\n--- Occurrence {idx+1} at {start} ---")
    print(snippet)
    print("--- END ---\n")
