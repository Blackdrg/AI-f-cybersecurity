#!/bin/bash
# AI-f Sovereign OS - SBOM Generation Script (CycloneDX)
# Requirements: pip install cyclonedx-bom

echo "[*] Generating Software Bill of Materials (SBOM)..."

if ! command -v cyclonedx-py &> /dev/null
then
    echo "[!] cyclonedx-py not found. Installing..."
    pip install cyclonedx-bom
fi

# Generate SBOM for backend
cd backend
cyclonedx-py requirements requirements.txt --output-format json --output-file sbom.json

echo "[+] SBOM generated at backend/sbom.json"

# Check for known vulnerabilities
echo "[*] Running vulnerability audit..."
pip install pip-audit
pip-audit -r requirements.txt --format json > audit_report.json

echo "[+] Vulnerability report generated at backend/audit_report.json"
