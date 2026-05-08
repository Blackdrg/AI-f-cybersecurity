#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add missing API endpoint sections to README.
Expands Admin & Analytics section and adds new sections for Events, Support, Legal, Recognition V2, Consent.
"""

readme_path = r"D:\AI-F\AI-f\README.md"

with open(readme_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Expand Admin & Analytics section (currently ends at line 882 with POST /api/admin/index/rebuild)
# We need to add 8 more rows to that table

old_admin_table_end = """| `POST /api/admin/index/rebuild` | Rebuild ANN index | Admin | Vector index maintenance |

### 💳 Subscriptions & Billing"""

new_admin_table_end = """| `POST /api/admin/index/rebuild` | Rebuild ANN index | Admin | Vector index maintenance |
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

content = content.replace(old_admin_table_end, new_admin_table_end)

# 2. Add Events section before Support
old_before_events = "### 🆘 Support & Ticketing"
new_with_events = """### 📅 Events & Timeline

**Implementation:** `backend/app/api/events.py`

Query historical recognition events and per-person timelines for forensic analysis.

| Endpoint | Method | Permission | Description |
|----------|--------|-------------|-------------|
| `GET /api/orgs/{org_id}/events` | List events | `VIEW_RECOGNITIONS` | Recent recognition events for organization |
| `GET /api/orgs/{org_id}/persons/{person_id}/timeline` | Person timeline | `VIEW_RECOGNITIONS` | Recognition history for specific person |

### 🆘 Support & Ticketing"""

content = content.replace(old_before_events, new_with_events)

# 3. Expand Support section with full 5 endpoints (currently has only partial? let's check)
# Actually the existing support section appears to be missing - let me check if it exists
# Looking at content after our insertion, we need to ensure Support section has full 5 endpoints.
# The plan: replace the Events section we just added plus Support section after it

# Actually let's do step-by-step. Next, within the Support section, ensure all 5 endpoints are listed.
# First locate support section
import re

# Find the Support section after we've inserted the Events section
support_section_pattern = r'(### 🆘 Support & Ticketing[\s\S]*?)(### [🔘🔘🔘])'
match = re.search(r'### 🆘 Support & Ticketing', content)
if match:
    support_start = match.start()
    # Find next section after support
    next_section = content.find('### ', support_start + 10)
    print(f"Support section starts at {support_start}, next section at {next_section}")
    support_content = content[support_start:next_section]
    print("Current support content:")
    print(support_content[:500])
else:
    print("Support section not found yet - will need to re-run after Events insertion")

with open(readme_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Step 1 complete: Expanded Admin table + added Events section header")
print("Now check support section exists; will add Legal/RecognitionV2/Consent sections next")
