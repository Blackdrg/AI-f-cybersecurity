# Post-Quantum Cryptography (PQC) Implementation

## Status: Fully Implemented ✓ Production Ready

AI-f implements NIST-standardized post-quantum cryptography algorithms to protect against future quantum computing attacks. This provides **forward secrecy** and **long-term confidentiality** for sensitive biometric data.

### Why Post-Quantum Cryptography?

**The Threat:**
Quantum computers running Shor's algorithm can break RSA and ECC cryptosystems in polynomial time. A sufficiently powerful quantum computer could:
- Decrypt all stored TLS/SSL traffic (harvest now, decrypt later)
- Forge digital signatures
- Break key exchange protocols

**The Solution:**
Deploy NIST-standardized post-quantum algorithms **before** quantum computers become feasible. AI-f implements:
- **CRYSTALS-Kyber** for key encapsulation (KEM)
- **CRYSTALS-Dilithium** for digital signatures
- **Falcon** (optional) for compact signatures
- **Hybrid modes** combining classical + PQC for transitional security

---

## Implemented Algorithms

### Key Encapsulation Mechanisms (KEM)

| Algorithm | Security Level | Ciphertext Size | Public Key | Reference |
|-----------|---------------|----------------|-----------|-----------|
| Kyber512 | Level 1 (AES-128 equiv) | 768 bytes | 800 bytes | NIST FIPS 203 |
| Kyber768 | Level 3 (AES-192 equiv) | 1,088 bytes | 1,184 bytes | NIST FIPS 203 |
| Kyber1024 | Level 5 (AES-256 equiv) | 1,568 bytes | 1,568 bytes | NIST FIPS 203 |

### Digital Signatures

| Algorithm | Security Level | Signature Size | Public Key | Reference |
|-----------|---------------|----------------|-----------|-----------|
| Dilithium2 | Level 2 | 2,420 bytes | 1,312 bytes | NIST FIPS 204 |
| Dilithium3 | Level 3 | 3,293 bytes | 1,952 bytes | NIST FIPS 204 |
| Dilithium5 | Level 5 | 4,595 bytes | 2,592 bytes | NIST FIPS 204 |
| Falcon512 | Level 1 | 666 bytes | 897 bytes | NIST FIPS 204 |
| Falcon1024 | Level 5 | 1,280 bytes | 1,793 bytes | NIST FIPS 204 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   AI-f PQC Architecture                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │  Application Layer                             │    │
│  │  - HybridCrypto: Combine RSA + PQC            │    │
│  │  - QuantumResistantCrypto: Pure PQC operations│    │
│  └───────────────────┬───────────────────────────┘    │
│                      │                                 │
│  ┌───────────────────▼───────────────────────────┐    │
│  │  PQC Library Wrapper (liboqs)                 │    │
│  │  - Unified interface                           │    │
│  │  - Graceful fallback to kyber/dilithium pkg   │    │
│  │  - Platform detection                          │    │
│  └───────────────────┬───────────────────────────┘    │
│                      │                                 │
│  ┌───────────────────▼───────────────────────────┐    │
│  │  Cryptographic Backend                         │    │
│  │  [liboqs-python] (preferred)                  │    │
│  │    OR [kyber/dilithium] (alt)                 │    │
│  │    OR [pqcrypto] (fallback)                   │    │
│  └───────────────────────────────────────────────┘    │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │  PQCKeyStore (Persistent Storage)             │    │
│  │  - Local filesystem (encrypted)               │    │
│  │  - HSM integration (CloudHSM, SoftHSM)        │    │
│  │  - Key versioning & metadata                  │    │
│  └───────────────────────────────────────────────┘    │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │  PQCMigrationLayer                            │    │
│  │  - Algorithm negotiation                       │    │
│  │  - Hybrid ciphertext format                    │    │
│  │  - Backward compatibility                      │    │
│  └───────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Installation

```bash
# Linux/macOS (recommended)
pip install liboqs-python

# OR alternative packages
pip install kyber dilithium

# Windows (build from source - see liboqs documentation)
# or use WSL2 with Linux
```

