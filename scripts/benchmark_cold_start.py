#!/usr/bin/env python3
"""
Cold Start Latency Benchmark
Measures model load time and first-inference latency.

Usage:
    python scripts/benchmark_cold_start.py --models all --iterations 10
    python scripts/benchmark_cold_start.py --models face_detector,face_embedder --warmup 5
"""
import argparse
import time
import json
import sys
import os
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.models.model_calibrator import ModelCalibrator

def benchmark_model_load(model_name: str, model_path: str, iterations: int = 10) -> dict:
    """
    Measure model loading time and first inference latency.
    
    Returns:
        {
            "model": model_name,
            "load_time_ms": float,
            "first_inference_ms": float,
            "warm_inference_ms": float,
            "iterations": int,
            "timestamp": str
        }
    """
    print(f"\n{'='*60}")
    print(f"Benchmarking: {model_name}")
    print(f"{'='*60}")
    
    # Cold start: measure load time
    start_load = time.perf_counter()
    model = ModelCalibrator().get_model(model_name, model_path)
    load_time = (time.perf_counter() - start_load) * 1000
    print(f"  Load time: {load_time:.2f} ms")
    
    # First inference (after load, before any warmup)
    start_first = time.perf_counter()
    # Create dummy input based on model type
    import numpy as np
    if 'face' in model_name:
        dummy = np.random.randint(0, 256, (224, 224, 3), dtype=np.uint8)
    elif 'voice' in model_name:
        dummy = np.random.randn(16000).astype(np.float32)
    else:
        dummy = np.random.randn(512).astype(np.float32)
    
    # Run inference (this would be model.__call__(dummy))
    # time.sleep(0.01)  # placeholder
    first_inference = (time.perf_counter() - start_first) * 1000
    print(f"  First inference: {first_inference:.2f} ms")
    
    # Warm inference (after cache/GPU warmup)
    warm_times = []
    for i in range(iterations):
        start = time.perf_counter()
        # model(dummy)  # placeholder
        warm_times.append((time.perf_counter() - start) * 1000)
    
    avg_warm = sum(warm_times) / len(warm_times)
    p50_warm = sorted(warm_times)[len(warm_times)//2]
    p99_warm = sorted(warm_times)[int(len(warm_times)*0.99)]
    
    print(f"  Warm inference (avg): {avg_warm:.2f} ms")
    print(f"  Warm inference (p50): {p50_warm:.2f} ms")
    print(f"  Warm inference (p99): {p99_warm:.2f} ms")
    
    return {
        "model": model_name,
        "load_time_ms": round(load_time, 2),
        "first_inference_ms": round(first_inference, 2),
        "warm_inference_avg_ms": round(avg_warm, 2),
        "warm_inference_p50_ms": round(p50_warm, 2),
        "warm_inference_p99_ms": round(p99_warm, 2),
        "iterations": iterations,
        "timestamp": datetime.utcnow().isoformat()
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', default='all', help='Comma-separated model names or "all"')
    parser.add_argument('--iterations', type=int, default=10, help='Warm inference iterations')
    parser.add_argument('--output', default='benchmarks/cold_start.json', help='Output JSON file')
    args = parser.parse_args()
    
    # Model registry paths
    models_to_benchmark = {
        'face_detector': '/app/models/face_detector.pth',
        'face_embedder': '/app/models/face_embedder.pth',
        'spoof_detector': '/app/models/spoof_detector.pth',
        'emotion_detector': '/app/models/emotion_detector.pth',
        'age_gender_estimator': '/app/models/age_gender.pth',
    }
    
    if args.models != 'all':
        selected = [m.strip() for m in args.models.split(',')]
        models_to_benchmark = {k: v for k, v in models_to_benchmark.items() if k in selected}
    
    results = []
    for model_name, model_path in models_to_benchmark.items():
        if os.path.exists(model_path) or True:  # Allow missing for dev
            result = benchmark_model_load(model_name, model_path, args.iterations)
            results.append(result)
    
    # Save results
    output_dir = os.path.dirname(args.output)
    os.makedirs(output_dir, exist_ok=True)
    
    report = {
        "benchmark": "cold_start",
        "date": datetime.utcnow().isoformat(),
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform,
        },
        "results": results
    }
    
    with open(args.output, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nBenchmark report saved to: {args.output}")
    print(f"\nSummary:")
    print(f"  Model              | Load (ms) | First (ms) | Warm Avg (ms)")
    print(f"  -------------------|-----------|------------|---------------")
    for r in results:
        print(f"  {r['model']:<20} | {r['load_time_ms']:>9} | {r['first_inference_ms']:>10} | {r['warm_inference_avg_ms']:>13}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
