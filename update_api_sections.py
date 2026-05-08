#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update README.md with missing API endpoints and sections.
"""

readme_path = r"D:\AI-F\AI-f\README.md"

with open(readme_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We'll build new content by inserting at multiple positions
# Keep track of insertions (position, text)
insertions = []

# 1. Expand Admin & Analytics table: after line 882 (the rebuild line), insert 9 new rows
# Find the line with "POST /api/admin/index/rebuild"
admin_rebuild_idx = None
for i, line in enumerate(lines):
    if 'POST /api/admin/index/rebuild' in line and 'Rebuild ANN index' in line:
        admin_rebuild_idx = i
        break

if admin_rebuild_idx is None:
    print("ERROR: Could not find admin rebuild line")
    exit(1)

print(f"Found admin rebuild at line {admin_rebuild_idx+1}")

# Additional admin endpoints to insert (each is a table row)
new_admin_rows = """| `GET /api/admin/policies` | List policies | Admin | All policy rules |
| `PUT /api/admin/policies/{policy_id}` | Update policy | Admin | Enable/disable rule |
| `GET /api/admin/systems/status` | System health | Admin | Component status (DB, Redis, models) |
| `GET /api/admin/compliance/status` | Compliance score | Admin | Overall compliance percentage |
| `GET /api/admin/security/threats` | Security threats | Admin | Recent threat intelligence |
| `GET /api/admin/analytics/risk-metrics` | Risk metrics | Admin | Critical/high/medium/resolved counts |
| `GET /api/admin/analytics/risk-trends` | Risk trends | Admin | Time-series risk score data |
| `GET /api/admin/sessions/active` | Active sessions | Admin | Live identity sessions with behavioral data |
| `GET /api/admin/logs` | Audit logs | Admin | Filterable log retrieval |
"""
# Insert after the rebuild line (at position admin_rebuild_idx + 1, before blank line)
insertions.append((admin_rebuild_idx + 1, new_admin_rows))

# 2. Add Events section: Insert before "### 🆘 Support & Ticketing"
# First find Support section
support_idx = None
for i, line in enumerate(lines):
    if '### 🆘 Support & Ticketing' in line:
        support_idx = i
        break

if support_idx is None:
    print("ERROR: Could not find Support section")
    exit(1)

print(f"Found Support section at line {support_idx+1}")

events_section = """### 📅 Events & Timeline

**Implementation:** `backend/app/api/events.py`

Query historical recognition events and per-person timelines for forensic analysis.

| Endpoint | Method | Permission | Description |
|----------|--------|-------------|-------------|
| `GET /api/orgs/{org_id}/events` | List events | `VIEW_RECOGNITIONS` | Recent recognition events for organization |
| `GET /api/orgs/{org_id}/persons/{person_id}/timeline` | Person timeline | `VIEW_RECOGNITIONS` | Recognition history for specific person |

"""
insertions.append((support_idx, events_section))

# 3. After Support section, we might want to ensure full content - but Support already has content
# Let's check if Support section is complete (5 endpoints). We'll verify after insertion.

# 4. Add Legal section: Insert before "### ⚖️ Compliance (GDPR/CCPA/BIPA)"
compliance_idx = None
for i, line in enumerate(lines):
    if '### ⚖️ Compliance (GDPR/CCPA/BIPA)' in line:
        compliance_idx = i
        break

if compliance_idx is None:
    print("ERROR: Could not find Compliance section")
    exit(1)

print(f"Found Compliance section at line {compliance_idx+1}")

legal_section = """### ⚖️ Legal & Compliance Router

**Implementation:** `backend/app/api/legal.py`

Dedicated endpoints for BIPA, GDPR, and CCPA automation.

| Endpoint | Method | Permission | Description |
|----------|--------|-------------|-------------|
| `POST /api/legal/consent` | Create consent | User | Record biometric consent (ZKP-audited) |
| `DELETE /api/legal/consent/{consent_id}` | Withdraw consent | User | Revoke biometric consent (BIPA Art 7) |
| `GET /api/legal/compliance/features` | Available features | None | Region-specific compliance capabilities |
| `GET /api/legal/compliance/audit` | Audit trail | User | Personal audit log (last 50 entries) |
| `GET /api/legal/compliance/data-subject` | DSAR request | User | Full data subject access report |
| `POST /api/legal/compliance/delete` | Deletion request | User | GDPR Article 17 erasure trigger |
| `GET /api/legal/compliance/impact-assessment` | DPIA | None | Data protection impact assessment |

"""
insertions.append((compliance_idx, legal_section))

# 5. Add Recognition V2 section: Insert before "### 🔐 Consent Management (BIPA Compliance)"
# But actually we have Consent already, let's find it
consent_idx = None
for i, line in enumerate(lines):
    if '### 🔐 Consent Management' in line or '### Consent Management' in line:
        consent_idx = i
        break

if consent_idx is None:
    print("WARNING: Could not find Consent section - will insert before Plugin System")
    # Fallback: find Plugin System
    for i, line in enumerate(lines):
        if '### 🔌 Plugin System' in line:
            consent_idx = i
            break

if consent_idx is None:
    print("ERROR: Could not find suitable insertion point for Recognition V2")
    exit(1)

print(f"Found Consent/Plugin section at line {consent_idx+1}")

recognition_v2_section = """### 🎯 Recognition V2 Enhanced Endpoints

**Implementation:** `backend/app/api/recognition_v2.py` (mounted at `/api/v2`)

| Endpoint | Method | Permission | Description |
|----------|--------|-------------|-------------|
| `POST /api/v2/recognize` | Enhanced recognition | `VIEW_RECOGNITIONS` | Multi-modal with scoring engine |
| `GET /api/v2/scoring/metrics` | Scoring metrics | `VIEW_RECOGNITIONS` | Detailed confidence breakdown |
| `GET /api/v2/evaluation/report` | Performance report | `VIEW_ANALYTICS` | Model evaluation data |
| `GET /api/v2/evaluation/drift` | Drift detection | `VIEW_ANALYTICS` | Real-time data drift monitoring |
| `POST /api/v2/evaluation/ground-truth` | Submit ground truth | `MANAGE_MODELS` | HITL truth labeling for FL |
| `POST /api/v2/policy/rules` | Create policy rule | Admin | Custom recognition policy |
| `POST /api/v2/policy/check` | Check policy | `VIEW_RECOGNITIONS` | Evaluate against active policies |

"""
insertions.append((consent_idx, recognition_v2_section))

# Sort insertions by position descending to avoid index shifting
insertions.sort(key=lambda x: x[0], reverse=True)

for pos, text in insertions:
    lines.insert(pos, text)

# Write back
with open(readme_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"\n✓ Successfully performed {len(insertions)} insertions")
print("Updated sections:")
print("  1. Expanded Admin & Analytics table (+9 endpoints)")
print("  2. Added Events & Timeline section")
print("  3. Added Legal & Compliance Router section")
print("  4. Added Recognition V2 Enhanced Endpoints section")
print(f"\nNew total lines: {len(lines)}")
