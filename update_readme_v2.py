#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update README.md with missing new implementations documentation.
"""

readme_path = r"D:\AI-F\AI-f\README.md"

with open(readme_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Find the line after the "---" that follows the RBAC Frontend Implementation section
# That "---" is line 61 (1-indexed) based on debug output, index 60 (0-indexed)
# We want to insert AFTER that separator

target_marker = "#### 7. **RBAC Frontend Implementation** ✅"
found_idx = None

for i, line in enumerate(lines):
    if target_marker in line:
        print(f"Found RBAC section at index {i} (line {i+1})")
        # Look for the next "---" within next 10 lines
        for j in range(i, min(i+10, len(lines))):
            if lines[j].strip() == "---":
                found_idx = j
                print(f"Found separator '---' at index {j} (line {j+1})")
                break
        break

if found_idx is None:
    print("ERROR: Could not find insertion point")
    exit(1)

# New content to insert - note: using standard ASCII hyphens for now
# We'll preserve the ✅ emoji and other unicode from the file
new_content = """#### 8. **Operator Workflow & HITL Panel** ✅
- **File:** `ui/react-app/public/src/components/OperatorWorkflowPanel.tsx` (11,815 bytes)
- **Features:** Guided workflow stepper, recommended actions with priority scoring, retry/override/escalate controls, decision history logging
- **Integration:** Confidence-based action suggestions, spoof detection flags, manual review prompts

#### 9. **AI Assistant Chat Interface** ✅
- **File:** `ui/react-app/public/src/AIAssistant.tsx` (7,165 bytes)
- **Model:** GPT-powered conversational assistant via `/api/ai/chat`
- **Features:** Multi-turn dialogue, token-aware sessions, example question library, streaming-ready architecture

#### 10. **Enterprise Admin Console (React)** ✅
- **File:** `ui/react-app/public/src/pages/AdminPanel.tsx` (25,403 bytes)
- **Tabs:** Organizations, Policy Engine, Compliance, Explainable AI, Operator Workflow, Intelligence, Enrichment, Anti-Spoof, Identity Tokens, Settings
- **Widgets:** System health cards, policy toggle matrix, real-time risk metrics, API key generation, forensic chain verification

#### 11. **Subscription & Billing UI** ✅
- **File:** `ui/react-app/public/src/SubscriptionPlans.tsx` (4,871 bytes)
- **Providers:** Stripe Checkout integration with `@stripe/react-stripe-js`
- **Plans:** Free, Pro, Enterprise tiers with feature matrix display
- **Management:** Current subscription view, cancellation at period end, billing history

#### 12. **Developer Platform & API Playground** ✅
- **File:** `ui/react-app/public/src/pages/DeveloperPlatform.tsx` (5,077 bytes)
- **Features:** Interactive API code snippets (Python, JavaScript, cURL), one-click copy, test request runner
- **Webhooks:** UI for configuring biometric event notifications
- **SDKs:** Documented Python v2.4, Node.js v1.8, Go v0.9

#### 13. **Camera Management & RTSP Integration** ✅
- **File:** `ui/react-app/public/src/pages/CameraManagement.tsx` (5,770 bytes)
- **Features:** Camera CRUD, RTSP URL validation, per-camera status monitoring, location tagging
- **API:** `/api/orgs/{org_id}/cameras` with start/stop streaming controls

#### 14. **Compliance & Privacy Dashboard** ✅
- **File:** `ui/react-app/public/src/pages/Compliance.tsx` (6,833 bytes)
- **GDPR Actions:** Data export (portability), right to erasure, DSAR status checking
- **BIPA:** Consent vault viewer, ZKP proof verification, biometric data inventory

#### 15. **Enhanced Enrollment Workflow** ✅
- **File:** `ui/react-app/public/src/pages/Enroll.tsx` (6,218 bytes)
- **Multi-modal:** Face image upload (multiple recommended), drag-and-drop zone, preview gallery with delete
- **Consent Integration:** BIPA-compliant checkbox (requires active consent token)

#### 16. **Webcam Capture Component** ✅
- **File:** `ui/react-app/public/src/components/WebcamCapture.tsx` (73 lines)
- **Features:** Live webcam feed, capture to File, retake before submit, integrates with Recognize page

#### 17. **Authentication Pages** ✅
- **Login:** `ui/react-app/public/src/pages/Login.tsx` (3,648 bytes) — email/password + MFA, demo login mode, redirect to dashboard
- **Demo credentials flow:** Environment variable controlled (`REACT_APP_ENABLE_DEMO`)

#### 18. **Centralized Type System** ✅
- **Directory:** `ui/react-app/public/src/types/` (12 index re-exports, RecognitionResult in dedicated file: 22 lines)
- **Interfaces:** Person, Metrics, Alert, Consent, Log, Camera, Plan, Webhook, Plugin, Snackbar, RecognitionResult
- **Type Safety:** Full TypeScript strict mode; API response validation against schemas

---
"""

# Insert after the separator line
insert_position = found_idx + 1
lines.insert(insert_position, new_content)

# Write back
with open(readme_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"✓ Inserted new feature sections after line {found_idx + 1}")
print(f"✓ New total lines: {len(lines)}")
print("\nSummary of added sections:")
print("  - Operator Workflow & HITL Panel")
print("  - AI Assistant Chat Interface")
print("  - Enterprise Admin Console (React)")
print("  - Subscription & Billing UI")
print("  - Developer Platform & API Playground")
print("  - Camera Management & RTSP Integration")
print("  - Compliance & Privacy Dashboard")
print("  - Enhanced Enrollment Workflow")
print("  - Webcam Capture Component")
print("  - Authentication Pages")
print("  - Centralized Type System")
