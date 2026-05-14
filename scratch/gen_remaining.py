#!/usr/bin/env python3
"""
AI-f Infrastructure Generator - Creates all production environment files
"""
import os

BASE = r"D:\AI-F\AI-f"
INTRA = os.path.join(BASE, "infra")

def wf(path, content):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    print(f"  Written: {path}")

# Redis sentinel template
sentinel = """# Redis Sentinel - AI-f Production Configuration
# Quorum: 2 of 3 sentinels required for failover

sentinel monitor mymaster redis-master 6379 2
sentinel auth-pass mymaster "${REDIS_PASSWORD:-redis_pass}"
sentinel down-after-milliseconds mymaster 10000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 30000

# Notification scripts (optional)
# sentinel notification-script mymaster /etc/redis/notify.sh
# sentinel client-reconfig-script mymaster /etc/redis/reconfig.sh

# Security
rename-command FLUSHALL ""
rename-command FLUSHDB ""
rename-command CONFIG ""
rename-command DEBUG ""

# Network
port 26379
bind 0.0.0.0
protected-mode no

# Logging
loglevel notice
logfile /var/log/redis/sentinel.log
"""

wf(os.path.join(INTRA, "redis-sentinel.conf"), sentinel)

# Docker Compose - Full sandbox
sandbox = """version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: face_recognition
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init_pgvector.sql:/docker-entrypoint-initdb.d/01-pgvector.sql
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s

  redis:
    image: redis:7.2.3-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redisdata:/data
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  backend:
    build: ../backend
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_USER: postgres
      DB_PASSWORD: ${POSTGRES_PASSWORD:-password}
      DB_NAME: face_recognition
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET: ${JWT_SECRET:-test}
      ENCRYPTION_KEY: ${ENCRYPTION_KEY:-testkey123456789012}
    ports: ["8000:8000"]
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-worker:
    build: ../backend
    command: celery -A app.celery worker --loglevel=info --concurrency=2
    environment:
      DB_HOST: postgres
      REDIS_URL: redis://redis:6379/0
    depends_on: [backend, redis]

volumes:
  pgdata:
  redisdata:
"""

wf(os.path.join(INTRA, "docker-compose.sandbox.yml"), sandbox)

# FAISS docker-compose
faiss_compose = """version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5433:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: face_recognition
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: changeme_prod

  redis:
    image: redis:7-alpine
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - ./redis.conf:/usr/local/etc/redis/redis.conf:ro
      - redisdata:/data
    ports: ["6380:6379"]

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://postgres:changeme_prod@postgres:5432/face_recognition
      REDIS_URL: redis://redis:6379
      JWT_SECRET: supersecretkeychangeinprod
    volumes:
      - ../backend/models:/app/models:ro
    depends_on: [postgres, redis]
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  backend-gpu:
    build:
      context: ../backend
      dockerfile: Dockerfile.gpu
    ports: ["8001:8000"]
    environment:
      DATABASE_URL: postgresql://postgres:changeme_prod@postgres:5432/face_recognition
      REDIS_URL: redis://redis:6379
    volumes:
      - ../backend/models:/app/models:ro
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
    profiles: [gpu]

  faiss:
    image: faiss/faiss:gpu-latest
    ports: ["50051:50051"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
    profiles: [gpu]

volumes:
  pgdata:
  redisdata:
"""

wf(os.path.join(INTRA, "docker-compose.yml.faiss"), faiss_compose)

# Prometheus targets for all infrastructure components
prometheus_full = """global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'ai-f-production'
    environment: 'production'

rule_files:
  - "alert_rules.yml"

scrape_configs:
  # Backend API (Prometheus client from FastAPI/Starlette)
  - job_name: 'face-recognition-backend'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['backend:8000']
        labels:
          service: 'backend-api'
    scrape_interval: 10s

  # PgPool-II stats
  - job_name: 'pgpool'
    static_configs:
      - targets: ['pgpool:9999']
    metrics_path: '/pgpool'

  # PostgreSQL exporter
  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgres-exporter:9187']
    metrics_path: '/metrics'

  # Redis exporter
  - job_name: 'redis'
    static_configs:
      - targets:
        - 'redis-master:9121'
        - 'redis-replica1:9121'
        - 'redis-replica2:9121'
    metrics_path: '/metrics'

  # Celery exporter (flower metrics)
  - job_name: 'celery'
    static_configs:
      - targets: ['celery-flower:5555']
    metrics_path: '/metrics'

  # NGINX status
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']
    metrics_path: '/status'

  # Node/system metrics
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  # Blackbox exporter
  - job_name: 'blackbox'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - 'http://backend:8000/healthz'
        - 'http://postgres:5432'
    scrape_interval: 30s

  # Grafana self-monitoring
  - job_name: 'grafana'
    static_configs:
      - targets: ['grafana:3000']
"""

wf(os.path.join(INTRA, "prometheus.yml"), prometheus_full)

print("\n=== Infrastructure generation complete ===")
print("Files created:")
print("  - infra/redis-sentinel.conf")
print("  - infra/docker-compose.sandbox.yml")
print("  - infra/docker-compose.yml.faiss")
print("  - infra/prometheus.yml")