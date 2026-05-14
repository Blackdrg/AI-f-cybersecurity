#!/usr/bin/env python3
"""Final syntax validation of all new/modified files."""
import py_compile
import sys
import os

ROOT = os.path.join("D:", os.sep, "AI-F", "AI-f")

FILES_TO_CHECK = [
    "backend/app/services/ioc_repository.py",
    "backend/app/providers/virustotal_provider.py",
    "backend/app/providers/urlhaus_provider.py",
    "backend/app/providers/emerging_threats_provider.py",
    "backend/app/providers/stix_taxii_provider.py",
    "backend/app/services/threat_cache.py",
    "backend/app/services/threat_enrichment_pipeline.py",
    "backend/app/services/threat_enhanced_recognition.py",
    "backend/app/services/connector_engine.py",
    "backend/app/services/incident_orchestrator.py",
    "backend/app/services/orchestrated_response.py",
    "backend/app/tasks/threat_intel_tasks.py",
    "backend/app/monitoring/observability.py",
    "backend/app/services/compliance_engine.py",
    "backend/app/sdk_validation.py",
    "backend/app/tests/test_threat_intel.py",
    "backend/app/tests/test_performance_validated.py",
    "backend/app/api/v1/compliance.py",
    "backend/app/api/alerts.py",
    "backend/app/main.py",
    "backend/app/celery.py",
    "backend/app/schemas.py",
]

errors = []
passed = 0
for f in FILES_TO_CHECK:
    path = os.path.join(ROOT, f.replace("/", os.sep))
    if not os.path.exists(path):
        print("MISSING: {}".format(f))
        errors.append(f)
        continue
    try:
        py_compile.compile(path, doraise=True)
        print("OK: {}".format(f))
        passed += 1
    except py_compile.PyCompileError as e:
        print("ERROR: {}: {}".format(f, e))
        errors.append(f)

print("")
print("=" * 50)
print("Results: {} passed, {} errors out of {} files".format(
    passed, len(errors), len(FILES_TO_CHECK)))
print("=" * 50)

if errors:
    print("\nFiles with errors:")
    for e in errors:
        print("  - {}".format(e))
    sys.exit(1)
else:
    print("All files compiled successfully!")
    sys.exit(0)