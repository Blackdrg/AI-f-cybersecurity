#!/usr/bin/env python3
import re

with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the TypeScript migration inconsistency - replace "Partial TypeScript migration (3% of components)"
# with accurate description only in the feature list section (not in the comparison tables)
# Find the section with the feature list and replace

# Pattern that matches the line we want to change in context
pattern = r'(- âœ… Material-UI \(MUI\) component library integration\n\n- âœ… MUI X Charts for data visualization\n\n- âœ… Partial TypeScript migration \(3% of components\))'

replacement = '- âœ… Material-UI (MUI) component library integration\n\n- âœ… MUI X Charts for data visualization\n\n- âœ… **Complete TypeScript migration** - 100% of 64 frontend components use TypeScript/TSX (no JavaScript files)'

content = re.sub(pattern, replacement, content)

# Also fix the comparison table that says "3% of components"
table_pattern = r'\| \*\*TypeScript\*\* \| 4\.9\.5 \(frontend\) \|'
table_replacement = '| **TypeScript** | 4.9.5 (frontend - 64 TS/TSX components, 0 JS files) |'
content = re.sub(table_pattern, table_replacement, content)

# Fix the v2.0 table row about components
v2_pattern = r'\| \*\*Frontend Components:\*\* \| 48 React components \(TypeScript/TSX\), 25\+ pages \|'
v2_replacement = '| **Frontend Components:** | 64 React components (TypeScript/TSX, 0 JS), 25+ pages |'
content = re.sub(v2_pattern, v2_replacement, content)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("README.md updated successfully")
