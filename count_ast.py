import ast
import os
from collections import defaultdict

tests_dir = 'backend/tests'
results = []

for root, dirs, files in os.walk(tests_dir):
    for f in files:
        if f.startswith('test_') and f.endswith('.py') and f != 'conftest.py':
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
            
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            
            test_funcs = []
            infra = 0
            redis_marked = 0
            stripe_marked = 0
            openai_marked = 0
            onnx_marked = 0
            pgvector_marked = 0
            gpu_marked = 0
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    test_funcs.append(node.name)
                    # Check decorators on this function
                    for dec in node.decorator_list:
                        dec_str = ast.unparse(dec)
                        if 'infra' in dec_str:
                            infra += 1
                        if 'redis' in dec_str:
                            redis_marked += 1
                        if 'stripe' in dec_str:
                            stripe_marked += 1
                        if 'openai' in dec_str:
                            openai_marked += 1
                        if 'onnx' in dec_str:
                            onnx_marked += 1
                        if 'pgvector' in dec_str:
                            pgvector_marked += 1
                        if 'gpu' in dec_str:
                            gpu_marked += 1
                # Also check async functions
                if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith('test_'):
                    test_funcs.append(node.name)
                    for dec in node.decorator_list:
                        dec_str = ast.unparse(dec)
                        if 'infra' in dec_str:
                            infra += 1
                        if 'redis' in dec_str:
                            redis_marked += 1
                        if 'stripe' in dec_str:
                            stripe_marked += 1
                        if 'openai' in dec_str:
                            openai_marked += 1
                        if 'onnx' in dec_str:
                            onnx_marked += 1
                        if 'pgvector' in dec_str:
                            pgvector_marked += 1
                        if 'gpu' in dec_str:
                            gpu_marked += 1
            
            results.append({
                'file': filepath.replace('backend/tests/', ''),
                'total_tests': len(test_funcs),
                'infra': infra,
                'redis': redis_marked,
                'stripe': stripe_marked,
                'openai': openai_marked,
                'onnx': onnx_marked,
                'pgvector': pgvector_marked,
                'gpu': gpu_marked,
            })
        
        elif f.startswith('test_') and f.endswith('.py') and 'conftest' in f:
            pass  # skip conftest

totals = {k: 0 for k in results[0].keys() if k != 'file'}
for r in results:
    for k in totals:
        totals[k] += r[k]

print('Per-file test counts and markers:')
for r in results:
    print(f\"  {r['file']}: tests={r['total_tests']}, infra={r['infra']}, onnx={r['onnx']}, gpu={r['gpu']}, stripe={r['stripe']}\")

print()
print('='*70)
print('FINAL RESULTS')
print('='*70)
print(f\"Total number of test functions: {totals['total_tests']}\")
print(f\"Tests marked @pytest.mark.infra: {totals['infra']}\")
print(f\"Tests marked @pytest.mark.redis: {totals['redis']}\")
print(f\"Tests marked @pytest.mark.stripe: {totals['stripe']}\")
print(f\"Tests marked @pytest.mark.openai: {totals['openai']}\")  
print(f\"Tests marked @pytest.mark.onnx: {totals['onnx']}\")
print(f\"Tests marked @pytest.mark.pgvector: {totals['pgvector']}\")
print(f\"Tests marked @pytest.mark.gpu: {totals['gpu']}\")
