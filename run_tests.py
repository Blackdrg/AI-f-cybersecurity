"""Simple test runner that outputs results to a file."""
import subprocess
import sys

# Run pytest with output to file
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_recognize.py", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    cwd="backend"
)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
