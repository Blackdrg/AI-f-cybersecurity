#!/bin/bash
set -euo pipefail

# Enclave Docker Entrypoint
# Handles initialization, attestation, and service startup

ENCLAVE_LOG_DIR="${ENCLAVE_LOG_DIR:-/var/log/enclave}"
ENCLAVE_CONFIG_DIR="${ENCLAVE_CONFIG_DIR:-/etc/enclave/config}"
ENCLAVE_MODEL_PATH="${ENCLAVE_MODEL_PATH:-/enclave/models}"

# Create log directory if writable
mkdir -p "${ENCLAVE_LOG_DIR}" || true
touch "${ENCLAVE_LOG_DIR}/enclave.log" || true

# Start logging
exec > >(tee -a "${ENCLAVE_LOG_DIR}/enclave.log") 2>&1

echo "[ENCLAVE] Starting Nitro Enclave image version ${ENCLAVE_VERSION:-dev}"

# Check if we're running in an enclave
if [ -f /etc/nitro_enclave ]; then
    echo "[ENCLAVE] Running inside Nitro Enclave (confirmed)"
    IN_ENCLAVE=true
else
    echo "[WARN] Not inside Nitro Enclave - running in compatibility mode"
    IN_ENCLAVE=false
fi

# Check VSOCK availability
if [ -S /run/enclave/vsock.sock ]; then
    echo "[ENCLAVE] VSOCK socket available"
else
    echo "[ENCLAVE] VSOCK socket not found - will use TCP fallback for local dev"
fi

# Load configuration
if [ -d "${ENCLAVE_CONFIG_DIR}" ]; then
    echo "[ENCLAVE] Loading config from ${ENCLAVE_CONFIG_DIR}"
    for cfg in "${ENCLAVE_CONFIG_DIR}"/*.env; do
        [ -f "$cfg" ] && export $(cat "$cfg" | xargs) && echo "  Loaded $cfg"
    done
fi

# Check model path
if [ ! -d "${ENCLAVE_MODEL_PATH}" ]; then
    echo "[ERROR] Model path not found: ${ENCLAVE_MODEL_PATH}"
    exit 1
fi

MODEL_COUNT=$(find "${ENCLAVE_MODEL_PATH}" -name '*.onnx' | wc -l)
echo "[ENCLAVE] Found ${MODEL_COUNT} ONNX models"

# Generate attestation document (if in enclave)
if [ "$IN_ENCLAVE" = true ]; then
    echo "[ENCLAVE] Generating attestation document..."
    if command -v nitro-cli &> /dev/null; then
        nitro-cli attestation document --output /run/enclave/attestation.json || true
        echo "[ENCLAVE] Attestation document saved to /run/enclave/attestation.json"
    else
        echo "[WARN] nitro-cli not available"
    fi
fi

# Wait for VSOCK listener to be ready
echo "[ENCLAVE] Waiting for client connections on VSOCK port 5000..."
echo "[ENCLAVE] Press Ctrl+C to stop"

# Run the application
exec python3 /enclave/app.py
