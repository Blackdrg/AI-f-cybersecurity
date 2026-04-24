#!/bin/bash
#
# AI-f Quick Diagnostics Bundle
# One-stop troubleshooting for common issues
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "AI-f Quick Diagnostics Bundle"
echo "=========================================="
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Create temporary report
REPORT_DIR="/tmp/ai-f-diagnostics-$(date +%s)"
mkdir -p "$REPORT_DIR"

# Run all checks
echo "Running system checks... (this may take 1-2 minutes)"
echo ""

# 1. Python diagnostics
echo "1/5: Python diagnostics..."
if python3 scripts/diagnostics.py --quick --output "$REPORT_DIR/system.json" 2>/dev/null; then
    echo "   ✓ Python/systems check complete"
else
    echo "   ⚠ Python check had issues"
fi

# 2. Database diagnostics
echo "2/5: Database diagnostics..."
if python3 scripts/db_diagnostics.py --output "$REPORT_DIR/database.json" 2>/dev/null; then
    echo "   ✓ Database check complete"
else
    echo "   ⚠ Database check had issues"
fi

# 3. Health check
echo "3/5: Service health..."
if bash scripts/health_check.sh > "$REPORT_DIR/health.txt" 2>&1; then
    echo "   ✓ Health check complete"
else
    echo "   ⚠ Health check had issues"
fi

# 4. Log scan (last 1000 lines)
echo "4/5: Recent log analysis..."
find logs -name "*.log" -type f 2>/dev/null | head -5 | while read logfile; do
    tail -1000 "$logfile" > "$REPORT_DIR/$(basename "$logfile").recent" 2>/dev/null || true
done
echo "   ✓ Log snapshot captured"

# 5. Docker status
echo "5/5: Container status..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" > "$REPORT_DIR/containers.txt" 2>/dev/null || true
echo "   ✓ Container status captured"

# Generate combined report
echo ""
echo "=========================================="
echo "DIAGNOSTICS COMPLETE"
echo "=========================================="
echo ""
echo "Report saved to: $REPORT_DIR"
echo ""
echo "Files:"
ls -1 "$REPORT_DIR" 2>/dev/null | sed 's/^/  /'

# Print summary
if [ -f "$REPORT_DIR/system.json" ]; then
    echo ""
    echo "Key findings:"
    python3 -c "
import json, sys
with open('$REPORT_DIR/system.json') as f:
    data = json.load(f)
issues = len(data.get('issues', []))
warns = len(data.get('warnings', []))
passed = len(data.get('passed', []))
print(f'  ✓ Passed: {passed}')
print(f'  ⚠ Warnings: {warns}')
print(f'  ✗ Critical: {issues}')
if issues > 0:
    print('')
    print('Top issues:')
    for issue in data.get('issues', [])[:3]:
        print(f'   • {issue}')
" 2>/dev/null || true
fi

echo ""
echo "To view full report:"
echo "  cat $REPORT_DIR/*.json | python3 -m json.tool"
echo ""
echo "For support, send the entire $REPORT_DIR directory."
