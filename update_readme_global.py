#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Global README update for missing API endpoints and frontend components.
Performs global string replacements (affects all occurrences).
"""

readme_path = r"D:\AI-F\AI-f\README.md"

with open(readme_path, 'r', encoding='utf-8') as f:
    content = f.read()

# === 1. Expand early Admin & Analytics tables (all occurrences) ===
# The block to find: backtick rows with feedback, upload, download, rebuild (the four lines)
old_admin_block = """| `POST /api/admin/feedback` | Submit human feedback | `MANAGE_USERS` | HITL correction |
| `POST /api/admin/models/upload` | Upload model version | Admin | OTA model distribution |
| `GET /api/admin/models/download` | Download model | Admin | Edge device OTA fetch |
| `POST /api/admin/index/rebuild` | Rebuild ANN index | Admin | Vector index maintenance |"""

new_admin_block = """| `POST /api/admin/feedback` | Submit human feedback | `MANAGE_USERS` | HITL correction |
| `POST /api/admin/models/upload` | Upload model version | Admin | OTA model distribution |
| `GET /api/admin/models/download` | Download model | Admin | Edge device OTA fetch |
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
| `GET /api/admin/logs` | Audit logs | Admin | Filterable log retrieval |"""

count1 = content.count(old_admin_block)
if count1:
    content = content.replace(old_admin_block, new_admin_block)
    print(f"[OK] Expanded Admin & Analytics tables ({count1} occurrence(s))")
else:
    print("[WARN] No matches for Admin block")

# === 2. Update Legal & Compliance block (all occurrences) ===
old_legal = """| GET | `/api/legal/privacy-policy` | Current privacy policy |
| GET | `/api/legal/terms-of-service` | Terms of service |
| POST | `/api/legal/consent/accept` | Accept updated terms |
| GET | `/api/legal/data-processing-agreement` | DPA document |"""

new_legal = """| POST | `/api/legal/consent` | Create consent record (ZKP-audited) |
| DELETE | `/api/legal/consent/{consent_id}` | Withdraw consent (BIPA Art 7) |
| GET | `/api/legal/compliance/features` | Region-specific compliance capabilities |
| GET | `/api/legal/compliance/audit` | Personal audit log (last 50 entries) |
| GET | `/api/legal/compliance/data-subject` | Full data subject access report |
| POST | `/api/legal/compliance/delete` | GDPR Article 17 erasure trigger |
| GET | `/api/legal/compliance/impact-assessment` | Data protection impact assessment |"""

count2 = content.count(old_legal)
if count2:
    content = content.replace(old_legal, new_legal)
    print(f"[OK] Updated Legal & Compliance endpoints ({count2} occurrence(s))")
else:
    print("[WARN] No matches for Legal block")

# === 3. Add missing V2 endpoints to Identity & Recognition table ===
old_policy_check = "| `POST /api/recognize_v2/policy/check` | Check policy | `VIEW_RECOGNITIONS` | Evaluate against policy |"
new_policy_check_with_extra = old_policy_check + "\n| `POST /api/recognize_v2/evaluation/ground-truth` | Submit ground truth | `MANAGE_MODELS` | HITL truth labeling for FL |\n| `GET /api/recognize_v2/policy/report` | Policy report | `VIEW_ANALYTICS` | Current policy engine report |"

count3 = content.count(old_policy_check)
if count3:
    content = content.replace(old_policy_check, new_policy_check_with_extra)
    print(f"[OK] Added V2 missing endpoints to Identity table ({count3} occurrence(s))")
else:
    print("[WARN] Policy/check row not found in Identity table")

# === 4. Expand Enhanced Recognition (v2) summary section ===
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
count4 = content.count(old_v2_summary)
if count4:
    content = content.replace(old_v2_summary, new_v2_summary)
    print(f"[OK] Expanded Enhanced Recognition (v2) summary ({count4} occurrence(s))")
else:
    print("[WARN] Enhanced Recognition v2 summary not found")

# === Write back ===
with open(readme_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n[OK] README update script complete.")
