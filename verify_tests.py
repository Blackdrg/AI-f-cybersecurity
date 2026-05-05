import ast
import os

test_files = [
    'tests/test_spoof_detection.py',
    'tests/test_federated_learning.py',
    'tests/test_jwt_revocation.py',
    'tests/test_enroll.py',
    'tests/test_recognize.py',
    'tests/test_key_rotation.py',
    'tests/test_edge_device.py',
    'tests/test_multi_camera.py'
]

base_path = r'D:\AI-F\AI-f\backend'
total = 0

for filepath in test_files:
    full_path = os.path.join(base_path, filepath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read())
                test_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'))
                print(f'{filepath}: {test_count} tests')
                total += test_count
            except Exception as e:
                print(f'{filepath}: ERROR - {e}')
    else:
        print(f'{filepath}: FILE NOT FOUND')

print(f'\nTotal core tests: {total}')