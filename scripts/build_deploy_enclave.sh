#!/bin/bash
# EIF Build and Deployment Script for AWS Nitro Enclaves
# Usage: ./scripts/build_deploy_enclave.sh [build|run|test]

set -e

ENCLAVE_DIR=../enclave
EIF=enclave.eif
NITRO_CLI=/opt/nitro/cli/v1/nitro-cli

echo "=== AWS Nitro Enclaves TEE Build & Deploy ==="

case $1 in
  build)
    echo "1. Building Docker image..."
    cd $ENCLAVE_DIR
    docker build -t ai-f-enclave:latest .
    
    echo "2. Creating EIF..."
    $NITRO_CLI build-enclave \
      --docker-uri ai-f-enclave:latest \
      --output-file $EIF \
      --memory 512 \
      --cpu-count 2
    
    echo "EIF built: $EIF"
    ;;
  run)
    echo "3. Running enclave..."
    $NITRO_CLI run-enclave \
      --eif-path $EIF \
      --cpu-count 2 \
      --memory 512M \
      --enclave-cid 3
    
    echo "Enclave running (CID=3). Check: nitro-cli describe-enclaves"
    ;;
  test)
    echo "4. Testing enclave connection..."
    python3 -c "
import socket, json, struct
s = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
try:
    s.connect((3, 5000))
    req = {'id':1, 'operation':'get_enclave_info'}
    req_json = json.dumps(req).encode()
    s.sendall(struct.pack('>I', len(req_json)) + req_json)
    len_data = s.recv(4)
    length = struct.unpack('>I', len_data)[0]
    resp = json.loads(s.recv(length).decode())
    print('✅ Enclave OK:', resp)
except Exception as e:
    print('❌ Enclave test failed:', e)
finally:
    s.close()
"
    ;;
  *)
    echo "Usage: $0 {build|run|test}"
    exit 1
    ;;
esac

echo "Next: docker-compose up (with enclave service) for full deployment"