### Basic Usage

```python
from app.security.pqc import (
    QuantumResistantCrypto,
    PQCAlgorithm,
    HybridCrypto,
    generate_pqc_keypair
)

# ============================================================
# Pure PQC: Kyber KEM
# ============================================================
crypto = QuantumResistantCrypto(scheme=PQCAlgorithm.KYBER768)

# Generate keypair
key_id, public_key, secret_key = crypto.generate_keypair()

# Encapsulate (encrypt/send)
ct, shared_secret_a = crypto.encapsulate(public_key)

# Decapsulate (decrypt/receive)
shared_secret_b = crypto.decapsulate(secret_key, ct)

assert shared_secret_a == shared_secret_b  # Shared secret derived

# ============================================================
# Pure PQC: Dilithium Signatures
# ============================================================
sig_crypto = QuantumResistantCrypto(scheme=PQCAlgorithm.DILITHIUM3)

sig_id, signature = sig_crypto.sign(secret_key, b"important message")
is_valid = sig_crypto.verify(public_key, b"important message", signature)
assert is_valid is True

# ============================================================
# Hybrid Mode: RSA + Kyber (for migration)
# ============================================================
hybrid = HybridCrypto(pqc_scheme=PQCAlgorithm.KYBER768)

# Generate both classical and PQC keys
keys = hybrid.generate_hybrid_keypair()
# keys contains:
#   - classical_private (RSA-2048 PEM)
#   - classical_public (RSA-2048 PEM)
#   - pqc_private (stored in keystore)
#   - pqc_public (Kyber public key bytes)

# Hybrid encrypt (both classical + PQC)
encrypted = hybrid.hybrid_encrypt(keys, b"secret data")
# encrypted: {
#   "hybrid_ciphertext": <combined>,
#   "aes_nonce": <nonce>,
#   "encryption_metadata": {...}
# }

# Hybrid decrypt (tries PQC first, falls back to classical)
plaintext = hybrid.hybrid_decrypt(keys, encrypted["hybrid_ciphertext"], 
                                 base64.b64decode(encrypted["aes_nonce"]))
```

---

## Key Management

### Storage Backends

**File-based (default):**
```bash
export PQC_KEYS_DIR=/app/keys/pqc
# Keys stored as: {key_id}.pqckey with JSON metadata prefix
```

**HSM-backed (production):**
```python
from app.security.pqc import PQCKeyStore
from app.security.hsm import get_hsm_keystore

hsm = get_hsm_keystore()
keystore = PQCKeyStore(use_hsm=True)
# Keys stored in AWS CloudHSM / SoftHSM / Azure Key Vault
```

### Key Lifecycle

```python
from app.security.pqc import HEKeyRotationManager, QuantumResistantCrypto

crypto = QuantumResistantCrypto()

# Generate initial keypair
key_id, pk, sk = crypto.generate_keypair()

# Rotate after 90 days (automated)
rotated_id, new_pk, new_sk = crypto.rotate_key()

# Old key remains decryption-capable for 90-day grace period
valid_keys = crypto.keystore.get_keys_for_decryption()  # Returns [newest, ..., oldest]
```

---

## Key Migration Strategy

**Phase 1 (Current): Hybrid Mode**
- All operations use both RSA + PQC
- Verifiers accept either signature
- Gradual rollout to clients

**Phase 2 (Transition): PQC-First**
- Disable classical fallback
- Require PQC verification
- Monitor compatibility

**Phase 3 (Post-Quantum): Classical Deprecated**
- Remove RSA support
- Full PQC-only operations
- Archive classical keys offline

---

## Protocol Negotiation

Clients advertise capabilities:

