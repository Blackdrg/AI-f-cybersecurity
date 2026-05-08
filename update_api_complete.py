#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete README API documentation update script.
Performs targeted edits to add missing endpoints.
"""

readme_path = r"D:\AI-F\AI-f\README.md"

with open(readme_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Expand Admin & Analytics table (the early one at line ~871)
# Find and replace the table header+ rows to add three more rows after index/rebuild
old_admin_table = """| `POST /api/admin/index/rebuild` | Rebuild ANN index | Admin | Vector index maintenance |

### 💳 Subscriptions & Billing"""

new_admin_table = """| `POST /api/admin/index/rebuild` | Rebuild ANN index | Admin | Vector index maintenance |
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

### 💳 Subscriptions & Billing"""

if old_admin_table in content:
    content = content.replace(old_admin_table, new_admin_table)
    print("✓ Expanded early Admin & Analytics table")
else:
    print("⚠ Early Admin table pattern not found - skipping")

# 2. Update Legal & Compliance block (replace stale legal endpoints with actual ones)
old_legal_block = """**Compliance & Consent:**
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
| GET | `/api/legal/data-processing-agreement` | DPA document |

**Versioned Admin & Compliance (v1):**"""

new_legal_block = """**Compliance & Consent:**
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
| GET | `/api/legal/compliance/impact-assessment` | Data protection impact assessment |

**Versioned Admin & Compliance (v1):**"""

if old_legal_block in content:
    content = content.replace(old_legal_block, new_legal_block)
    print("✓ Updated Legal & Compliance endpoints (replaced stale static endpoints)")
else:
    print("⚠ Legal block pattern not found - skipping")

# 3. Expand Recognition V2 section to include missing ground-truth and policy/report
# Find the Recognition V2 section (we inserted earlier maybe, but if not, there is already one)
# Actually there are two potential places: earlier we might have inserted a new section; also there is mention in main API reference.
# Let's search for "### 🎯 Recognition V2 Enhanced Endpoints" that we inserted
if '### 🎯 Recognition V2 Enhanced Endpoints' in content:
    # We inserted this, now want to expand it to include missing endpoints
    old_v2_section = """### 🎯 Recognition V2 Enhanced Endpoints

**Implementation:** `backend/app/api/recognition_v2.py` (mounted at `/api/v2`)

| Endpoint | Method | Permission | Description |
|----------|--------|-------------|-------------|
| `POST /api/v2/recognize` | Enhanced recognition | `VIEW_RECOGNITIONS` | Multi-modal with scoring engine |
| `GET /api/v2/scoring/metrics` | Scoring metrics | `VIEW_RECOGNITIONS` | Detailed confidence breakdown |
| `GET /api/v2/evaluation/report` | Performance report | `VIEW_ANALYTICS` | Model evaluation data |
| `GET /api/v2/evaluation/drift` | Drift detection | `VIEW_ANALYTICS` | Real-time data drift monitoring |
| `POST /api/v2/policy/rules` | Create policy rule | Admin | Custom recognition policy |
| `POST /api/v2/policy/check` | Check policy | `VIEW_RECOGNITIONS` | Evaluate against active policies |

"""
    new_v2_section = """### 🎯 Recognition V2 Enhanced Endpoints

**Implementation:** `backend/app/api/recognition_v2.py` (mounted at `/api/v2`)

| Endpoint | Method | Permission | Description |
|----------|--------|-------------|-------------|
| `POST /api/v2/recognize` | Enhanced recognition | `VIEW_RECOGNITIONS` | Multi-modal with scoring engine |
| `GET /api/v2/scoring/metrics` | Scoring metrics | `VIEW_RECOGNITIONS` | Detailed confidence breakdown |
| `GET /api/v2/evaluation/report` | Performance report | `VIEW_ANALYTICS` | Model evaluation data |
| `GET /api/v2/evaluation/drift` | Drift detection | `VIEW_ANALYTICS` | Real-time data drift monitoring |
| `POST /api/v2/evaluation/ground-truth` | Submit ground truth | `MANAGE_MODELS` | HITL truth labeling for FL |
| `GET /api/v2/policy/report` | Policy report | `VIEW_ANALYTICS` | Current policy engine report |
| `POST /api/v2/policy/rules` | Create policy rule | Admin | Custom recognition policy |
| `POST /api/v2/policy/check` | Check policy | `VIEW_RECOGNITIONS` | Evaluate against active policies |

"""
    content = content.replace(old_v2_section, new_v2_section)
    print("✓ Updated Recognition V2 section with missing endpoints")
else:
    # If we haven't inserted the section yet (because our earlier insertion didn't happen), skip
    print("⚠ Recognition V2 section not found (may be handled later)")

# 4. Also ensure early Recognition V2 mentions include ground-truth and policy/report if missing
# The existing part under "### 👤 Identity & Recognition" already lists some v2 endpoints but not all.
# Find those rows and extend them? Actually that table includes rows for recognize_v2, scoring/metrics, evaluation/report, evaluation/drift, policy/rules, policy/check. It does not include ground-truth or policy/report. Let's check lines ~829-834.

# But maybe we shouldn't duplicate? We could add them to that table too. However it's fine to have comprehensive section later.

# Write back
with open(readme_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ API documentation update complete")
