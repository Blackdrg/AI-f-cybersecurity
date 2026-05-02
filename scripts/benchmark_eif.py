#!/usr/bin/env python3
"""
TEE Enclave Performance Benchmark
Tests face/voice matching latency and throughput.
"""

import asyncio
import time
import socket
import json
import struct
import numpy as np
from statistics import mean, pstdev
import argparse

async def benchmark_enclave_operations(num_requests=1000, embedding_dim=512):
    """Benchmark enclave face_match operations."""
    latencies = []
    
    for i in range(num_requests):
        start = time.time()
        
        # Generate random embedding
        embedding = np.random.randn(embedding_dim).tolist()
        request = {
            "id": i,
            "operation": "face_match",
            "embedding": embedding
        }
        
        try:
            sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((3, 5000))
            
            req_json = json.dumps(request).encode()
            sock.sendall(struct.pack('>I', len(req_json)) + req_json)
            
            # Read response
            len_data = sock.recv(4)
            length = struct.unpack('>I', len_data)[0]
            _ = sock.recv(length)
            sock.close()
            
            latency = (time.time() - start) * 1000  # ms
            latencies.append(latency)
            
        except Exception as e:
            print(f"Request {i} failed: {e}")
            latencies.append(5000)  # Penalty for failure
    
    return latencies

async def main():
    latencies = await benchmark_enclave_operations(500)
    
    p50 = np.percentile(latencies, 50)
    p90 = np.percentile(latencies, 90)
    p99 = np.percentile(latencies, 99)
    throughput = len(latencies) / (max(latencies)/1000)  # req/s
    
    print("=== TEE Enclave Performance ===")
    print(f"P50: {p50:.1f}ms | P90: {p90:.1f}ms | P99: {p99:.1f}ms")
    print(f"Throughput: {throughput:.1f} req/s")
    print(f"Mean: {mean(latencies):.1f}ms | StdDev: {pstdev(latencies):.1f}ms")
    
    # Pass/Fail thresholds
    if p99 < 100 and mean(latencies) < 20:
        print("✅ PERFORMANCE PASS")
    else:
        print("❌ PERFORMANCE FAIL")

if __name__ == "__main__":
    asyncio.run(main())

