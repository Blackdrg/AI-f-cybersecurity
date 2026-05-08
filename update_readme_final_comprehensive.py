#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
README comprehensive update: add missing API endpoints, expand tables.
"""

readme_path = r"D:\AI-F\AI-f\README.md"

with open(readme_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Track changes
changes = []

# 1. Expand early Admin & Analytics table (before Subscriptions)
old1 = """| `GET /api/admin/models/download` | Download model | Admin | Edge device OTA fetch |
| `POST /api/admin/index/rebuild` | Rebuild ANN index | Admin | Vector index maintenance |

### 🏷️ Subscriptions & Billing"""

new1 = """| `GET /api/admin/models/download` | Download model | Admin | Edge device OTA fetch |
| `POST /api/admin/index/rebuild` | Rebuild ANN index | Admin | Vector index maintenance |
| `GET /api/admin/persons/{person_id}` | Get person details | `VIEW_IDENTITIES` | View identity profile |
| `POST /api/admin/persons/{person_id}/revoke` | Revoke identity | Admin | Soft delete (mark) |
| `DELETE /api/admin/persons/{person_id}` | Delete identity | `MANAGE_USERS` | Hard delete record |
| `POST /api/admin/consent_vault` | Manage consent vault | Auth | Grant/revoke/view consent records |
| `GET /api/admin/policies` | List policies | Admin | All policy rules |
| `PUT /api/admin/policies/{policy_id}` | Update policy | Admin | Enable/disable rule |
| `GET /api/admin/systems/status` | System health | Admin | Component status (DB, Redis, models) |
| `GET /api/admin/compliance/status` | Compliance score | Admin | Overall compliance percentage |
| `GET /api/admin/security/threats` | Security threats | Admin | Recent threat intelligence |
| `GET /api/admin/analytics/risk-metrics` | Risk metrics | Admin | Critical/high/medium/resolved counts |
| `GET /api/admin/analytics/risk-trends` | Risk trends | Admin | Time-series risk score data |
| `GET /api/admin/sessions/active` | Active sessions | Admin | Live identity sessions with behavioral data |
| `GET /api/admin/logs` | Audit logs | Admin | Filterable log retrieval |

### 🏷️ Subscriptions & Billing"""

if old1 in content:
    content = content.replace(old1, new1)
    changes.append("Expanded early Admin & Analytics table")
else:
    print("⚠ Pattern for early Admin table not found")

# 2. Expand Admin & Operations block (two occurrences - will replace both later via separate script? We'll handle both by replacing the whole block twice with updated counts.
# We'll use a function to replace each occurrence.

def update_admin_ops_block(content_block):
    old_block = """**Admin & Operations (12 endpoints):**
| Method | Endpoint | RBAC | Description |
|--------|----------|------|-------------|
| GET | `/api/admin/metrics` | `VIEW_METRICS` | System metrics (Prometheus aggregate) |
| GET | `/api/admin/logs` | `VIEW_AUDIT_LOGS` | Audit log query with filters |
| POST | `/api/admin/index/rebuild` | `MANAGE_INDEX` | Rebuild vector HNSW index (async) |
| GET | `/api/admin/health` | `ADMIN` | Detailed dependency health |
| POST | `/api/admin/models/reload` | `ADMIN` | Hot-reload ML models |
| GET | `/api/admin/queues` | `ADMIN` | Celery queue depth + worker status |
| GET | `/api/admin/analytics` | `ADMIN` | Time-series analytics (recognitions/enrollments) |
| POST | `/api/admin/feedback` | `ADMIN` | Submit recognition feedback (TP/FP/FN) |
| POST | `/api/admin/models/upload` | `ADMIN` | Upload new model version |
| GET | `/api/admin/models/download` | `ADMIN` | Download model for edge OTA |
| GET | `/api/admin/bias_report` | `OPERATOR` | Bias detection report |
| GET | `/api/admin/systems/status` | `ADMIN` | All systems status (policy, models, DB, Redis)
"""
    new_block = """**Admin & Operations (19 endpoints):**
| Method | Endpoint | RBAC | Description |
|--------|----------|------|-------------|
| GET | `/api/admin/metrics` | `VIEW_METRICS` | System metrics (Prometheus aggregate) |
| GET | `/api/admin/logs` | `VIEW_AUDIT_LOGS` | Audit log query with filters |
| POST | `/api/admin/index/rebuild` | `MANAGE_INDEX` | Rebuild vector HNSW index (async) |
| GET | `/api/admin/health` | `ADMIN` | Detailed dependency health |
| POST | `/api/admin/models/reload` | `ADMIN` | Hot-reload ML models |
| GET | `/api/admin/queues` | `ADMIN` | Celery queue depth + worker status |
| GET | `/api/admin/analytics` | `ADMIN` | Time-series analytics (recognitions/enrollments) |
| POST | `/api/admin/feedback` | `ADMIN` | Submit recognition feedback (TP/FP/FN) |
| POST | `/api/admin/models/upload` | `ADMIN` | Upload new model version |
| GET | `/api/admin/models/download` | `ADMIN` | Download model for edge OTA |
| GET | `/api/admin/bias_report` | `OPERATOR` | Bias detection report |
| GET | `/api/admin/systems/status` | `ADMIN` | All systems status (policy, models, DB, Redis)
| GET | `/api/admin/policies` | `ADMIN` | List all policy rules |
| PUT | `/api/admin/policies/{policy_id}` | `ADMIN` | Enable/disable a policy |
| GET | `/api/admin/compliance/status` | `ADMIN` | Overall compliance score |
| GET | `/api/admin/security/threats` | `ADMIN` | Recent security threat intelligence |
| GET | `/api/admin/analytics/risk-metrics` | `ADMIN` | Critical/high/medium/resolved risk counts |
| GET | `/api/admin/analytics/risk-trends` | `ADMIN` | Time-series risk score data |
| GET | `/api/admin/sessions/active` | `ADMIN` | Active identity sessions with behavioral data |
"""
    return content_block.replace(old_block, new_block)

