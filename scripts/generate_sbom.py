#!/usr/bin/env python3
"""
Generate a Software Bill of Materials (SBOM) for AI-f.

Outputs a CycloneDX-compatible JSON SBOM listing Python dependencies
from backend/requirements.txt and Node.js dependencies from ui/react-app/package.json.

Usage:
    python scripts/generate_sbom.py [--output sbom.json]

Author: AI-f Security Team
"""

import json
import os
import re
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any

def parse_requirements(requirements_path: str) -> List[Dict[str, Any]]:
    """Parse requirements.txt into SBOM components."""
    components = []
    if not os.path.exists(requirements_path):
        print(f"Warning: {requirements_path} not found", file=sys.stderr)
        return components

    with open(requirements_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Parse "package==version" or "package>=version" etc.
            match = re.match(r'^([a-zA-Z0-9_.-]+)\s*([=<>!~]+)\s*([a-zA-Z0-9_.-]+)', line)
            if match:
                name = match.group(1)
                version = match.group(3)
                components.append({
                    "type": "library",
                    "name": name,
                    "version": version,
                    "purl": f"pkg:pypi/{name}@{version}",
                    "scope": "required"
                })
            else:
                # Just package name without version constraint
                name = line.split()[0]
                components.append({
                    "type": "library",
                    "name": name,
                    "version": "unknown",
                    "purl": f"pkg:pypi/{name}",
                    "scope": "required"
                })
    return components

def parse_package_json(package_path: str) -> List[Dict[str, Any]]:
    """Parse package.json for frontend dependencies."""
    components = []
    if not os.path.exists(package_path):
        return components
    with open(package_path, 'r') as f:
        pkg = json.load(f)
    deps = pkg.get('dependencies', {})
    deps.update(pkg.get('devDependencies', {}))
    for name, version in deps.items():
        components.append({
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:npm/{name}@{version}",
            "scope": "required"
        })
    return components

def generate_sbom(backend_reqs: str, frontend_pkg: str) -> Dict[str, Any]:
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "version": 1,
        "serialNumber": f"urn:uuid:{os.urandom(16).hex()}",
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tools": [
                {
                    "vendor": "AI-f",
                    "name": "generate_sbom.py",
                    "version": "1.0"
                }
            ],
            "component": {
                "type": "application",
                "name": "AI-f Enterprise Face Recognition Platform",
                "version": "2.2.1"
            }
        },
        "components": []
    }

    # Add backend Python components
    bom["components"].extend(parse_requirements(backend_reqs))

    # Add frontend Node components
    bom["components"].extend(parse_package_json(frontend_pkg))

    return bom

def main():
    parser = argparse.ArgumentParser(description="Generate SBOM for AI-f")
    parser.add_argument('--output', default='docs/sbom/sbom.json', help='Output SBOM file path')
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_reqs = os.path.join(repo_root, 'backend', 'requirements.txt')
    frontend_pkg = os.path.join(repo_root, 'ui', 'react-app', 'package.json')

    sbom = generate_sbom(backend_reqs, frontend_pkg)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(sbom, f, indent=2)

    print(f"SBOM generated: {args.output} ({len(sbom['components'])} components)")

if __name__ == '__main__':
    main()
