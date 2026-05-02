# Mock Enclave Service for Development
# This service mimics the behavior of the TEE enclave for face matching.
# In production, this would be replaced by the actual enclave running via AWS Nitro Enclaves
# and communication would happen over VSOCK.

import socket
import json
import numpy as np
import os
import threading
from typing import Optional, Tuple

# Configuration
HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 5000         # Port to listen on (non-privileged ports are > 1023)
KNOWN_EMBEDDINGS_FILE = 'known_embeddings.npy'

class MockEnclaveService:
    def __init__(self):
        self.known_embeddings = self._load_known_embeddings()
        self.lock = threading.Lock()  # To protect access to known_embeddings
    
    def _load_known_embeddings(self) -> np.ndarray:
        """Load known embeddings from file."""
        if os.path.exists(KNOWN_EMBEDDINGS_FILE):
            return np.load(KNOWN_EMBEDDINGS_FILE)
        else:
            # Return an empty array with shape (0, d) where d is the embedding dimension.
            # We don't know the dimension yet, so we'll return a 0x0 array and set the dimension on first load.
            return np.array([]).reshape(0, 0)
    
    def _save_known_embeddings(self):
        """Save known embeddings to file."""
        np.save(KNOWN_EMBEDDINGS_FILE, self.known_embeddings)
    
    def _compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        # Ensure the embeddings are normalized
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return np.dot(emb1, emb2) / (norm1 * norm2)
    
    def _find_best_match(self, input_embedding: np.ndarray, threshold: float = 0.6) -> Tuple[Optional[int], float]:
        """Find the best match for the input embedding among known embeddings.
        
        Returns:
            Tuple of (index, similarity) if match found above threshold, else (None, similarity)
        """
        if self.known_embeddings.size == 0:
            return None, 0.0
        
        # Ensure input_embedding is 2D for dot product
        if input_embedding.ndim == 1:
            input_embedding = input_embedding.reshape(1, -1)
        
        # Compute similarities
        # We'll compute dot product and then divide by norms
        dot_products = np.dot(self.known_embeddings, input_embedding.T).flatten()
        norms = np.linalg.norm(self.known_embeddings, axis=1) * np.linalg.norm(input_embedding)
        # Avoid division by zero
        norms = np.where(norms == 0, 1e-10, norms)
        similarities = dot_products / norms
        
        best_idx = np.argmax(similarities)
        best_similarity = similarities[best_idx]
        
        if best_similarity >= threshold:
            return int(best_idx), float(best_similarity)
        else:
            return None, float(best_similarity)
    
    def handle_client(self, conn: socket.socket, addr):
        """Handle a client connection."""
        print(f"Connected by {addr}")
        try:
            while True:
                # Receive message length (4 bytes, big endian)
                raw_msglen = self._recvall(conn, 4)
                if not raw_msglen:
                    break
                msglen = struct.unpack('>I', raw_msglen)[0]
                # Receive the message data
                data = self._recvall(conn, msglen)
                if not data:
                    break

                # Parse the request (assuming JSON for simplicity)
                try:
                    request = json.loads(data.decode('utf-8'))
                except json.JSONDecodeError:
                    self._send_error(conn, "Invalid JSON")
                    continue

                request_id = request.get('id')
                operation = request.get('operation')

                response = {}
                if operation == 'face_match':
                    # Expecting an embedding to compare against known embeddings
                    if 'embedding' not in request:
                        self._send_error(conn, "Missing 'embedding' in request")
                        continue

                    input_embedding = np.array(request['embedding'], dtype=np.float32)
                    # Use a threshold of 0.6 for matching (can be made configurable)
                    best_idx, similarity = self._find_best_match(input_embedding, threshold=0.6)

                    if best_idx is not None:
                        response = {
                            'id': request_id,
                            'result': {
                                'matched': True,
                                'index': best_idx,
                                'similarity': similarity
                            },
                            'status': 'success'
                        }
                    else:
                        response = {
                            'id': request_id,
                            'result': {
                                'matched': False,
                                'similarity': similarity
                            },
                            'status': 'success'
                        }
                elif operation == 'add_known_embedding':
                    # This operation would be used to enroll a new person (securely)
                    # In production, you would have strict authentication and authorization for this.
                    if 'embedding' not in request or 'label' not in request:
                        self._send_error(conn, "Missing 'embedding' or 'label' in request")
                        continue

                    new_embedding = np.array(request['embedding'], dtype=np.float32)
                    label = request['label']

                    # Load existing embeddings (with lock to prevent race conditions)
                    with self.lock:
                        # For simplicity, we are just appending. In production, you would store this securely.
                        if self.known_embeddings.size == 0:
                            # We need to reshape to 2D
                            self.known_embeddings = new_embedding.reshape(1, -1)
                        else:
                            self.known_embeddings = np.vstack([self.known_embeddings, new_embedding])

                        # Save the updated embeddings back to the file
                        self._save_known_embeddings()

                    response = {
                        'id': request_id,
                        'result': {
                            'message': f'Added embedding for {label}',
                            'total_embeddings': self.known_embeddings.shape[0]
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
                self._send_response(conn, request_id, response)
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            conn.close()
            print(f"Connection closed by {addr}")

    def _send_response(self, conn: socket.socket, request_id: Optional[int], response: dict):
        """Send a JSON response over the connection."""
        response_json = json.dumps(response)
        response_bytes = response_json.encode('utf-8')
        # Send length first
        conn.sendall(struct.pack('>I', len(response_bytes)))
        conn.sendall(response_bytes)

    def _send_error(self, conn: socket.socket, error_message: str):
        """Send an error response."""
        response = {
            'id': None,  # We don't have the request ID in case of JSON decode error
            'error': error_message,
            'status': 'error'
        }
        self._send_response(conn, None, response)

    def _recvall(self, conn: socket.socket, n: int) -> Optional[bytes]:
        """Helper function to receive n bytes or return None if EOF is reached."""
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def start(self):
        """Start the mock enclave service."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            print(f"Mock enclave service listening on {HOST}:{PORT}")
            while True:
                conn, addr = s.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()

if __name__ == '__main__':
    import struct
    service = MockEnclaveService()
    service.start()