# Admin Guide - LEVI-AI Enterprise

## 1. System Architecture
LEVI-AI is a containerized biometric engine consisting of:
- **FastAPI Backend**: Core logic and ML inference.
- **PostgreSQL + pgvector**: Secure storage of biometric embeddings.
- **Redis**: Real-time queue and cache.
- **React UI**: Administrative dashboard.

## 2. Deployment
Use the `scripts/install_enterprise.sh` script for automated deployment on Ubuntu systems.
Ensure the following ports are open:
- 8000: API
- 3000: Dashboard
- 5432: Database (Internal only)

## 3. Security Management
- **Audit Logs**: Access the `audit_log` table to view hash-chained forensic logs.
- **Rate Limiting**: Configure limits in `policy_engine.py`.
- **Secrets**: Rotate `ENCRYPTION_KEY` every 90 days.

## 4. Maintenance
- **Backups**: Run `scripts/ops/backup_postgres.sh` daily.
- **ML Drift**: Monitor accuracy via `scripts/validation/accuracy_report.py`.
- **Scaling**: Increase `num_shards` in `main.py` if managing > 100k identities.

## 5. Support Workflow
Admins can manage support tickets via the `/api/support/tickets` endpoint. Always reply to "High" priority tickets within 4 hours.