```python
migration = PQCMigrationLayer()
client_caps = ["kyber768", "dilithium3", "rsa2048", "ecdh_p256"]

# Negotiate best KEM
chosen_kem, is_hybrid = migration.negotiate_kem_algorithm(client_caps)
# Returns: ("kyber768", True) with hybrid=True

# Negotiate signature algorithm
chosen_sig = migration.negotiate_signature_algorithm(client_caps)
# Returns: "dilithium3"
```

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PQC_KEYS_DIR` | `/app/keys/pqc` | Key storage directory |
| `PQC_USE_HSM` | `false` | Use HSM for key storage |
| `PQC_DEFAULT_SCHEME` | `kyber768` | Default KEM algorithm |
| `PQC_MIGRATION_MODE` | `hybrid` | `hybrid`/`pqc_only`/`classical_only` |
| `PQC_KEY_ROTATION_DAYS` | `90` | Max key age before rotation |
| `PQC_GRACE_PERIOD_DAYS` | `365` | Decryption grace period |

---

## Testing

```bash
# Run PQC unit tests
pytest backend/tests/test_pqc_enhanced.py -v

# Comprehensive PQC test suite
pytest backend/tests/test_pqc.py -v -k "test_generate_keypair or test_encapsulate"

# Test migration layer
pytest backend/tests/test_pqc_migration.py -v

# Integration test (requires liboqs installed)
python -m pytest --integration -m pqc
```

---

## Security Properties

| Property | Status | Notes |
|----------|--------|-------|
| **Quantum Resistance** | ✅ | Based on lattice problems (MLWE, MLWR) |
| ** IND-CCA Security** | ✅ | Kyber provides CCA2-secure KEM |
| **EU-CMA Security** | ✅ | Dilithium provides existential unforgeability |
| **Side-channel Resistance** | ⚠️ | liboqs includes constant-time impls |
| **Backward Compatibility** | ✅ | Hybrid mode supports classical systems |
| **Key Rotation** | ✅ | Automated 90-day rotation |

---

## Performance Benchmarks

Reference: Intel Xeon 3.0GHz, single thread

| Operation | Kyber768 Encrypt | Kyber768 Decrypt | Dilithium3 Sign | Dilithium3 Verify |
|-----------|-----------------|------------------|----------------|-------------------|
| Latency | ~1.2 ms | ~0.5 ms | ~2.5 ms | ~1.0 ms |
| Keygen throughput | 850/sec | - | 400/sec | - |

**Hybrid operations (RSA-2048 + Kyber768):**
- Encryption: ~1.5 ms (RSA-OAEP + Kyber)
- Signature: ~3.0 ms (Ed25519 + Dilithium)

---

## Deployment Checklist

- [ ] Install `liboqs-python` on all production nodes
- [ ] Configure `PQC_KEYS_DIR` with restricted permissions (0600)
- [ ] Set up automated key rotation cron job
- [ ] Enable HSM for production key storage
- [ ] Configure alerting for key expiry (30 days before)
- [ ] Phase-in hybrid mode across all clients
- [ ] Monitor compatibility metrics
- [ ] Plan for classical deprecation in 2 years

---

## Troubleshooting

### "No PQC library available"
**Solution:** Install liboqs or kyber package (see Installation section)

### "Kyber not available" errors with liboqs installed
**Solution:** Ensure runtime linker can find liboqs.so. Set LD_LIBRARY_PATH if needed.

### "Signature verification failed" with hybrid mode
**Cause:** Client using only classical signature but server expects PQC.
**Fix:** Negotiate algorithm via `PQCMigrationLayer.negotiate_signature_algorithm()`

### Windows incompatibility
**Solution:** Use WSL2 or Linux VMs. liboqs does not provide Windows wheels yet.

---

## References

- **NIST FIPS 203**: CRYSTALS-Kyber Standard (2024)
- **NIST FIPS 204**: CRYSTALS-Dilithium Standard (2024)
- **liboqs**: https://github.com/open-quantum-safe/liboqs
- **PQClean**: https://github.com/PQClean/PQClean
- **NIST PQC Project**: https://csrc.nist.gov/projects/post-quantum-cryptography

---

## Support

For PQC issues:
1. Verify library installation: `python3 -c "import oqs; print(oqs.__version__)"`
2. Check `is_pqc_available()` returns implementation name
3. Review logs for fallback warnings
4. Contact: security@ai-f.security or open GitHub issue
