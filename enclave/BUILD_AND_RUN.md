# Building and Running the Enclave

## Status: Production Ready ✓

AI-f enclave runs as a **real AWS Nitro Enclave** (no mocks in production). This document describes building, deploying, and operating the secure enclave.

## Prerequisites

- **AWS Nitro CLI** installed (https://docs.aws.amazon.com/enclaves/latest/user/nitro-cli-install.html)
- **Docker** installed
- **Linux environment** (Ubuntu 20.04+ or Amazon Linux 2); Windows via WSL2 OK
- **liboqs** (optional) for post-quantum crypto inside enclave
- **Minimum 2GB RAM, 2 vCPU** allocated to enclave

## Steps

### 1. Build the EIF Docker Image

From the `enclave` directory:

```bash
# Build optimized EIF image
docker build -f Dockerfile.eif -t face-recognition-enclave:2.2.1 .

# Verify image built
docker images | grep face-recognition-enclave
```

**What's included:**
- Minimal Python 3.11 runtime (Nitro base image)
- ML dependencies (ONNX Runtime, OpenCV, NumPy, SciPy, SpeechBrain)
- Pre-compiled ONNX models (optimized with ORT)
- Cached Python packages for fast startup
- Non-root `enclave` user (UID 1000)
- Health check endpoint (vsock port 5000)

### 2. Convert Docker Image to EIF

```bash
# Using nitro-cli directly
nitro-cli build-enclave \
  --docker-uri face-recognition-enclave:2.2.1 \
  --output-file face-recognition-enclave.eif \
  --memory-mib 2048 \
  --cpu-count 2

# Or use the automated script
cd ../scripts
./build_deploy_enclave.sh build
```

**Output:** `face-recognition-enclave.eif` (~650MB compressed)

### 3. Run the Enclave

```bash
# Basic run (debug mode)
nitro-cli run-enclave \
  --eif face-recognition-enclave.eif \
  --cpu-count 2 \
  --memory 2048 \
  --debug-mode

# Production (no debug)
nitro-cli run-enclave \
  --eif face-recognition-enclave.eif \
  --cpu-count 2 \
  --memory 2048 \
  --disable-debug-mode
```

**Enclave ID:** Captured from `nitro-cli describe-enclaves`

### 4. Verify Enclave Health

```bash
# Check enclave status
nitro-cli describe-enclaves

# View enclave logs
nitro-cli console --enclave-id <id>

# Health check via vsock (localhost for local dev)
# In real AWS: enclave CID = 16, localhost:5000 maps to vsock:5000
```

### 5. Stop the Enclave

```bash
# Terminate by ID
nitro-cli terminate-enclave --enclave-id <enclave-id>

# Or terminate all
nitro-cli terminate-enclave --all
```

## Enclave Communication
The enclave listens on VSOCK port 5000. Your application (running on the host) can communicate with the enclave using VSOCK.

Example Python code to connect to the enclave (to be run on the host):
```python
import socket
import struct
import json

def send_request(request):
    # Connect to the enclave via VSOCK
    # Note: The enclave's CID is usually 3, but you can get it from the nitro-cli output
    sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
    sock.connect((3, 5000))  # (CID, port)

    # Encode the request
    request_json = json.dumps(request)
    request_bytes = request_json.encode('utf-8')
    # Send length first
    sock.sendall(struct.pack('>I', len(request_bytes)))
    sock.sendall(request_bytes)

    # Receive response
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    response_bytes = recvall(sock, msglen)
    sock.close()
    return json.loads(response_bytes.decode('utf-8'))

def recvall(conn, n):
    data = b''
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

# Example request
request = {
    "id": 1,
    "operation": "face_match",
    "embedding": [0.1, 0.2, ...]  # Your embedding vector
}
response = send_request(request)
print(response)
```

## Enclave Communication

The enclave listens on **VSOCK port 5000**. Host applications communicate via vsock (port 5000).

### Python VSOCK Client

```python
import socket
import struct
import json
import base64

def send_enclave_request(enclave_cid: int, request: dict) -> dict:
    """
    Send request to enclave over vsock.
    Args:
        enclave_cid: VSOCK CID (usually 16 for enclave, 3 for VSOCK_ANY)
        request: JSON-serializable dict
    Returns:
        Response dict
    """
    sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect((enclave_cid, 5000))
    
    # Encode request
    request_json = json.dumps(request)
    request_bytes = request_json.encode('utf-8')
    
    # Send length-prefixed
    sock.sendall(struct.pack('>I', len(request_bytes)))
    sock.sendall(request_bytes)
    
    # Receive response
    raw_msglen = sock.recv(4)
    msglen = struct.unpack('>I', raw_msglen)[0]
    response_bytes = sock.recv(msglen)
    sock.close()
    
    return json.loads(response_bytes.decode('utf-8'))

# Example: Face match request
response = send_enclave_request(
    enclave_cid=3,
    request={
        "id": 1,
        "operation": "face_match",
        "embedding": [0.12, 0.34, ...]  # 512-d normalized embedding
    }
)
print(response)
```

### Production Transport Security

In production, host↔enclave communication also uses **AES-GCM session keys** after attestation:

```python
from app.models.attestation import EnclaveSession

# Establish secure session (attestation + key exchange)
session = EnclaveSession(enclave_id="prod-enclave-1")
if session.verify_attestation():
    session.establish_session()
    # Now use encrypted channel
    encrypted_req = session.encrypt_for_enclave(json.dumps(request).encode())
    # send over vsock...
```

---

## Attestation & Verification

**Remote Attestation** ensures you're talking to a genuine, untampered Nitro Enclave.

### Process

1. **Request attestation document** from enclave
   ```bash
   curl http://localhost:5000/attestation
   ```

2. **Verify** using AWS root certificate (built-in):
   ```python
   from app.models.attestation import NitroAttestationVerifier
   verifier = NitroAttestationVerifier()
   result = verifier.verify_attestation_document(attestation_doc)
   assert result["success"] is True
   ```

3. **Extract enclave public key** from document
4. **Establish encrypted session** using ECDH or RSA-OAEP with enclave's public key
5. **All traffic encrypted** with AES-256-GCM session key

### Automated Attestation

For host applications, use `EnclaveSession` (see code above) which handles:
- Attestation document fetching
- PCR validation (code integrity)
- Certificate chain validation (AWS root → signing)
- Session key establishment
- Continuous attestation (background thread)

**Configuration:**
```bash
export ENCLAVE_URL=http://localhost:5000           # Host:port
export ATTESTATION_WEBHOOK_URL=https://...        # Alerting
export ATTESTATION_CHECK_INTERVAL=300             # 5 minutes
```

---

## Important Notes for Production

### 1. Security Hardening

- **Always encrypt embeddings** before sending to enclave (use HE or session key)
- **Enforce attestation** before any sensitive operation
- **Use HSM** for storing enclave private keys (AWS CloudHSM)
- **Restrict vsock access**: Only host network namespace can connect
- **Enable debug mode OFF** in production

### 2. Data Persistence

Known embeddings are stored in `/run/enclave/known_faces.npy` (tmpfs). For persistence:

- **Option A**: Re-enroll at each restart (ephemeral, most secure)
- **Option B**: Encrypted backup to KMS-encrypted S3, restore on boot
- **Option C**: Use Nitro's local NVMe storage (encrypted at rest via LUKS)

### 3. Model Security

ONNX models are stored in `/enclave/models/` (read-only). Extra hardening:

```bash
# Encrypt models at rest
aws kms encrypt --key-id alias/ai-f-models --plaintext file://model.onnx --output-file model.onnx.enc
# Decrypt at enclave boot using KMS (after attestation)
```

### 4. Resource Constraints

| Resource | Default | Max |
|-----------|---------|-----|
| Memory | 2 GiB | 16 GiB (i3.metal) |
| vCPUs | 2 | 8 |
| Storage | tmpfs (ephemeral) | 8 GiB NVMe |
| Network | VSOCK only (no external) | - |

**Monitor:**
```bash
nitro-cli describe-enclaves --long
```

### 5. Logging

Enclave logs written to: `/var/log/enclave/enclave.log` (host mounted)

```bash
# View logs
sudo cat /var/log/enclave/enclave.log | grep -i error

# Real-time monitoring
sudo tail -f /var/log/enclave/enclave.log
```

---

## Advanced Configuration

### Custom Enclave Parameters

Environment variables (in `docker-entrypoint.sh`):

```bash
ENCLAVE_CONFIG_DIR=/etc/enclave/config    # Mount volume for config
ENCLAVE_MODEL_PATH=/enclave/models        # Mount models read-only
ENCLAVE_KNOWN_FACES_PATH=/run/enclave/faces.npy
ENCLAVE_KNOWN_VOICES_PATH=/run/enclave/voices.npy
ENCLAVE_LOG_DIR=/var/log/enclave          # Host- mounted logs
```

### Multi-Model Enclave

Add multiple models for hybrid recognition:

```python
# In enclave/app.py
MODEL_PATHS = {
    "face": "/enclave/models/face_recognition.onnx",
    "voice": "/enclave/models/voice_recognition.onnx",
    "fusion": "/enclave/models/fusion_engine.onnx"
}
```

---

## Troubleshooting

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| `EIF build fails: no space` | Disk full | Clean Docker: `docker system prune` |
| Enclave crashes on boot | Model file missing | Mount models dir to `/enclave/models` |
| VSOCK connection refused | Enclave not listening | Check `nitro-cli describe-enclaves` |
| Attestation fails | Invalid cert chain | Update root CA bundle |
| High latency (>100ms) | CPU throttling | Increase allocated vCPUs |
| OOM killed | Memory too low | Increase `--memory` to 4GiB+ |

**Debug commands:**
```bash
# Check enclave memory/CPU
nitro-cli describe-enclaves --long

# View enclave console
nitro-cli console --enclave-id <id>

# Check vsock listener
ss -x | grep 5000

# Validate EIF structure
nitro-cli enclave-info --eif face-recognition-enclave.eif
```

---

## CI/CD Pipeline

GitHub Actions example: (see `.github/workflows/enclave-build.yml`)

```yaml
name: Build Enclave EIF
on:
  push:
    branches: [main]
    paths: ['enclave/**']

jobs:
  build-eif:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t ai-f-enclave:$GITHUB_SHA -f enclave/Dockerfile.eif .
      - name: Build EIF
        run: |
          nitro-cli build-enclave \
            --docker-uri ai-f-enclave:$GITHUB_SHA \
            --output-file ai-f-enclave-$GITHUB_SHA.eif \
            --memory-mib 2048 --cpu-count 2
      - name: Upload EIF artifact
        uses: actions/upload-artifact@v3
        with:
          name: enclave-eif
          path: ai-f-enclave-*.eif
```

---

## References

- [AWS Nitro Enclaves User Guide](https://docs.aws.amazon.com/enclaves/latest/user/what-is-enclaves.html)
- [Nitro Cli Reference](https://github.com/aws/aws-nitro-enclaves-nitro-cli)
- [vsock(7) Linux man page](https://man7.org/linux/man-pages/man7/vsock.7.html)
- [TenSEAL CKKS for HE in Enclave](https://github.com/OpenMined/TenSEAL)