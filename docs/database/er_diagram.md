# Database Entity Relationship Diagram

```mermaid
erDiagram
    persons ||--o{ embeddings : "has"
    persons ||--o{ recognition_events : "observed_in"
    persons ||--o{ consent_logs : "consent"
    persons ||--o{ feedback : "feedback"
    persons ||--o{ audit_log : "audit"
    
    organizations ||--o{ org_members : "contains"
    organizations ||--o{ cameras : "deploys"
    organizations ||--o{ recognition_events : "generates"
    organizations ||--o{ bias_reports : "has"
    
    users ||--o{ org_members : "member_of"
    users ||--o{ subscriptions : "subscribes"
    users ||--o{ payments : "pays"
    users ||--o{ tickets : "reports"
    users ||--o{ sessions : "has"
    users ||--o{ mfa_secrets : "has"
    users ||--o{ mfa_attempts : "makes"
    
    persons ||--o{ persons : "merged_to" |
    persons ||--o{ persons : "merged_from"
    
    model_versions ||--o{ edge_devices : "deployed_on"
    edge_devices ||--o{ ota_updates : "receives"
    federated_updates ||--o{ edge_devices : "from"
    
    alert_rules ||--o{ alerts : "triggers"
    recognition_events ||--o{ alerts : "generates"
```

## Table Relationships

### Core Identity Flow
```
users ──(org_members)──> organizations ──(org_id)──> persons ──(person_id)──> embeddings
                                                                     │
                                                                     ├─> recognition_events ──> (camera_id)──> cameras
                                                                     │
                                                                     └─> audit_log (person_id)
```

### Multi-Tenancy Isolation
```
organizations
    ├── users (via org_members with role)
    ├── cameras
    ├── recognition_events
    ├── persons
    └── api_keys
```

### Model Registry & OTA
```
model_versions
    ├── edge_devices (current model)
    └── edge_devices.pending_update (OTA target)
         └── ota_updates (deployment tracking)
```

### Audit Trail (Hash-Chain)
```
audit_log
    ├── previous_hash (links to previous row)
    ├── hash (current row fingerprint)
    └── zkp_proof (optional cryptographic proof)
```

### Session & MFA
```
users
    ├── sessions (active sessions)
    ├── mfa_secrets (TOTP config)
    └── mfa_attempts (audit of MFA tries)
```

### Billing & Usage
```
users
    ├── subscriptions (active plan)
    ├── payments (transactions)
    ├── usage (monthly counters)
    └── support_tickets (support)
```

### Federated Learning
```
edge_devices
    ├── federated_updates (gradient uploads)
    └── ota_updates (model distribution)
```

---

## Column Indexes (Performance)

### Primary Keys (Clustered)
- All `*_id` columns are PKs (UUID or SERIAL)

### Foreign Key Indexes
```sql
-- persons
CREATE INDEX idx_persons_org ON persons(org_id);

-- embeddings (HNSW for vector, B-tree for FK)
CREATE INDEX embedding_idx ON embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_embeddings_person ON embeddings(person_id);

-- recognition_events (time-series)
CREATE INDEX idx_recognition_org ON recognition_events(org_id, timestamp DESC);
CREATE INDEX idx_recognition_camera ON recognition_events(camera_id);
CREATE INDEX idx_recognition_person ON recognition_events(person_id);
CREATE INDEX idx_recognition_org_risk ON recognition_events(org_id, risk_score);

-- audit_log (immutable chain)
CREATE INDEX idx_audit_time ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_person ON audit_log(person_id);

-- sessions (TTL cleanup)
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

-- model_versions (lookup)
CREATE INDEX idx_model_versions_name ON model_versions(name);
CREATE INDEX idx_model_versions_status ON model_versions(status);

-- ota_updates (status filter)
CREATE INDEX idx_ota_device ON ota_updates(device_id, status);

-- mfa_attempts (recent tries)
CREATE INDEX idx_mfa_attempts_user ON mfa_attempts(user_id, created_at);

-- bias_reports (org + date range)
CREATE INDEX idx_bias_reports_org ON bias_reports(org_id, report_date);
```

## Data Retention Policies

| Table | Retention | Notes |
|-------|-----------|-------|
| `audit_log` | 7 years | Immutable for compliance |
| `recognition_events` | 90 days (configurable) | Aggregated metrics kept longer |
| `sessions` | 30 days | Auto-cleaned by Celery task |
| `mfa_attempts` | 1 year | Security audit trail |
| `bias_reports` | Indefinite | Historical fairness tracking |
| `model_versions` | Indefinite | Version history (delete manually) |
| `embeddings` | Indefinite | Until person deletion (GDPR) |
| `consent_logs` | Indefinite | Legal requirement |

## Partitioning Strategy

### TimescaleDB Hypertable (Optional)
If TimescaleDB extension is installed, `recognition_events` can be converted to a hypertable:

```sql
SELECT create_hypertable('recognition_events', 'timestamp',
                         chunk_time_interval => INTERVAL '7 days',
                         if_not_exists => TRUE);
```

This自动 partitions by time (7-day chunks) for efficient time-series queries.

---

**Files:**
- Schema: `infra/init.sql`
- Migrations: `alembic/versions/001_initial_schema.py`
- ER Diagram source: `docs/database/er_diagram.md` (this file)
