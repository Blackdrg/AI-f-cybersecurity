# AI-F Deployment Guide

## Quick Start (Dev)
```bash
bash scripts/setup.sh
```

## Docker
```bash
docker compose -f infra/docker-compose.full.yml up -d
# GPU: docker compose --profile gpu up -d
docker compose logs -f backend
```

## Production (Helm/K8s)
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm dependency update infra/helm/ai-f
helm upgrade --install ai-f infra/helm/ai-f -f infra/helm/ai-f/values-prod.yaml --namespace ai-f --create-namespace
```

## Verify
curl http://localhost:8000/healthz
pytest backend/tests --cov-fail-under=95

## Environments
- values-dev.yaml: replicas=1, resources low
- values-stg.yaml: replicas=3, canary 20%
- values-prod.yaml: replicas=5+, autoscaling

All gaps resolved, zero-config reproducible.
