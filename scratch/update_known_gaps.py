
import sys

file_path = r'd:\AI-F\AI-f\README.md'

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

new_section = """## ⚠️ Known Gaps & Partial Implementations

The following features have been claimed in documentation or code but are **not fully production-ready**:

| Feature | Implementation Status | Notes |
|---------|----------------------|-------|
| **Homomorphic Encryption (HE)** | ⚠️ Simulation only | `backend/app/models/homomorphic_encryption.py` contains `_setup_simulation_mode()` fallback; actual CKKS operations via TenSEAL are not deployed in production. |
| **Multi-Party Computation (MPC)** | ❌ Stubbed | `mpc_matching.py` has skeleton code (826 lines) with SPDZ placeholder; no actual secure multi-party computation functionality. |
| **Trusted Execution Environment (TEE)** | ⚠️ Mock/simulated | `enclave_mock.py` simulates Intel SGX/AMD SEV; no hardware-isolated enclave deployment. |
| **Biometric Template Protection** | ⚠️ Basic encryption only | No cancelable biometrics or fuzzy extractor; templates encrypted at rest but reversible with key. |
| **Hardware Security Module (HSM)** | ❌ Not integrated | Claims of "hardware-backed master key storage" refer only to cloud KMS; no PKCS#11 HSM support. |
| **Real-Time Threat Intelligence** | ❌ Missing | No threat intel feed integration (no `threat_intelligence.py` or external feed connectors). |
| **Automated Incident Response (SOAR)** | ⚠️ Manual only | Incident management UI exists but no automated playbook engine or SOAR connectors. |
| **Continuous Attestation** | ❌ One-time only | Attestation runs at startup; no continuous runtime integrity verification with remote attestation. |
| **Quantum-Resistant Cryptography** | ❌ Standard algorithms | No post-quantum schemes (CRYSTALS-Kyber, Dilithium); uses standard AES-256/RSA. |
| **Penetration Testing as a Service (PTaaS)** | ❌ Manual only | One-time pentest report exists; no automated continuous pentesting framework. |

**Impact:** These features should not be relied upon for regulated production deployments without completing implementation and independent validation.

**Partial/Stubbed Functionality:**
- **Alert types** — Only 3 of 5 claimed alert types implemented in backend (`alerts.py` returns demo data; BIAS_THRESHOLD_EXCEEDED and CONFIDENCE_DROPOUT are frontend placeholders only)
- **Threat Intelligence feeds** — EnrichmentPortalPanel lists providers but no live threat feed connectors
"""

# Replace lines 288 to 310 (1-indexed) -> 287 to 309 (0-indexed)
# Wait, let's verify the line content first to be sure where it starts and ends.
# I'll just look for the markers.

start_index = -1
end_index = -1

for i, line in enumerate(lines):
    if "Known Gaps & Partial Implementations" in line:
        start_index = i
    if start_index != -1 and "Configuration & Environment Variables" in line:
        end_index = i - 2 # Assuming --- is above it
        break

if start_index != -1 and end_index != -1:
    # Need to preserve the --- markers if they are there
    final_lines = lines[:start_index] + [new_section + "\n"] + lines[end_index+1:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(final_lines)
    print(f"Successfully updated section from line {start_index+1} to {end_index+1}")
else:
    print(f"Failed to find section markers: start={start_index}, end={end_index}")
