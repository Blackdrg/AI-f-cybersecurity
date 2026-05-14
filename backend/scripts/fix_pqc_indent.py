import re

with open(r'D:\AI-F\AI-f\backend\app\security\pqc.py') as f:
    lines = f.readlines()

# Fix lines 164-165 (def load_key) - should be 4 spaces
# Fix lines 175-176 (def list_keys) - should be 4 spaces
new_lines = []
for i, line in enumerate(lines):
    if i == 163 and line.startswith('    def load_key('):
        new_lines.append(line)
    elif i >= 164 and i <= 174 and not line.startswith(' ') and not line.startswith('\n'):
        # line at wrong indent level
        new_lines.append('    ' + line if not line.startswith('    ') and line.strip() else line)
    elif i == 175 and line.startswith('    def list_keys('):
        new_lines.append(line)
    elif i >= 176 and not line.startswith('    ') and line.strip() and not line.startswith('\n'):
        new_lines.append('    ' + line)
    else:
        new_lines.append(line)

with open(r'D:\AI-F\AI-f\backend\app\security\pqc.py', 'w') as f:
    f.writelines(new_lines)
print('Fixed pqc.py indentation')