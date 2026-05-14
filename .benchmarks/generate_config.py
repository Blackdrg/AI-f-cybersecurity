#!/usr/bin/env python3
"""
AI-f Load Testing Configuration
Generates Locust scenarios and test configurations.
"""
import json

# Load test scenarios
SCENARIOS = {
    "baseline": {
        "name": "Baseline Performance",
        "users": 100,
        "spawn_rate": 10,
        "duration_seconds": 300,
        "description": "100 concurrent users, 5 minutes"
    },
    "medium_load": {
        "name": "Medium Load",
        "users": 500,
        "spawn_rate": 50,
        "duration_seconds": 600,
        "description": "500 concurrent users, 10 minutes"
    },
    "stress": {
        "name": "Stress Test",
        "users": 1000,
        "spawn_rate": 100,
        "duration_seconds": 1800,
        "description": "1000 concurrent users, 30 minutes"
    },
    "spike": {
        "name": "Spike Test",
        "users": 2000,
        "spawn_rate": 500,
        "duration_seconds": 600,
        "description": "Instant spike to 2000 users, 10 minutes"
    },
    "endurance": {
        "name": "72-Hour Endurance",
        "users": 100,
        "spawn_rate": 10,
        "duration_seconds": 259200,
        "description": "Sustained load for 72 hours"
    }
}

# Endpoint definitions
ENDPOINTS = [
    {"path": "/api/v1/healthz", "method": "GET", "weight": 1, "name": "health"},
    {"path": "/api/v1/status", "method": "GET", "weight": 2, "name": "status"},
    {"path": "/api/v1/recognize", "method": "POST", "weight": 10, "name": "recognize"},
    {"path": "/api/v1/enroll", "method": "POST", "weight": 3, "name": "enroll"},
    {"path": "/api/v1/persons", "method": "GET", "weight": 5, "name": "persons_list"},
    {"path": "/api/v1/cameras", "method": "GET", "weight": 4, "name": "cameras_list"},
    {"path": "/api/v1/alerts", "method": "GET", "weight": 3, "name": "alerts_list"},
    {"path": "/metrics", "method": "GET", "weight": 1, "name": "prometheus_metrics"},
]

# Thresholds
THRESHOLDS = {
    "max_p50_latency_ms": 50,
    "max_p95_latency_ms": 200,
    "max_p99_latency_ms": 500,
    "min_throughput_rps": 500,
    "max_error_rate_pct": 1.0,
}

config = {
    "scenarios": SCENARIOS,
    "endpoints": ENDPOINTS,
    "thresholds": THRESHOLDS,
    "target_api_url": "${API_URL:-http://localhost:8000}",
    "redis_url": "${REDIS_URL:-redis://localhost:6379}",
}

with open('/D:/AI-F/AI-f/.benchmarks/load_test_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print("Load test configuration written")
print(json.dumps(config, indent=2))