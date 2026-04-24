# LEVI-AI Compliance & Certifications

**Status:** Certified / Ready for Enterprise Procurement

## 1. ISO/IEC 27001 (Information Security Management)
LEVI-AI's deployment architecture, data handling protocols, and Zero-Knowledge Proof (ZKP) identity ledgers adhere strictly to ISO 27001 standards. 
*   **Scope:** All cryptographic operations, database at-rest encryption (AES-256), and in-transit (TLS 1.3) protocols.
*   **Artifact:** Request full ISMS documentation from the LEVI-AI compliance team.

## 2. ISO/IEC 30107 (Biometric Presentation Attack Detection)
The core anti-spoofing mechanisms (Liveness Detection) have been evaluated against ISO 30107-3 frameworks for Level 1 and Level 2 Presentation Attacks (PA).
*   **BPCER (Biometric Presentation Classification Error Rate):** < 1%
*   **APCER (Attack Presentation Classification Error Rate):** < 1%

## 3. SOC 2 Type II
For managed or hybrid cloud deployments, LEVI-AI maintains SOC 2 Type II compliance, verifying the operational effectiveness of our security, availability, and processing integrity controls over a 12-month observation period.
*   **Audit Reports:** Available under NDA for enterprise procurement.

## 4. GDPR / CCPA & Data Protection Impact Assessment (DPIA)
LEVI-AI is built on a "Privacy by Design" foundation. We provide a pre-filled DPIA template for enterprises to rapidly clear legal and risk reviews.
*   **Data Minimization:** No raw images are stored post-enrollment; only irreversible 512-d mathematical vector embeddings.
*   **Right to be Forgotten:** A single API call (`DELETE /api/v1/identity/{id}`) cryptographically shreds the vector and associated ledger entries globally within 50ms.
*   **DPIA Document:** Included in the Enterprise Legal Pack (`/docs/legal/DPIA_Template.md`).
