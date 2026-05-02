# enclave/app.py
import json
import socket
import struct
import numpy as np
import os
import sys

# In a real implementation, you would load your model and known embeddings here.
# For this example, we'll simulate the face matching by comparing embeddings.

# Path to the known embeddings files (inside the enclave)
KNOWN_FACE_EMBEDDINGS_PATH = "/known_face_embeddings.npy"
KNOWN_VOICE_EMBEDDINGS_PATH = "/known_voice_embeddings.npy"

def load_known_embeddings(path):
    """Load known embeddings from a file."""
    if os.path.exists(path):
        return np.load(path)
    else:
        # If the file doesn't exist, return an empty array for demonstration.
        # In production, you would have a secure way to provision this data.
        return np.array([])

def compute_similarity(embedding1, embedding2):
    """Compute cosine similarity between two embeddings."""
    # Ensure the embeddings are normalized
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return np.dot(embedding1, embedding2) / (norm1 * norm2)

def find_best_match(input_embedding, known_embeddings, threshold=0.6):
    """Find the best match for the input embedding among known embeddings."""
    if known_embeddings.size == 0:
        return None, 0.0

    # Compute similarities
    similarities = np.dot(known_embeddings, input_embedding) / (
        np.linalg.norm(known_embeddings, axis=1) * np.linalg.norm(input_embedding)
    )
    # Handle division by zero (if any embedding is zero vector)
    similarities = np.nan_to_num(similarities)

    best_idx = np.argmax(similarities)
    best_similarity = similarities[best_idx]

    if best_similarity >= threshold:
        return best_idx, best_similarity
    else:
        return None, best_similarity

def handle_client(conn):
    """Handle a single client connection over vsock."""
    while True:
        # Receive message length (4 bytes, big endian)
        raw_msglen = recvall(conn, 4)
        if not raw_msglen:
            break
        msglen = struct.unpack('>I', raw_msglen)[0]
        # Receive the message data
        data = recvall(conn, msglen)
        if not data:
            break

        # Parse the request (assuming JSON for simplicity)
        try:
            request = json.loads(data.decode('utf-8'))
        except json.JSONDecodeError:
            send_error(conn, "Invalid JSON")
            continue

        request_id = request.get('id')
        operation = request.get('operation')

        response = {}
        if operation == 'face_match':
            # Expecting an embedding to compare against known embeddings
            if 'embedding' not in request:
                send_error(conn, "Missing 'embedding' in request")
                continue

            input_embedding = np.array(request['embedding'], dtype=np.float32)
            known_embeddings = load_known_embeddings(KNOWN_FACE_EMBEDDINGS_PATH)

            best_idx, similarity = find_best_match(input_embedding, known_embeddings)

            if best_idx is not None:
                response = {
                    'id': request_id,
                    'result': {
                        'matched': True,
                        'index': int(best_idx),
                        'similarity': float(similarity)
                    },
                    'status': 'success'
                }
            else:
                response = {
                    'id': request_id,
                    'result': {
                        'matched': False,
                        'similarity': float(similarity)
                    },
                    'status': 'success'
                }
        elif operation == 'voice_match':
            # Expecting an embedding to compare against known embeddings
            if 'embedding' not in request:
                send_error(conn, "Missing 'embedding' in request")
                continue

            input_embedding = np.array(request['embedding'], dtype=np.float32)
            known_embeddings = load_known_embeddings(KNOWN_VOICE_EMBEDDINGS_PATH)

            best_idx, similarity = find_best_match(input_embedding, known_embeddings)

            if best_idx is not None:
                response = {
                    'id': request_id,
                    'result': {
                        'matched': True,
                        'index': int(best_idx),
                        'similarity': float(similarity)
                    },
                    'status': 'success'
                }
            else:
                response = {
                    'id': request_id,
                    'result': {
                        'matched': False,
                        'similarity': float(similarity)
                    },
                    'status': 'success'
                }
        elif operation == 'add_known_face_embedding':
            # This operation would be used to enroll a new person (securely)
            # In production, you would have strict authentication and authorization for this.
            if 'embedding' not in request or 'label' not in request:
                send_error(conn, "Missing 'embedding' or 'label' in request")
                continue

            new_embedding = np.array(request['embedding'], dtype=np.float32)
            label = request['label']

            # Load existing embeddings
            known_embeddings = load_known_embeddings(KNOWN_FACE_EMBEDDINGS_PATH)
            # For simplicity, we are just appending. In production, you would store this securely.
            if known_embeddings.size == 0:
                known_embeddings = new_embedding.reshape(1, -1)
            else:
                known_embeddings = np.vstack([known_embeddings, new_embedding])

            # Save the updated embeddings back to the file (in production, you would encrypt this)
            np.save(KNOWN_FACE_EMBEDDINGS_PATH, known_embeddings)

            response = {
                'id': request_id,
                'result': {
                    'message': f'Added embedding for {label}',
                    'total_embeddings': known_embeddings.shape[0]
                },
                'status': 'success'
            }
        elif operation == 'add_known_voice_embedding':
            # This operation would be used to enroll a new person (securely)
            # In production, you would have strict authentication and authorization for this.
            if 'embedding' not in request or 'label' not in request:
                send_error(conn, "Missing 'embedding' or 'label' in request")
                continue

            new_embedding = np.array(request['embedding'], dtype=np.float32)
            label = request['label']

            # Load existing embeddings
            known_embeddings = load_known_embeddings(KNOWN_VOICE_EMBEDDINGS_PATH)
            # For simplicity, we are just appending. In production, you would store this securely.
            if known_embeddings.size == 0:
                known_embeddings = new_embedding.reshape(1, -1)
            else:
                known_embeddings = np.vstack([known_embeddings, new_embedding])

            # Save the updated embeddings back to the file (in production, you would encrypt this)
            np.save(KNOWN_VOICE_EMBEDDINGS_PATH, known_embeddings)

            response = {
                'id': request_id,
                'result': {
                    'message': f'Added embedding for {label}',
                    'total_embeddings': known_embeddings.shape[0]
                },
                'status': 'success'
            }
        else:
            response = {
                'id': request_id,
                'error': 'Unknown operation',
                'status': 'error'
            }

        # Send response
        send_response(conn, request_id, response)

def send_response(conn, request_id, response):
    """Send a JSON response over the connection."""
    response_json = json.dumps(response)
    response_bytes = response_json.encode('utf-8')
    # Send length first
    conn.sendall(struct.pack('>I', len(response_bytes)))
    conn.sendall(response_bytes)

def send_error(conn, error_message):
    """Send an error response."""
    response = {
        'id': None,  # We don't have the request ID in case of JSON decode error, but we try to get it from the request if possible
        'error': error_message,
        'status': 'error'
    }
    # Try to get the request ID from the request if we have it (but we might not if JSON decode failed)
    # For simplicity, we'll set it to None and let the client handle it.
    send_response(conn, None, response)

def recvall(conn, n):
    """Helper function to receive n bytes or return None if EOF is reached."""
    data = b''
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def main():
    # VSOCK ports typically start from 3:2048, but we can choose a port above 1024
    port = 5000
    with socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM) as s:
        # Bind to the enclave's CID (which is always 3) and the port
        s.bind((socket.VMADDR_CID_ANY, port))
        s.listen()
        print(f"Enclave listening on vsock port {port}")
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                handle_client(conn)

if __name__ == '__main__':
    main()