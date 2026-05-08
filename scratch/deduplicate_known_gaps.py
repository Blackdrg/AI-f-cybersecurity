
import sys

file_path = r'd:\AI-F\AI-f\README.md'

with open(file_path, 'rb') as f:
    content = f.read()

# The section markers
section_start = b"## \xf0\x9f\x9a\xa0 Known Gaps & Partial Implementations" 
# Wait, I'll use a simpler ASCII marker
marker = b"Known Gaps & Partial Implementations"

# Find all occurrences of the marker
indices = []
pos = content.find(marker)
while pos != -1:
    indices.append(pos)
    pos = content.find(marker, pos + 1)

print(f"Found marker at indices: {indices}")

if len(indices) >= 1:
    # We want to keep only the first occurrence of the section
    # and find where the duplication ends.
    # The next section after the gaps is "Configuration & Environment Variables"
    config_marker = b"Configuration & Environment Variables"
    config_pos = content.find(config_marker)
    
    if config_pos != -1:
        # Everything between line 288 (approx) and config_pos should be the CLEAN version of the section.
        # But wait, the user's edit added it at the end of the previous one.
        
        # Let's find the FIRST start of the section
        first_start = content.rfind(b"##", 0, indices[0])
        
        # The clean text we want
        clean_section = """## ⚠️ Known Gaps & Partial Implementations

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

---

"""
        # Replace everything from first_start up to config_pos
        # But wait, config_pos might be in the middle of a header
        config_header_start = content.rfind(b"##", 0, config_pos)
        
        new_content = content[:first_start] + clean_section.encode('utf-8') + content[config_header_start:]
        
        with open(file_path, 'wb') as f:
            f.write(new_content)
        print("Successfully deduplicated and cleaned up Known Gaps section.")
    else:
        print("Could not find Configuration header marker.")
else:
    print("Could not find Known Gaps marker.")
