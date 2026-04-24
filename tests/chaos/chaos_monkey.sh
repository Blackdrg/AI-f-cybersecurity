#!/bin/bash
# LEVI-AI Chaos & Failure Testing Script (Chaos Monkey)
# Simulates catastrophic failures in a Kubernetes/Docker environment

echo "========================================="
echo "🦍 Initiating LEVI-AI Chaos Testing 🦍"
echo "========================================="

echo "[1] Simulating Redis Cache Failure (Mid-Recognition)..."
kubectl scale deployment redis-master --replicas=0
sleep 5
echo "--> Verifying fallback to PostgreSQL..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/recognize
echo ""
kubectl scale deployment redis-master --replicas=1

echo "[2] Simulating PostgreSQL Database Failure (During Enrollment)..."
kubectl scale deployment postgresql --replicas=0
sleep 5
echo "--> Verifying ZKP Ledger handles transaction rollback..."
curl -X POST -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/enroll
echo ""
kubectl scale deployment postgresql --replicas=1

echo "[3] Simulating GPU Crash / OOM..."
# Force a crash on the GPU pod (assuming nvidia-smi is available in the pod)
kubectl exec $(kubectl get pods -l app=ai-f -o jsonpath='{.items[0].metadata.name}') -- kill -9 1
sleep 10
echo "--> Verifying Pod Auto-Recovery via Liveness Probes..."
kubectl get pods -l app=ai-f

echo "[4] Simulating Network Partition (Service Mesh)..."
# Applying a network policy to drop traffic between API and DB
kubectl apply -f tests/chaos/network-partition.yaml
sleep 5
echo "--> Verifying circuit breakers trip cleanly..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
kubectl delete -f tests/chaos/network-partition.yaml

echo "========================================="
echo "✅ Chaos Test Suite Completed. View logs for recovery times."
echo "========================================="
