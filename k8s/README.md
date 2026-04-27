# Kustomize Overlays for Kubernetes

This directory defines environment-specific overlays for deploying AI-f.

## Structure

```
k8s/
├── base/                    # Base configuration (shared)
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml            # PodDisruptionBudget
│   └── cert-manager.yaml   # TLS certificates
├── overlays/
│   ├── development/
│   │   ├── kustomization.yaml
│   │   ├── configmap.yaml   # Dev-specific config
│   │   ├── ingress.yaml     # Dev ingress rules
│   │   └── patches/
│   │       └── deployment.yaml  # Dev resource limits
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   ├── configmap.yaml   # Staging config
│   │   ├── secret.yaml      # Staging secrets (SOPS encrypted)
│   │   └── patches/
│   └── production/
│       ├── kustomization.yaml
│       ├── configmap.yaml   # Prod config
│       ├── secret.yaml      # Prod secrets (external-secrets)
│       ├── ingress.yaml     # Prod ingress with WAF
│       ├── pod-disruption-budget.yaml
│       └── patches/
│           └── deployment.yaml  # Prod resource limits + replicas
└── components/              # Reusable components
    ├── redis/
    ├── postgresql/
    └── prometheus-operator/
```

## Base Configuration (`base/`)

The base layer defines the core application resources that are common across all environments.

### base/kustomization.yaml
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

# All resources are applied in order
resources:
  - namespace.yaml
  - configmap.yaml
  - secret.yaml (template, actual values from overlays)
  - deployment.yaml
  - service.yaml
  - ingress.yaml
  - hpa.yaml
  - pdb.yaml

# Common labels for all resources
commonLabels:
  app: ai-f
  environment: base

# Name prefix
namePrefix: ai-f-

# Secret generator (for local/dev only - use external-secrets in prod)
generatorOptions:
  disableNameSuffixHash: true

secretGenerator:
  - name: app-secrets
    namespace: face-recognition
    envs:
      - secrets.env
    type: Opaque
```

### base/deployment.yaml
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-f-backend
  template:
    metadata:
      labels:
        app: ai-f-backend
    spec:
      serviceAccountName: ai-f-backend
      containers:
        - name: backend
          image: ghcr.io/owner/ai-f-backend:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: app-secrets
          resources:
            limits:
              cpu: "4"
              memory: "16Gi"
              nvidia.com/gpu: 1  # Request GPU (if available)
            requests:
              cpu: "2"
              memory: "8Gi"
          startupProbe:
            httpGet:
              path: /api/health
              port: 8000
            failureThreshold: 30
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /api/health
              port: 8000
            periodSeconds: 30
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /api/dependencies
              port: 8000
            periodSeconds: 10
          volumeMounts:
            - name: models
              mountPath: /app/models
      volumes:
        - name: models
          persistentVolumeClaim:
            claimName: models-pvc
```

## Overlays

### Development (`overlays/development/`)

**Purpose:** Local development, testing, CI.

**Characteristics:**
- Single replica
- Debug logging enabled
- Mock external services (S3, Stripe)
- In-memory SQLite fallback if PostgreSQL unavailable
- Resource limits lower (CPU: 1, Memory: 2Gi)

**kustomization.yaml:**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: face-recognition-dev

bases:
  - ../../base

patchesStrategicMerge:
  - patches/deployment.yaml
  - patches/service.yaml

configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - LOG_LEVEL=DEBUG
      - ENVIRONMENT=development
      - DB_SSL_MODE=disable
      - CORS_ORIGINS=*
      - RATE_LIMIT_ENABLED=false
      - METRICS_ENABLED=true

secretGenerator:
  - name: app-secrets
    envs:
      - secrets-dev.env
    type: Opaque
```

**patches/deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 1  # Single replica for dev
  template:
    spec:
      containers:
        - name: backend
          resources:
            limits:
              cpu: "1"
              memory: "2Gi"
              nvidia.com/gpu: 0  # No GPU required
            requests:
              cpu: "500m"
              memory: "1Gi"
          env:
            - name: DEBUG
              value: "true"
```

### Staging (`overlays/staging/`)

**Purpose:** Pre-production testing, QA, performance validation.

**Characteristics:**
- 3 replicas (HA)
- Real PostgreSQL + Redis
- Staging Stripe test environment
- Moderate resource limits
- Canary deployment strategy enabled

**kustomization.yaml:**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: face-recognition-staging

bases:
  - ../../base
  - ../../components/ingress-nginx

patchesStrategicMerge:
  - patches/deployment-staging.yaml
  - patches/hpa-staging.yaml

configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - LOG_LEVEL=WARNING
      - ENVIRONMENT=staging
      - DB_SSL_MODE=require
      - CORS_ORIGINS=https://staging.example.com
      - RATE_LIMIT_ENABLED=true
      - METRICS_ENABLED=true

secretGenerator:
  - name: app-secrets
    envs:
      - secrets-staging.enc.env  # Encrypted with SOPS
    encryption:
      type: AESGCM
      ... 
```

### Production (`overlays/production/`)

**Purpose:** Live production traffic.

**Characteristics:**
- Multi-region deployment (us-east-1, us-west-2)
- Auto-scaling (3-50 pods)
- GPU-enabled nodes
- Strict resource limits + requests
- External secrets (AWS Secrets Manager / HashiCorp Vault)
- PodDisruptionBudget (min 2 available)
- NetworkPolicies (zero-trust)

**kustomization.yaml:**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: face-recognition-production

bases:
  - ../../base

patchesStrategicMerge:
  - patches/deployment-prod.yaml
  - patches/hpa-prod.yaml
  - patches/pdb.yaml
  - patches/network-policy.yaml
  - patches/pod-anti-affinity.yaml

configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - LOG_LEVEL=WARNING
      - ENVIRONMENT=production
      - DB_SSL_MODE=verify-full
      - CORS_ORIGINS=https://example.com
      - RATE_LIMIT_ENABLED=true
      - METRICS_ENABLED=true
      - OTEL_EXPORTER=jaeger

secretGenerator:
  - name: app-secrets
    externalSecrets:
      - aws-secrets-manager: ai-f/production
```

**patches/deployment-prod.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero-downtime
  template:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: ai-f-backend
                topologyKey: kubernetes.io/hostname
      containers:
        - name: backend
          resources:
            limits:
              cpu: "4"
              memory: "16Gi"
              nvidia.com/gpu: 1
            requests:
              cpu: "2"
              memory: "8Gi"
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: app-secrets
```

**patches/hpa-prod.yaml:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend
spec:
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## Usage

### Build & Deploy Development
```bash
# Build Docker image
docker build -t ai-f-backend:dev ./backend

# Deploy with Kustomize
kustomize build k8s/overlays/development | kubectl apply -f -

# Verify
kubectl get pods -n face-recognition-dev
```

### Deploy to Staging
```bash
export IMAGE_TAG=staging-20260427
kustomize build k8s/overlays/staging | kubectl apply -f -
```

### Deploy to Production
```bash
# Use GitOps (Flux/ArgoCD) for production
# Or manual promotion from staging:
kustomize build k8s/overlays/production | kubectl apply -f -
```

### Generate Manifests
```bash
# See what will be applied
kustomize build k8s/overlays/production > prod-manifest.yaml

# Diff against live cluster
kubectl diff -f prod-manifest.yaml
```

---

**Note:** For production, integrate with external-secrets operator for secret management:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets-prod
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: aws-secrets-store
    kind: SecretStore
  target:
    name: app-secrets
  data:
    - secretKey: JWT_SECRET
      remoteRef:
        key: ai-f/production
        property: jwt_secret
```
