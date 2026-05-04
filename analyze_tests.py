import os
import re

tests_dir = 'backend/tests'
results = []

for root, dirs, files in os.walk(tests_dir):
    for f in files:
        if f.startswith('test_') and f.endswith('.py'):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
            
            test_funcs = re.findall(r'^\s*def\s+test_\w+\s*\(', content, re.MULTILINE)
            async_test_funcs = re.findall(r'^\s*async\s+def\s+test_\w+\s*\(', content, re.MULTILINE)
            total_funcs = len(test_funcs) + len(async_test_funcs)
            
            infra = len(re.findall(r'@pytest\.mark\.infra', content))
            onnx = len(re.findall(r'@pytest\.mark\.onnx', content))
            gpu = len(re.findall(r'@pytest\.mark\.gpu', content))
            
            results.append({
                'file': filepath.replace('backend/tests/', ''),
                'total_tests': total_funcs,
                'infra': infra,
                'onnx': onnx,
                'gpu': gpu,
            })

totals = {'total_tests': 0, 'infra': 0, 'onnx': 0, 'gpu': 0}
for r in results:
    totals['total_tests'] += r['total_tests']
    totals['infra'] += r['infra']
    totals['onnx'] += r['onnx']
    totals['gpu'] += r['gpu']

print('Per file:')
for r in results:
    print(f"  {r['file']}: {r['total_tests']} tests")

print()
print(f"TOTAL test functions: {totals['total_tests']}")
print(f"TOTAL @pytest.mark.infra: {totals['infra']}")
print(f"TOTAL @pytest.mark.onnx: {totals['onnx']}")
print(f"TOTAL @pytest.mark.gpu: {totals['gpu']}")
