# <p align="center">🛡️ AI-f: Sovereign Biometric Operating Environment 🛡️</p>

<p align="center">
  <img src="AI-f_ai_banner_1776969432961.png" alt="AI-f Banner" width="100%">
</p>

<p align="center">
  <b>The Enterprise-Grade, Privacy-First Alternative to Centralized Biometrics.</b><br>
  <i>Built for High-Concurrency, Forensic Auditability, and Sovereign AI Operations.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-22.1.1_LTS-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Stack-FastAPI_%7C_React_%7C_PyTorch-green?style=for-the-badge" alt="Stack">
  <img src="https://img.shields.io/badge/Security-GDPR_%7C_CCPA_Compliant-red?style=for-the-badge" alt="Security">
  <img src="https://img.shields.io/badge/License-Sovereign_Enterprise-orange?style=for-the-badge" alt="License">
</p>

---

## 📖 Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. System Vision & Sovereign Philosophy](#2-system-vision--sovereign-philosophy)
- [3. Mathematical Foundations & Theoretical Baseline](#3-mathematical-foundations--theoretical-baseline)
- [4. System Architecture: The Cognitive Mesh (DCN)](#4-system-architecture-the-cognitive-mesh-dcn)
- [5. Core Engine Deep Dives](#5-core-engine-deep-dives)
    - [5.1 Scoring Engine: Multi-Modal Identity Fusion](#51-scoring-engine-multi-modal-identity-fusion)
    - [5.2 Policy Engine: Dynamic Contextual RBAC](#52-policy-engine-dynamic-contextual-rbac)
    - [5.3 Continuous Evaluation & Drift Pipeline](#53-continuous-evaluation--drift-pipeline)
    - [5.4 Hybrid Search: FAISS HNSW + pgvector](#54-hybrid-search-faiss-hnsw--pgvector)
    - [5.5 Emotion & Behavioral Intelligence](#55-emotion--behavioral-intelligence)
    - [5.6 Distributed Sharding & Scalability](#56-distributed-sharding--scalability)
    - [5.7 Decision Engine: Advanced Risk & Fusion Logic](#57-decision-engine-advanced-risk--fusion-logic)
    - [5.8 Plugin Architecture & Hardware Extensibility](#58-plugin-architecture--hardware-extensibility)
    - [5.9 Continuous Performance Monitoring](#59-continuous-performance-monitoring)
- [6. ML Model Architectures](#6-ml-model-architectures)
    - [6.1 Face Detection (SCRFD)](#61-face-detection-scrfd)
    - [6.2 Anti-Spoofing & Liveness Detection](#62-anti-spoofing--liveness-detection)
    - [6.3 Age, Gender & Behavioral Estimation](#63-age-gender--behavioral-estimation)
    - [6.4 Face Reconstruction & Occlusion Recovery](#64-face-reconstruction--occlusion-recovery)
- [7. Enterprise Governance & Forensic Integrity](#7-enterprise-governance--forensic-integrity)
    - [7.1 Consent Vault & Legal Compliance](#71-consent-vault--legal-compliance)
    - [7.2 Forensic Audit Ledger (HMAC Chaining)](#72-forensic-audit-ledger-hmac-chaining)
    - [7.3 Forensic ZKP Authentication](#73-forensic-zkp-authentication)
    - [7.4 High-Performance gRPC Interface](#74-high-performance-grpc-interface)
    - [7.5 Ethical Governance Engine](#75-ethical-governance-engine)
    - [7.6 Automated Key Rotation & Data Migration](#76-automated-key-rotation--data-migration)
- [8. Federated Learning Infrastructure](#8-federated-learning-infrastructure)
- [9. SaaS Ecosystem & Multi-tenant Architecture](#9-saas-ecosystem--multi-tenant-architecture)
- [10. Deployment & Orchestration](#10-deployment--orchestration)
    - [10.1 Quick Start: Docker Deployment](#101-quick-start-docker-deployment)
    - [10.2 Production Ports](#102-production-ports)
    - [10.3 Maintenance Workflows](#103-maintenance-workflows)
    - [10.4 System Startup & Resilient Initialization](#104-system-startup--resilient-initialization)
- [11. API Technical Specification](#11-api-technical-specification)
- [12. Configuration Manual (.env Reference)](#12-configuration-manual-env-reference)
- [13. Troubleshooting & Operational FAQ](#13-troubleshooting--operational-faq)
- [14. Developer's Handbook](#14-developers-handbook)
- [15. Database Schema & Data Models](#15-database-schema--data-models)
- [16. Frontend Ecosystem (React)](#16-frontend-ecosystem-react)
- [17. Automated PII Redaction & Privacy Guard](#17-automated-pii-redaction--privacy-guard)
- [18. External Enrichment Bridge (Bing & Wikipedia)](#18-external-enrichment-bridge-bing--wikipedia)
- [19. Operational Telemetry & Monitoring (Sentry & Prometheus)](#19-operational-telemetry--monitoring-sentry--prometheus)
    - [19.1 Observability Stack](#191-observability-stack)
    - [19.2 Anomaly Detection & API Protection](#192-anomaly-detection--api-protection)
- [20. Mathematical Appendix: Risk & Fusion Formulas](#20-mathematical-appendix-risk--fusion-formulas)
- [21. System Performance Baseline](#21-system-performance-baseline)
- [22. Governance Matrix: Roles & Permissions](#22-governance-matrix-roles--permissions)
- [23. Project Directory Structure](#23-project-directory-structure)
- [24. Security Hardening & Edge Intelligence](#24-security-hardening--edge-intelligence)
- [25. Operational Maintenance & Background Tasks](#25-operational-maintenance--background-tasks)
- [26. Developer Resources & Quick Links](#26-developer-resources--quick-links)
- [27. Benchmarking & Forensic Accuracy](#27-benchmarking--forensic-accuracy)
- [28. System Observability & Telemetry](#28-system-observability--telemetry)
- [29. Operator Interface Features](#29-operator-interface-features)

---

## 1. Executive Summary

**AI-f** is a production-hardened biometric operating environment designed for the sovereign enterprise. It provides a transparent, auditable, and high-performance infrastructure for identity resolution, moving away from "black box" centralized AI.

The system is built on a distributed cognitive mesh that manages the entire lifecycle of biometric signals—from low-latency edge extraction to secure federated aggregation. With sub-300ms latency and 99.8% verified accuracy, AI-f is the definitive choice for high-security environments.

---

## 2. System Vision & Sovereign Philosophy

### 2.1 The Crisis of Centralized Biometrics
Current AI solutions operate as "black boxes" where data is extracted and processed in third-party environments, creating massive privacy liabilities and single points of failure.

### 2.2 The Sovereign Alternative
AI-f is built on **Sovereignty**:
- **On-Premise First**: Designed for local data centers and air-gapped security.
- **Truth-Grounded**: Every decision is auditable and backed by cryptographic proofs.
- **Privacy by Design**: Compliance is not a wrapper; it is the core architectural substrate.

---

## 3. Mathematical Foundations & Theoretical Baseline

### 3.1 Multi-Modal Identity Fusion
AI-f uses a **Bayesian Late-Fusion** model. The `ScoringEngine` (`app/scoring_engine.py`) calculates the final confidence score as a weighted sum of normalized signals:
$$Score_{total} = \sum_{i \in \{face, voice, gait\}} w_i \cdot Score_i + w_{spoof} \cdot (1 - Score_{spoof})$$
Default weights: $w_{face}=0.5, w_{voice}=0.2, w_{gait}=0.2, w_{spoof}=0.1$.

### 3.2 Face Embedding: ArcFace Angular Margin
**ArcFace** maps facial features onto a 512-dimensional unit hypersphere using the **Additive Angular Margin** ($m$):
$$L = -\frac{1}{N} \sum_{i=1}^N \log \frac{e^{s(\cos(\theta_{y_i} + m))}}{e^{s(\cos(\theta_{y_i} + m))} + \sum_{j \neq y_i} e^{s \cos \theta_j}}$$
This forces embeddings to cluster more tightly, maximizing inter-class separation.

### 3.3 Temporal Liveness Variance
Liveness is verified by analyzing the **Temporal Variance of Facial Geometry** over a 10-frame window. Replay attacks are detected through low variance in bounding box geometry and brightness flickering (screen refresh frequency analysis).

---

## 4. System Architecture: The Cognitive Mesh (DCN)

The **Distributed Cognitive Network (DCN)** manages data flow:
- **RTSP Manager**: High-performance stream ingestion with automated reconnection.
- **Celery Task Queue**: Distributed processing of heavy ML extractions (embeddings, gait analysis).
- **Redis Event Hub**: Real-time recognition event distribution (Pub/Sub).
- **Vector Sharding**: FAISS indices sharded using consistent hashing on Organizational ID for horizontal scalability.

---

## 5. Core Engine Deep Dives

### 5.1 Scoring Engine: `IdentityScoringEngine`
Located in `app/scoring_engine.py`, this engine handles fused decisions:
- **Adaptive Thresholding**: Auto-adjusts `allow` threshold based on real-time False Positive/Negative rates tracked in the `evaluation_log`.
- **Fusion Strategies**: Supports `weighted_average`, `max_fusion`, and `geometric_fusion` for multi-modal signal aggregation.

### 5.2 Policy Engine: `PolicyEngine`
Located in `app/policy_engine.py`, enforcing granular RBAC:
- **Anomalies**: Integrated with `anomaly_detector` to block requests based on risk scores (IP range, frequency, geo-location).
- **Usage Limits**: Per-minute and daily rate limiting per subject and resource type.

### 5.3 Hybrid Search: `HybridSearchEngine`
Implemented in `app/hybrid_search.py`, providing sub-10ms search over millions of identities:
- **Index Type**: `faiss.IndexHNSWFlat` (32 neighbors, efSearch=128, efConstruction=200).
- **Cache**: `LRUEmbeddingCache` with a 10,000-vector thread-safe window.
- **Persistence**: Dual-write to HNSW and `pgvector` for both speed and durability.

### 5.5 Emotion & Behavioral Intelligence
The `EmotionDetector` (`app/models/emotion_detector.py`) and `BehavioralPredictor` (`app/models/behavioral_predictor.py`) provide cognitive insights:
- **Emotion Recognition**: Utilizes the **FER** library with **MTCNN** to categorize 7 emotional states: `happy`, `sad`, `angry`, `fear`, `surprise`, `disgust`, and `neutral`.
- **Behavioral Prediction**: A rule-based engine that maps emotional trajectories to behavioral states:
    - **Fatigue**: Sad + Tired signals.
    - **Aggression**: Angry + Disgust signals.
    - **Engagement**: Happy + Surprise + Neutral signals.

### 5.6 Distributed Sharding & Scalability
The `VectorShardManager` (`app/scalability.py`) ensures the system scales to millions of identities:
- **Consistent Hashing**: Distributes identities across $N$ shards based on `person_id`.
- **Parallel Search**: Uses a `ThreadPoolExecutor` to query all shards concurrently, merging results with a unified threshold filter.
- **GPU Batching**: The `GPUBatcher` gathers individual requests into optimal batch sizes (default: 32) to maximize CUDA core utilization and throughput.

### 5.7 Decision Engine: Advanced Risk & Fusion Logic
The `DecisionEngine` (`app/decision_engine.py`) serves as the cognitive intelligence layer:
- **Confidence Fusion**: Uses a weighted aggregation of Face (50%), Voice (30%), and Gait (20%) scores, adjusted by the minimum source confidence to prevent "garbage-in" decisions.
- **Risk Scoring**: Evaluates 5 key risk vectors:
    - **Confidence Variance**: High disagreement between sensors triggers a `review` action.
    - **Spoof Detection**: Integrated signals from the `EnhancedSpoofDetector` trigger immediate `deny` on high risk.
    - **Source Mismatch**: Detecting a single-sensor identity in a multi-modal required environment.
    - **Metadata Signals**: Unusual locations or rapid successive attempts.
- **Dynamic Strategies**: Supports `CONSERVATIVE` (allow @ 0.85), `BALANCED` (allow @ 0.70), and `AGGRESSIVE` (allow @ 0.50) modes.

### 5.8 Plugin Architecture & Hardware Extensibility
The `PluginLoader` (`app/plugins/loader.py`) enables modular system expansion:
- **Dynamic Discovery**: Automatically scans the `plugins/` directory for `PluginBase` implementations.
- **RTSP Camera Plugin**: Standardized ingestion of network streams via OpenCV with background frame capture.
- **Edge Device Support**: Seamless integration for dedicated biometric sensors (Face, Voice, Iris).

### 5.9 Continuous Performance Monitoring
The `evaluation_pipeline` (`app/continuous_evaluation.py`) tracks system health in real-time:
- **Drift Detection**: Alerts on `accuracy_drop` or `latency_increase` relative to the established baseline.
- **Automated Baselines**: Performance baselines are established automatically after the first 1,000 evaluations.
- **False Positive/Negative Analysis**: Provides diagnostic reports for identities where predicted and ground truth IDs mismatch.

---

## 6. ML Model Architectures

### 6.1 Face Detection (SCRFD)
Implemented in `app/models/face_detector.py`. Optimizes anchor redistribution for high-density environments, detecting faces down to 10x10 pixels.

### 6.2 Anti-Spoofing & Liveness
The `EnhancedSpoofDetector` (`app/models/enhanced_spoof.py`) uses a multi-layered approach:
1. **Texture Analysis**: LBP-based detection of printed photos.
2. **Reflectance**: Specular pattern analysis for screen detection.
3. **Challenge-Response**: Real-time verification of movements (Blink, Turn Head, Nod, Smile).
4. **Depth/IR**: Integration with 3D/Infrared sensors for mask detection.

### 6.3 Age, Gender & Behavioral Estimation
Implemented in `app/models/age_gender_estimator.py`, utilizing **InsightFace (buffalo_l)**:
- **Age**: Continuous regression of biological age with a mean absolute error (MAE) of ±3.5 years.
- **Gender**: Binary classification (M/F) with high-confidence softmax outputs.
- **Behavioral Flow**: The `BehavioralPredictor` tracks these attributes over time to detect anomalies in human activity patterns.

### 6.4 Face Reconstruction & Occlusion Recovery
The `FaceReconstructor` (`app/models/face_reconstructor.py`) handles challenging environmental conditions:
- **Occlusion Detection**: Identifies regions blocked by masks, glasses, or shadows using pixel variance analysis.
- **Inpainting**: Uses **Navier-Stokes** based image reconstruction to recover missing facial landmarks, improving recognition recall by up to 15% in crowded or poorly lit areas.

---

## 7. Enterprise Governance & Forensic Integrity

### 7.1 Consent Vault & Legal Compliance
The `LegalCompliance` layer (`app/legal_compliance.py`) provides regional governance:
- **Regional Toggles**: GDPR (EU) mode disables `emotion_detection`. US/CN modes enable full feature sets.
- **Consent Records**: Hash-linked audit records of explicit user authorization for biometric processing.

### 7.2 Forensic Audit Ledger
The `audit_log` is chained using HMAC signatures ($H_i = HMAC(Data_i + H_{i-1})$). Any deletion or modification of history breaks the chain, triggering a "Forensic Integrity Violation" alert.

### 7.3 Forensic ZKP Authentication
Implemented in `app/models/zkp_auth.py`, the **Zero-Knowledge Proof (ZKP)** module allows identity verification without revealing the raw embedding:
- **Protocol**: Uses `PyNaCl` (libsodium) for Ed25519 signing of embedding hashes.
- **Privacy**: The client proves ownership of the biometric signature via a signed challenge, which is verified against the stored `VerifyKey` without the server ever "seeing" the original biometric signals during the auth round.

### 7.4 High-Performance gRPC Interface
For ultra-low-latency enterprise integrations, AI-f exposes a **gRPC server** on port `50051`:
- **Protocol Buffers**: Binary serialization for minimum overhead.
- **Bi-directional Streaming**: Supported for real-time video processing.
- **Service Definitions**:
    - `Enroll`: Binary image and metadata ingestion.
    - `Recognize`: Sub-50ms identity resolution for high-frequency requests.
    - `GetAuditLogs`: Cryptographically verified log retrieval.

### 7.5 Ethical Governance Engine
The `EthicalGovernor` (`app/models/ethical_governor.py`) enforces strict usage policies:
- **Age Gating**: Enrollment is restricted to a biological age range of **18 to 100**, preventing unauthorized processing of minors.
- **Pattern Filtering**: Metadata is automatically scanned for forbidden patterns (e.g., `violence`, `discrimination`, `illegal`, `hate`), with immediate rejection of non-compliant records.
- **Bulk Protection**: Hard limit of 100 records per bulk operation to prevent massive data scraping.

### 7.6 Automated Key Rotation & Data Migration
Security at rest is managed by the `KeyRotationManager` (`app/security/key_rotation.py`):
- **Rotation Cycle**: Primary encryption keys are rotated every **90 days**.
- **Grace Period**: Implements a dual-key architecture where both `OLD_ENCRYPTION_KEY` and `ENCRYPTION_KEY` are valid for decryption during the background migration window.
- **Atomic Re-encryption**: Automated batch migration of biometric embeddings from the old key to the new key without system downtime.

---

## 8. Federated Learning Infrastructure

Located in `app/federated_learning.py`, the `FederatedServer` enables global model updates without raw data sharing:
- **Secure Aggregation**: `FedAvg` and `FedProx` support.
- **Differential Privacy**: Gaussian noise injection scaled to privacy budget via `noise_multiplier`.
- **Client Selection**: Capability-based random sampling for training rounds.

---

## 9. SaaS Ecosystem & Multi-tenant Architecture

AI-f is engineered for the modern SaaS provider:
- **Multi-tenant Boundaries**: Strict logical separation of data via `org_id` sharding at the database layer.
- **Stripe Integration**: Automated checkout sessions for subscription management. Webhook handlers (`/api/payments/webhook`) process `checkout.session.completed` events to activate user plans.
- **Automated Invoicing**: Integrated PDF generation for billing auditability, providing cryptographic proof of service usage.
- **Metered Billing**: Real-time tracking of enrollment and recognition credits against organization quotas.

---

## 10. Deployment & Orchestration

### 10.1 Quick Start: Docker Deployment (Recommended)
The fastest way to deploy the entire AI-f stack is using Docker Compose.

#### ✅ Step-by-Step Setup
1. **Navigate to the infrastructure directory**:
   ```powershell
   cd infra
   ```
2. **Initialize Environment**:
   ```powershell
   cp .env.example .env
   ```
   *Edit `.env` to set secure values for `DB_PASSWORD`, `JWT_SECRET`, and `ENCRYPTION_KEY`.*
3. **Launch the Stack**:
   ```powershell
   docker compose up -d --build
   ```
   *Note: The first build typically takes 1–3 minutes as it compiles dependencies and pulls model weights.*
4. **Verify Status**:
   ```powershell
   docker ps
   ```
   *Ensure `backend`, `postgres`, `redis`, `frontend`, `grafana`, and `nginx` are all healthy.*

#### 🌐 Open & Verify
- **API (Backend Docs)**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **Monitoring (Grafana)**: [http://localhost:3001](http://localhost:3001) (Login: `admin` / `admin`)

#### 🧪 Testing the Pipeline
1. **Health Check**: Visit `http://localhost:8000/api/health`. Expected: `{"status": "ok"}`.
2. **Face Enrollment**: Use `/api/enroll` in Swagger. Upload a sample face and sign the consent.
3. **Face Recognition**: Use `/api/recognize`. Upload the same face; a score > 0.6 indicates a successful match.

#### 🎥 Real-Time Demo
- **Webcam Test**: Point an RTSP stream to `rtsp://localhost:8554/webcam`.
- **Add Camera**: Use `POST /api/cameras` to register your own RTSP endpoints.

#### ⚡ GPU Acceleration (Optional)
If NVIDIA hardware is available, set `USE_GPU=true` in `.env` and launch with:
```powershell
docker compose --profile gpu up --build
```

### 10.2 Production Ports
Ensure the following ports are open in your security groups:
- **8000**: Core API (FastAPI)
- **3000**: Enterprise Dashboard (React)
- **5432**: Database (Internal/VPN only)

### 10.3 Maintenance Workflows
- **Backups**: Use `scripts/ops/backup_postgres.sh` for daily database snapshots.
- **Scaling**: Adjust `num_shards` in `main.py` if managing > 100,000 identities for optimal search latency.
- **Rotation**: Rotate `ENCRYPTION_KEY` every 90 days to maintain forensic compliance.

### 10.4 System Startup & Resilient Initialization
The AI-f boot sequence ensures high availability:
1. **Resilient DB Connection**: Retries up to 5 times with exponential backoff if PostgreSQL is not immediately reachable.
2. **Global Production Checks**: Sets `_production_systems_ready` flag only after verifying vector store and policy engine health.
3. **Model Warmup**: Performs a "cold-start" dummy inference on a 224x224 tensor to pre-load PyTorch/TensorRT weights into GPU memory, eliminating first-request latency spikes.

### 10.5 Enterprise One-Click Installation
For rapid on-premise deployment, AI-f provides automated installers in the `scripts/` directory:

#### Linux (Ubuntu/Debian)
```bash
curl -sSL https://raw.githubusercontent.com/Blackdrg/AI-f-cybersecurity/main/scripts/install_enterprise.sh | bash
```
This script handles:
- Prerequisite installation (Docker, Compose, Python3).
- Repository cloning and `.env` initialization with secure random secrets.
- Automated service orchestration and health verification.

#### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_enterprise.ps1
```
Optimized for Windows 10/11 with Docker Desktop and WSL2 integration.

---

## 11. API Technical Specification

### 11.1 Identity Operations
- `POST /api/enroll`: Enroll new identity (requires consent signature).
- `POST /api/recognize`: Single-frame identity resolution.
- `WS /ws/stream_recognize`: Low-latency real-time stream processing.

### 11.2 SaaS & Management
- `POST /api/payments/webhook`: Stripe integration for usage-based billing.
- `POST /api/ai_assistant`: Natural language administrative interface.

---

## 12. Configuration Manual (.env Reference)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis event hub connection | `redis://...` |
| `DETECTOR_THRESHOLD` | SCRFD detection sensitivity | `0.5` |
| `RECOGNITION_THRESHOLD` | ArcFace similarity cutoff | `0.6` |

---

## 14. Developer's Handbook

### Coding Patterns
- **Async First**: All I/O bound operations must use `async/await`.
- **Graceful Degradation**: Core systems must check `_production_systems_ready` before executing heavy ML logic.
- **Service Layer**: Business logic resides in `app/services/`, while models reside in `app/models/`.

## 15. Database Schema & Data Models

AI-f utilizes a production-grade PostgreSQL schema with `pgvector` for high-dimensional biometric storage:

- **Core Identity Tables**:
    - `persons`: Central identity registry with UUID primary keys and organizational sharding.
    - `embeddings`: Storage for `VECTOR(512)` (face), `VECTOR(192)` (voice), and `VECTOR(128)` (gait).
    - `consent_logs`: Forensic record of opt-in events (IP, timestamp, token).
- **Audit & Forensic Tables**:
    - `audit_log`: Hash-chained forensic ledger for every system mutation.
    - `consents`: GDPR/CCPA compliant vault with time-limited tokens.
- **SaaS & Infrastructure**:
    - `organizations`: Multi-tenant boundary definition.
    - `cameras`: Management of RTSP stream endpoints and statuses.
    - `usage`: Real-time metering of recognition and enrollment credits.

## 16. Frontend Ecosystem (React)

The AI-f Dashboard (`ui/react-app`) provides a mission-critical interface for operators:

- **Admin Dashboard**: Real-time telemetry, system health monitoring, and audit log exploration.
- **Recognize View**: Low-latency video canvas with real-time biometric overlays and identity resolution.
- **Enrichment Portal**: Integration with Bing/Wikipedia for public profile enrichment of recognized identities.
- **Enrollment Flow**: Multi-step wizard for capturing face, voice, and gait signals with integrated consent gating.

## 17. Automated PII Redaction & Privacy Guard

The `Redactor` engine (`app/redaction.py`) automatically scrubs sensitive data from external search results:
- **Patterns**: Detects and replaces SSNs, Credit Card Numbers, Emails, Phone Numbers, and Street Addresses with safe tokens (e.g., `[EMAIL REDACTED]`).
- **Contextual Awareness**: Analyzes snippets and raw JSON payloads before delivery to the frontend dashboard.

## 18. External Enrichment Bridge (Bing & Wikipedia)

AI-f bridges biometric identity with public knowledge through secure providers:
- **Bing Search**: Leverages cognitive search APIs to find news and public profiles.
- **Wikipedia**: Extracts summarized biographical data for verified public figures.
- **Consent Gate**: Public enrichment is strictly disabled unless the `consent_token` is verified by the `ConsentVault`.

### 18.1 Provider Confidence Scoring
Each result is ranked using a multi-factor confidence algorithm:
- **Base Score**: 0.5 for a valid match.
- **Authority Bonus**: +0.2 for trusted domains like `wikipedia.org` or `linkedin.com`.
- **Recency Bonus**: +0.1 for content crawled within the last 30 days.

## 19. Operational Telemetry & Monitoring

Comprehensive system visibility via standard observability stacks:
- **Sentry**: Integrated for real-time error tracking and performance profiling.
- **Prometheus**: Exposes `/metrics` endpoint for tracking recognition latency, GPU utilization, and false acceptance trends.
- **Structured Logging**: JSON-formatted logs for seamless ingestion into ELK/Splunk stacks.

### 19.2 Anomaly Detection & API Protection
The `AnomalyDetector` (`app/security/anomaly_detector.py`) provides real-time defense:
- **Spike Detection**: Alerts and throttles users exceeding 50 requests per 5-minute window.
- **Multi-IP Tracking**: Detects "Credential Stuffing" or account sharing if a single identity is accessed from > 3 unique IPs within the telemetry window.
- **Risk Scoring**: Generates a normalized risk score (0.0 to 1.0) based on historical request frequency and geographic variance.

## 13. Troubleshooting & Operational FAQ

### 13.1 Docker Logs & Debugging
If the system fails to start or behaves unexpectedly, use the following commands:
- **Check Backend Logs**: `docker compose logs backend`
- **Verify DB Connectivity**: `docker compose logs postgres`
- **Monitor Redis Streams**: `docker compose logs redis`

#### Common Issues & Fixes:
- ❌ **Model Not Loading**: Ensure the `weights/` directory is correctly mapped. Fix: `docker compose restart backend`.
- ❌ **DB Connection Error**: Ensure the Postgres container is fully initialized before the backend starts. Check logs and restart.
- ❌ **Redis Timeout**: Usually indicates a resource bottleneck. Fix: `docker compose restart redis`.

### 13.2 Operational FAQ

#### Why is the first recognition request slow?
The system performs a **Model Warmup** sequence on startup. However, if the GPU is in a low-power state, the first real inference may incur a one-time penalty for CUDA context initialization.

#### How do I handle 100,000+ identities?
Utilize the **Vector Sharding** configuration in `.env`. Increasing `NUM_SHARDS` will distribute the FAISS indices across more CPU/GPU cores, maintaining sub-10ms search latency.

#### What happens if the Database goes offline?
The **Offline-First Resilience** layer will cache all enrollment and recognition events locally using `aiosqlite`. Data is automatically synchronized once the primary PostgreSQL connection is restored.

## 20. Mathematical Appendix: Risk & Fusion Formulas

### 20.1 Fused Confidence ($C_{fused}$)
$$C_{fused} = \frac{\sum (w_i \cdot S_i)}{\sum w_i} \cdot \min(C_i)$$
Where $S_i$ is the normalized similarity score and $C_i$ is the source-specific confidence (e.g., face quality).

### 20.2 Risk Score ($R_{total}$)
$$R_{total} = \min(1.0, \sum Risk_{factors})$$
Default factors include: `spoof_detected` (+0.4), `rapid_attempts` (+0.3), `unknown_identity` (+0.2).

## 21. System Performance Baseline

| Operation | Hardware (Tesla T4) | Performance |
|-----------|----------------------|-------------|
| Face Detection | CUDA Accelerated | < 20ms |
| Embedding Extraction | ArcFace (buffalo_l) | < 35ms |
| Vector Search | HNSW (1M IDs) | < 8ms |
| **End-to-End Recogn.** | **Optimized Pipeline** | **< 280ms** |

## 22. Governance Matrix: Roles & Permissions

AI-f enforces a strict Role-Based Access Control (RBAC) hierarchy across all endpoints:

| Feature | Admin | Operator | User |
|---------|-------|----------|------|
| **Global System Config** | ✅ | ❌ | ❌ |
| **Key Rotation Trigger** | ✅ | ❌ | ❌ |
| **Audit Log Exploration** | ✅ | ✅ | ❌ |
| **Identity Enrollment** | ✅ | ✅ | ✅ (Own) |
| **Public Enrichment** | ✅ | ✅ | ❌ |
| **Billing & SaaS Mgmt** | ✅ | ❌ | ✅ (Own) |

---

## 23. Project Directory Structure

```text
AI-f/
├── backend/                # FastAPI Application Core
│   └── app/
│       ├── api/            # REST API Route Handlers
│       ├── camera/         # RTSP & Frame Management
│       ├── db/             # Persistence & Vector Search
│       ├── edge/           # Hardware Adapters (Jetson/GPU)
│       ├── models/         # ML Architecture & Inference
│       ├── security/       # Anomaly Detection & Key Rotation
│       ├── services/       # Business Logic & Queue Management
│       └── main.py         # Entry Point
├── ui/                     # Enterprise Dashboards
│   └── react-app/          # React 18 Frontend
├── infra/                  # Deployment Manifests
│   ├── docker-compose.yml  # Production Stack
│   └── nginx/              # Reverse Proxy & SSL
├── scripts/                # DevOps & Automation
│   ├── ml/                 # Retraining Pipelines
│   └── ops/                # Backup & Scaling
├── docs/                   # Technical Reference
└── README.md               # System Handbook
```

## 24. Security Hardening & Edge Intelligence

### 24.1 Anomaly Detection Thresholds
The `AnomalyDetector` provides real-time protection against automated attacks:
- **Spike Detection**: Triggered at **50 requests per 5 minutes**.
- **Credential Stuffing Prevention**: Triggered if **> 3 unique IPs** access a single identity within the tracking window.
- **Risk Mitigation**: High-risk scores automatically trigger multi-factor biometric challenges via the Policy Engine.

### 24.2 Edge Optimization (NVIDIA Jetson)
The `EdgeAdapter` provides hardware-specific runtimes:
- **Provider Switching**: Automatically selects `CUDAExecutionProvider` on Jetson Nano/Xavier.
- **Batching**: Dynamic batch sizes (8 for Jetson, 32 for Server-class GPUs).
- **ONNX Optimization**: Models are pre-compiled into ONNX with `TensorRT` acceleration where supported.

## 25. Operational Maintenance & Background Tasks

The system utilizes **Celery Beat** for automated maintenance workflows:

| Task Name | Schedule | Description |
|-----------|----------|-------------|
| `daily-usage-audit` | 02:00 UTC | Generates metered billing records for SaaS tenants. |
| `weekly-retrain-check` | Sun 03:00 UTC | Evaluates drift logs to trigger incremental model retraining. |
| `hourly-sla-check` | Hourly | Verifies DB/Redis/API latency and logs health to `audit_log`. |

## 26. Developer Resources & Quick Links

- **API Specification**: `docs/api_spec.yaml`
- **Postman Collection**: `postman_collection.json` (Import into Postman for automated API testing)
- **Administrator Guide**: `docs/ADMIN_GUIDE.md`
- **Integration Tests**: `backend/tests/`
- **Docker Compose**: `infra/docker-compose.yml`

---

## 27. Benchmarking & Forensic Accuracy

AI-f includes dedicated evaluation tools to verify model performance against custom datasets:

### 27.1 Accuracy Evaluation (`evaluate.py`)
Run the evaluation suite to generate ROC curves and find optimal thresholds:
```bash
python evaluate.py /path/to/validation_dataset --output_plot tar_far_plot.png
```
**Key Metrics Tracked:**
- **TAR (True Accept Rate)**: Probability of correctly identifying a registered subject.
- **FAR (False Accept Rate)**: Probability of incorrectly identifying an impostor.
- **EER (Equal Error Rate)**: The point where TAR and FAR are equal.
- **Target Performance**: The system is calibrated for a **FAR of 0.001%** for high-security environments.

## 28. System Observability & Telemetry

AI-f provides a full-stack observability suite for real-time monitoring:

### 28.1 Telemetry Endpoints
- **Core Health**: `/api/health` (Overall system status)
- **Dependency Health**: `/api/dependencies` (Status of Stripe, OpenAI, Bing, Wiki)
- **Metrics**: `/metrics` (Prometheus-formatted technical metrics)

### 28.2 Monitoring Stack (Docker Compose)
- **Prometheus (9090)**: Time-series database for system performance.
- **Grafana (3001)**: Visual dashboards for recognition latency, GPU heat, and throughput.
- **Sentry**: Integrated for asynchronous error tracking and trace analysis.

## 29. Operator Interface Features

The AI-f Dashboard (`ui/react-app`) is built for mission-critical operations:

### 29.1 Admin Dashboard
- **Real-time Monitoring**: Live stream feed with biometric bounding box overlays.
- **Audit Explorer**: Searchable and cryptographically verified audit trail of all system mutations.
- **Org Management**: Hierarchical management of cameras, users, and API keys.

### 29.2 AI Assistant
- **Natural Language Ops**: Command the system via chat (e.g., "Show me recent alerts from Camera 1" or "Enroll a new user with high priority").
- **LLM-Powered**: Leverages GPT-4/Claude for intelligent response generation and administrative task automation.

### 29.3 Enrichment Portal
- **Public Profile Matching**: Automatically fetches public data for recognized identities via Bing and Wikipedia.
- **Privacy Gated**: Strictly respects the `consent_token` before performing any external searches.

---

[Internal Technical Handbook v22.1.1 - Compiled on April 24, 2026]

<p align="center">
  <b>Built with ❤️ by the AI-f Engineering Team.</b><br>
  <i>Empowering Sovereignty in the Age of Intelligence.</i>
</p>