content = update_admin_ops_block(content)
# After first replacement, the second occurrence (later) should also be updated (still present in the modified content)
content = update_admin_ops_block(content)
changes.append("Expanded Admin & Operations tables (2 occurrences)")

# 3. Update Legal & Compliance block
old_legal = """**Compliance & Consent:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/compliance/export/{person_id}` | GDPR data export (DSAR) |
| DELETE | `/api/compliance/delete/{person_id}` | GDPR right to erasure |
| GET | `/api/compliance/status` | System compliance status |
| GET | `/api/audit/verify` | Verify entire audit chain integrity |
| GET | `/api/audit/forensic/{event_id}` | Forensic trace for event |
| POST | `/api/consent/enroll` | Record biometric consent (BIPA) |
| GET | `/api/consent/verify` | Verify consent token validity |
| POST | `/api/consent/revoke` | Withdraw consent (GDPR Art 7) |
| GET | `/api/consent/history` | User consent history |
| GET | `/api/legal/privacy-policy` | Current privacy policy |
| GET | `/api/legal/terms-of-service` | Terms of service |
| POST | `/api/legal/consent/accept` | Accept updated terms |
| GET | `/api/legal/data-processing-agreement` | DPA document |"""

new_legal = """**Compliance & Consent:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/compliance/export/{person_id}` | GDPR data export (DSAR) |
| DELETE | `/api/compliance/delete/{person_id}` | GDPR right to erasure |
| GET | `/api/compliance/status` | System compliance status |
| GET | `/api/audit/verify` | Verify entire audit chain integrity |
| GET | `/api/audit/forensic/{event_id}` | Forensic trace for event |
| POST | `/api/consent/enroll` | Record biometric consent (BIPA) |
| GET | `/api/consent/verify` | Verify consent token validity |
| POST | `/api/consent/revoke` | Withdraw consent (GDPR Art 7) |
| GET | `/api/consent/history` | User consent history |
| POST | `/api/legal/consent` | Create consent record (ZKP-audited) |
| DELETE | `/api/legal/consent/{consent_id}` | Withdraw consent (BIPA Art 7) |
| GET | `/api/legal/compliance/features` | Region-specific compliance capabilities |
| GET | `/api/legal/compliance/audit` | Personal audit log (last 50 entries) |
| GET | `/api/legal/compliance/data-subject` | Full data subject access report |
| POST | `/api/legal/compliance/delete` | GDPR Article 17 erasure trigger |
| GET | `/api/legal/compliance/impact-assessment` | Data protection impact assessment |"""

if old_legal in content:
    content = content.replace(old_legal, new_legal)
    changes.append("Updated Legal & Compliance endpoints (replaced 4 stale with 7 current)")
else:
    print("⚠ Legal block pattern not found")

# 4. Add missing V2 endpoints to early Identity & Recognition table
# Find the policy/check row and insert after
old_policy_check_row = "| `POST /api/recognize_v2/policy/check` | Check policy | `VIEW_RECOGNITIONS` | Evaluate against policy |"
if old_policy_check_row in content:
    addition = "\n| `POST /api/recognize_v2/evaluation/ground-truth` | Submit ground truth | `MANAGE_MODELS` | HITL truth labeling for FL |\n| `GET /api/recognize_v2/policy/report` | Policy report | `VIEW_ANALYTICS` | Current policy engine report |\n"
    content = content.replace(old_policy_check_row, old_policy_check_row + addition)
    changes.append("Added missing V2 endpoints (ground-truth, policy/report) to Identity table")
else:
    print("⚠ Policy/check row not found")

# 5. Expand Enhanced Recognition (v2) section
old_v2_summary = """**Enhanced Recognition (v2):**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v2/recognize` | Required | Enhanced with scoring engine + environment calibration |
| GET | `/api/v2/models/status` | Required | Current model version + metrics |
"""
new_v2_summary = """**Enhanced Recognition (v2):**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v2/recognize` | Required | Enhanced with scoring engine + environment calibration |
| GET | `/api/v2/models/status` | Required | Current model version + metrics |
| GET | `/api/v2/scoring/metrics` | Required | Detailed confidence breakdown |
| GET | `/api/v2/evaluation/report` | Required | Model evaluation data |
| GET | `/api/v2/evaluation/drift` | Required | Real-time data drift monitoring |
| POST | `/api/v2/evaluation/ground-truth` | Required | HITL truth labeling for FL |
| GET | `/api/v2/policy/report` | Required | Current policy engine report |
| POST | `/api/v2/policy/rules` | Admin | Custom recognition policy |
| POST | `/api/v2/policy/check` | Required | Evaluate against active policies |
"""
if old_v2_summary in content:
    content = content.replace(old_v2_summary, new_v2_summary)
    changes.append("Expanded Enhanced Recognition (v2) section with full endpoints")
else:
    print("⚠ Enhanced Recognition v2 block not found")

# Write back
with open(readme_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ README update complete. Changes applied:")
for c in changes:
    print(" -", c)
