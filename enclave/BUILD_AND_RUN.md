# Building and Running the Enclave

## Prerequisites
- AWS Nitro CLI installed (https://docs.aws.amazon.com/enclaves/latest/user/nitro-cli-install.html)
- Docker installed
- Running in a Linux environment (you can use WSL2 on Windows)

## Steps

### 1. Build the EIF-optimized Docker image
From the `enclave` directory:
```bash
docker build -f Dockerfile.eif -t ai-f-enclave:eif .
```

### 2. Convert the Docker image to an EIF (Enclave Image File)
```bash
nitro-cli build-enclave \
  --docker-uri ai-f-enclave:eif \
  --output-file ai-f-enclave.eif \
  --memory-mib 512 \
  --cpu-count 2
```

**Or use the unified script:**
```bash
cd ../scripts
./build_deploy_enclave.sh build
```

### 3. Run the enclave
```bash
nitro-cli run-enclave --eif face-recognition-enclave.eif --cpu-count 2 --memory 512 --debug-mode
```
Note: Adjust `--cpu-count` and `--memory` as needed.

### 4. Verify the enclave is running
You can check the enclave's console output (if you used `--debug-mode`) or use:
```bash
nitro-cli describe-enclaves
```

### 5. To stop the enclave
```bash
nitro-cli terminate-enclave --enclave-id <enclave-id>
```
Get the enclave-id from `nitro-cli describe-enclaves`.

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

## Important Notes for Production
1. **Security**: In production, you must:
   - Encrypt the embeddings before sending them to the enclave (and decrypt inside the enclave).
   - Use AWS KMS to manage encryption keys and release them only after attestation.
   - Implement proper authentication for the enclave operations (e.g., only allow enrolled users to add embeddings).

2. **Attestation**: You should implement remote attestation to verify the enclave's identity before sending sensitive data.
   - The Nitro CLI provides an attestation document that can be verified.

3. **Data Persistence**: The known embeddings are stored in a file inside the enclave. In production, you would want to:
   - Encrypt this file at rest (using a key managed by KMS and released after attestation).
   - Consider using a secure database or secure storage solution.

4. **Model Security**: The ONNX model should be protected. Consider encrypting the model and decrypting it inside the enclave.

5. **Resource Constraints**: Enclaves have limited resources (CPU, memory). Optimize your model and code accordingly.

## Troubleshooting
- If you encounter issues building the EIF, ensure Docker is running and you have allocated enough resources.
- Check the nitro-cli logs for errors.
- Make sure the enclave is not blocked by any security groups or firewall rules (though vsock is local).

For more information, refer to the AWS Nitro Enclaves documentation:
https://docs.aws.amazon.com/enclaves/latest/user/what-is-enclaves.html