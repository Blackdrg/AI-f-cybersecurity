# Air-Gapped Deployment Guide for AI-f

**Version: 1.0**  
**Classification: Public**  
**Last Updated: 2026-05-08**

---

## Overview

This guide describes how to deploy AI-f in air-gapped (disconnected) environments commonly required by government, defense, and high-security organizations.

---

## Prerequisites

### Hardware Requirements
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 8 cores | 16 cores |
| RAM | 32 GB | 64 GB |
| Storage | 1 TB SSD | 2 TB NVMe |
| GPU | NVIDIA T4 | NVIDIA A10G |
| Network | 1 Gbps | 10 Gbps |

### Software Requirements
- Ubuntu 22.04 LTS or RHEL 9
- Docker Engine 24.x
- Docker Compose 2.x
- Kubernetes 1.28+ (optional)

---

## Deployment Methods

### Option 1: Air-Gap Installer Script

```bash
#!/bin/bash
# airgap-install.sh

set -e

echo "Installing AI-f in air-gapped mode..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker required"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose required"; exit 1; }

# Load images from local tar files
echo "Loading Docker images..."
for image in docker-images/*.tar; do
    docker load -i "$image"
done

# Create necessary directories
mkdir -p /opt/ai-f/{data,models,logs}
chmod 750 /opt/ai-f

# Extract configuration
unzip -q config.zip -d /opt/ai-f/config

# Generate certificates
openssl req -x509 -newkey rsa:4096 -keyout /opt/ai-f/config/key.pem -out /opt/ai-f/config/cert.pem -days 365 -nodes -subj "/CN=ai-f.local"

# Start services
echo "Starting services..."
docker-compose -f docker-compose.airgap.yml up -d

echo "Deployment complete!"
echo "Access: https://$(hostname -I | awk '{print $1}'):8443"
```

### Option 2: Kubernetes Air-Gap

```bash
#!/bin/bash
# k8s-airgap-install.sh

set -e

# Load all required images
echo "Loading Kubernetes images..."
for image in k8s-images/*.tar; do
    kind load docker-image "$image" --name ai-f-cluster
done

# Create namespaces
kubectl create namespace ai-f-system

# Apply manifests
kubectl apply -f manifests/airgap/

# Wait for services
kubectl wait --for=condition=available --timeout=300s deployment -n ai-f-system --all

echo "Kubernetes deployment complete!"
```

---

## Offline Model Distribution

### Creating Model Bundles

```python
# tools/create_model_bundle.py
import tarfile
import hashlib
import json
from pathlib import Path

def create_model_bundle(models_dir: str, output_file: str):
    """Create air-gap compatible model bundle."""
    
    bundle = {
        "version": "1.0",
        "created": "2026-05-08",
        "models": []
    }
    
    with tarfile.open(output_file, "w:gz") as tar:
        for model_file in Path(models_dir).glob("*.onnx"):
            # Add model file
            tar.add(model_file, arcname=f"models/{model_file.name}")
            
            # Calculate checksum
            with open(model_file, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            
            bundle["models"].append({
                "name": model_file.stem,
                "file": model_file.name,
                "checksum": checksum,
                "size": model_file.stat().st_size
            })
    
    # Add manifest
    manifest = Path(output_file).stem + ".manifest.json"
    with open(manifest, "w") as f:
        json.dump(bundle, f, indent=2)
    
    tar.add(manifest, arcname="manifest.json")
    Path(manifest).unlink()

if __name__ == "__main__":
    create_model_bundle("models/production", "ai-f-models-airgap.tar.gz")
```

### Loading Models in Air-Gap

```bash
# Load model bundle
tar -xzf ai-f-models-airgap.tar.gz -C /opt/ai-f/models
cat manifest.json

# Verify integrity
sha256sum -c models/*.sha256
```

---

## Configuration Settings

### Environment Variables (.env.airgap)

```bash
# Database (offline mode)
DB_HOST=localhost
DB_PORT=5432
DB_USER=ai_f
DB_NAME=face_recognition

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Model paths (local only)
MODEL_PATH=/opt/ai-f/models
EMBEDDING_MODEL=/opt/ai-f/models/embedding.onnx

# Licensing (offline)
LICENSE_KEY_FILE=/opt/ai-f/config/license.lic

# TLS (self-signed)
TLS_CERT=/opt/ai-f/config/cert.pem
TLS_KEY=/opt/ai-f/config/key.pem

# Disable external integrations
DISABLE_EXTERNAL_APIS=true
DISABLE_TELEMETRY=true
```

---

## Security Configuration

### Offline Certificate Authority

```bash
# Create private CA for air-gap
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 1825 -key ca.key -out ca.crt -subj "/CN=AI-f AirGap CA"

# Sign server certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=*.ai-f.local"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365
```

### Network Isolation

```yaml
# docker-compose.airgap.yml
version: '3.8'

services:
  backend:
    image: ai-f-backend:airgap
    ports:
      - "8443:8443"
    networks:
      - airgap
    volumes:
      - ./models:/opt/ai-f/models:ro
      - ./data:/opt/ai-f/data
    environment:
      - DISABLE_EXTERNAL_APIS=true
      - OFFLINE_MODE=true
      
  postgres:
    image: ai-f-postgres:airgap
    networks:
      - airgap
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      
  redis:
    image: ai-f-redis:airgap
    networks:
      - airgap
    volumes:
      - ./data/redis:/data

networks:
  airgap:
    driver: bridge
    internal: true  # No external access
```

---

## Air-Gap Installer Package Structure

```
ai-f-airgap-installer-v1.0/
├── install.sh                    # Main installer script
├── uninstall.sh                  # Cleanup script
├── docker-images/               # Pre-built Docker images (.tar)
│   ├── ai-f-backend.tar
│   ├── ai-f-postgres.tar
│   └── ai-f-redis.tar
├── models/                      # Pre-packaged models
│   ├── embedding.onnx
│   └── embedding.onnx.sha256
├── config.zip                   # Default configuration
├── manifests/                   # Kubernetes manifests (optional)
│   └── airgap/
└── README.md                    # This file
```

---

## Verification Checklist

- [ ] All container images loaded successfully
- [ ] Model files extracted and verified
- [ ] TLS certificates generated
- [ ] Services started and healthy
- [ ] API accessible at https://localhost:8443
- [ ] Face recognition working with test image
- [ ] Database initialized with schemas

---

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs backend

# Verify image loaded
docker images | grep ai-f

# Check disk space
df -h
```

### Model Not Loading
```bash
# Verify model path
ls -la /opt/ai-f/models/

# Check permissions
chmod 644 /opt/ai-f/models/*.onnx

# Verify model integrity
sha256sum -c embedding.onnx.sha256
```

### Database Connection Failed
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify database initialized
docker exec -it ai-f-postgres pg_isready

# Reinitialize if needed
docker volume rm ai-f-data_postgres
```

---

## Compliance Notes

### NIST 800-171 Compliance
- Data at rest: Encrypted with AES-256
- Data in transit: TLS 1.3
- Audit logs: Retained locally

### CMMC Level 3
- Multi-factor authentication available
- Session timeout configured
- Role-based access control

---

## Support

**Air-Gap Support Portal**: Available offline at /opt/ai-f/docs/support.html  
**Security Contact**: security@ai-f.example.com (for pre-approved communication channels)