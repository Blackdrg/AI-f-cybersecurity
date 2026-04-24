# LEVI-AI Architecture Diagram

```mermaid
graph TD
    %% External Entities
    Client[Enterprise Client / Camera RTSP]
    Admin[Admin Dashboard]

    %% Ingress & API Gateway
    subgraph K8s_Cluster [Kubernetes Sovereign Cluster]
        Ingress[Nginx Ingress / TLS 1.3]
        
        %% Core API Services
        subgraph App_Layer [Application Layer]
            API[FastAPI Core Gateway]
            Web[React Frontend UI]
        end

        %% Cognitive Mesh
        subgraph Cognitive_Mesh [Cognitive Mesh & ML]
            EdgeManager[RTSP / Edge Manager]
            Scoring[Identity Scoring Engine]
            ZKP[Zero-Knowledge Proof Auth]
            Celery[Celery ML Workers - GPU]
        end

        %% Data Persistence
        subgraph Data_Layer [State & Persistence]
            Redis[(Redis Pub/Sub & Cache)]
            PG[(PostgreSQL + pgvector)]
            FAISS[(FAISS HNSW Vector Shards)]
        end

        %% Observability
        subgraph Observability [Telemetry]
            Prometheus[Prometheus Metrics]
            Grafana[Grafana Dashboards]
        end
    end

    %% Flow Connections
    Client -- "RTSP / Video Stream" --> EdgeManager
    Client -- "HTTPS / API Calls" --> Ingress
    Admin -- "HTTPS / WSS" --> Ingress
    
    Ingress --> Web
    Ingress --> API

    API --> ZKP
    API --> Scoring
    API -- "Async Tasks" --> Celery

    EdgeManager -- "Frame Pub" --> Redis
    Scoring -- "Search Vectors" --> FAISS
    Scoring -- "Transactional Sync" --> PG
    Celery -- "Read/Write Embeddings" --> PG

    API -. "Metrics" .-> Prometheus
    Celery -. "Metrics" .-> Prometheus
    Prometheus --> Grafana
```

This diagram illustrates the fully sovereign, air-gapped deployment architecture for LEVI-AI. All components reside within the enterprise's controlled Kubernetes environment.
