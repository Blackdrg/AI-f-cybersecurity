import os
import re

total = 0
files = []
for root, dirs, filenames in os.walk('backend/tests'):
    for f in filenames:
        if f.startswith('test_') and f.endswith('.py'):
            files.append(os.path.join(root, f))

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            content = fp.read()
            matches = re.findall(r'^def test_\w+', content, re.MULTILINE)
            c = len(matches)
            total += c
            print(f'{os.path.basename(f)}: {c}')
    except Exception as e:
        print(f'Error: {f} - {e}')

print(f'\nTotal test functions: {total}')
print(f'Test files: {len(files)}')
