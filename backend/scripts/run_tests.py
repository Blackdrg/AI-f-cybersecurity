import subprocess
import sys
import os

os.chdir(r'D:\AI-F\AI-f\backend')

result = subprocess.run([
    sys.executable, '-m', 'pytest',
    'tests/test_pqc.py', 'tests/test_pqc_enhanced.py',
    'tests/test_mpc_enhanced.py', 'tests/test_hsm.py',
    '-v', '--tb=short'
], capture_output=True, text=True, cwd=r'D:\AI-F\AI-f\backend')

print(result.stdout[-12000:] if len(result.stdout) > 12000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-3000:])