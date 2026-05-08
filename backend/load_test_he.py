"""Load test Homomorphic Encryption (TenSEAL CKKS) operations.

Tests encryption, multiplication, and decryption under concurrency.

Usage:
    python -m backend.load_test_he --workers 10 --iterations 100
"""
import argparse
import time
import threading
import numpy as np
import logging

try:
    import tenseal as ts
    TENSEAL_AVAILABLE = True
except ImportError:
    TENSEAL_AVAILABLE = False

logger = logging.getLogger(__name__)

def create_context():
    context = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=8192,
        coeff_mod_bit_sizes=[60, 40, 40, 60]
    )
    context.global_scale = 2 ** 40
    context.generate_galois_keys()
    context.generate_relin_keys()
    return context

def worker(worker_id, iterations, results):
    ctx = create_context()
    vec_size = 1024
    a = np.random.rand(vec_size).astype(np.float64)
    b = np.random.rand(vec_size).astype(np.float64)
    times = []
    for i in range(iterations):
        start = time.perf_counter()
        # Encrypt a and b
        enc_a = ts.ckks_vector(ctx, a)
        enc_b = ts.ckks_vector(ctx, b)
        # Multiply (element-wise) and rescale
        enc_prod = enc_a * enc_b
        # Decrypt
        prod = enc_prod.decrypt()
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    results[worker_id] = times

def main():
    parser = argparse.ArgumentParser(description="HE load test")
    parser.add_argument("--workers", type=int, default=4, help="Number of concurrent workers")
    parser.add_argument("--iterations", type=int, default=20, help="Iterations per worker")
    args = parser.parse_args()

    if not TENSEAL_AVAILABLE:
        logger.error("TenSEAL not available; install with pip install tenseal")
        return

    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting HE load test with {args.workers} workers, {args.iterations} iterations each")
    results = {}
    threads = []
    start = time.time()
    for w in range(args.workers):
        t = threading.Thread(target=worker, args=(w, args.iterations, results))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    total_time = time.time() - start
    total_ops = args.workers * args.iterations
    logger.info(f"Completed {total_ops} enc/mult/dec cycles in {total_time:.2f}s")
    logger.info(f"Throughput: {total_ops / total_time:.2f} ops/sec")
    # Latency statistics
    all_times = [t for times in results.values() for t in times]
    avg = np.mean(all_times) * 1000
    p50 = np.percentile(all_times, 50) * 1000
    p99 = np.percentile(all_times, 99) * 1000
    logger.info(f"Average latency: {avg:.2f}ms | P50: {p50:.2f}ms | P99: {p99:.2f}ms")

if __name__ == "__main__":
    main()
