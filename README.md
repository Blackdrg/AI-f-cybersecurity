proceed
# Face Recognition System

A production-capable, consent-first face recognition service built with FastAPI, InsightFace, and PostgreSQL+pgvector.

## Features
- Face enrollment with consent logging
- Real-time recognition from images
- Admin management and metrics
- Privacy-focused: no raw images stored without consent, encrypted embeddings
- Dockerized for easy deployment

## SaaS Features
- **User Management**: Account creation, authentication, and profile management
- **Subscription Plans**: Free, Pro, and Enterprise tiers with different limits
- **Usage Tracking**: Monitor recognition and enrollment usage per month
- **AI Assistant**: Get help with face recognition tasks using GPT models
- **Support System**: Create and manage support tickets
- **Payment Processing**: Stripe integration for subscription payments
- **Special Access**: daredevil0101a@gmail.com has automatic Enterprise access

### Subscription Plans
- **Free**: 100 recognitions, 10 enrollments/month
- **Pro**: 10,000 recognitions, 1,000 enrollments/month - $29.99/month
- **Enterprise**: Unlimited usage - Free for daredevil0101a@gmail.com

## Architecture
- **Backend**: FastAPI with InsightFace for detection/embedding
- **Database**: PostgreSQL with pgvector for embeddings
- **UI**: React TypeScript for enrollment, recognition, admin, subscriptions, and AI assistant
- **Infra**: Docker-compose for POC, k8s for production

## Setup
1. Clone repo
2. Run POC: `./scripts/run_poc.sh`
3. Access UI at http://localhost

## API
See `docs/api_spec.yaml` for OpenAPI spec including all SaaS endpoints.

## SaaS API Endpoints
- `POST /api/users` - Create user account
- `GET /api/users/me` - Get current user info
- `GET /api/plans` - List subscription plans
- `POST /api/subscriptions` - Create subscription
- `GET /api/usage/current` - Get current usage
- `POST /api/ai/assistant` - Query AI assistant
- `POST /api/support/tickets` - Create support ticket
- `POST /api/payments/create-session` - Create payment session

## Switching Vector Store
To use Milvus instead of pgvector:
1. Update `infra/docker-compose.yml` to include Milvus service
2. Modify `backend/app/db/db_client.py` to use Milvus client
3. Rebuild and redeploy

## Privacy
- Consent required for enrollment
- Embeddings encrypted at rest
- Audit logs for all actions
- GDPR-compliant deletion

## Evaluation
Run `python evaluate.py` with labeled dataset to tune thresholds.

## Environment Limitations and Setup Notes

### Windows Development Issues
This project was developed on Windows 11, which presented several challenges:

- **GCC Version**: Windows GCC 6.3.0 is incompatible with numpy/opencv compilation. InsightFace requires Docker for Windows environments.
- **Docker**: Docker Desktop must be running for full POC testing.
- **MSVC++ Build Tools**: Required for some Python packages, but not installed in this environment.

### Recommended Development Environment
For full functionality testing, use:
- **Linux/macOS** with Docker
- **Docker Desktop** on Windows with WSL2
- **Python virtual environment** with proper C++ build tools

### Partial Verification Completed
- ✅ Core Python dependencies (FastAPI, Uvicorn, Pytest, Pydantic, Cryptography)
- ✅ React UI build successful
- ✅ Project structure and code implementation complete
- ❌ Full backend testing blocked by numpy/opencv installation
- ❌ POC docker-compose blocked by Docker daemon not running
- ❌ Model evaluation blocked by InsightFace dependency

### Full Testing Instructions
To complete verification in a proper environment:

1. **Install Docker and ensure daemon is running**
2. **Run POC**:
   ```bash
   ./scripts/run_poc.sh
   ```
3. **Run tests**:
   ```bash
   cd backend && pytest tests/ -v
   ```
4. **Evaluate accuracy**:
   ```bash
   python evaluate.py --dataset /path/to/validation/data
