import subprocess
import sys
import os

os.chdir(r'D:\AI-F\AI-f\backend')
result = subprocess.run([
    sys.executable, '-m', 'pytest',
    'tests/test_mpc_enhanced.py::TestZKPIntegration::test_multiplication_proof_generation',
    '-v', '--tb=long'
], capture_output=True, text=True, cwd=r'D:\AI-F\AI-f\backend')
print(result.stdout[-8000:])
print(result.stderr[-3000:] if result.stderr else '')