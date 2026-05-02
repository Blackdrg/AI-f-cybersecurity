# AI-f (LEVI-AI) Project Update

## Recent Work Completed

### TypeScript Migration
- Converted `apiEnhanced.js` to TypeScript (`apiEnhanced.ts`)
- Verified 0 remaining `.js` files in frontend source (excluding config files)
- All frontend pages and components are now in TypeScript

### E2E Testing Framework
- Installed and configured Cypress
- Created test directory structure and added test scripts to `package.json`
- Written comprehensive E2E tests covering:
  - User login flow
  - Person enrollment flow (with file upload and consent)
  - Face recognition flow (webcam/upload)
  - Subscription purchase flow (Stripe integration)

### Billing System Improvements
- Fixed `SubscriptionPlans.tsx` to use proper Stripe integration via `@stripe/stripe-js`
- Added Stripe JS libraries to dependencies
- Added missing Stripe webhook endpoint tests (`backend/tests/test_payments_webhook.py`)
- Added payment processing tests (`backend/tests/test_payments.py`)
- Verified existing billing and webhook test coverage

### TEE Implementation Ready for AWS Deployment
- Defined sensitive workloads (face embeddings, biometric data, matching pipeline, encryption keys, audit logs, identity/auth decisions)
- Selected AWS Nitro Enclaves as TEE platform
- Created enclave application:
  - `enclave/app.py` - Secure face matching service using VSOCK communication
  - `enclave/Dockerfile` - Builds enclave image with necessary dependencies
  - `enclave/BUILD_AND_RUN.md` - Detailed build and deployment instructions
- Modified backend APIs to route sensitive operations to enclave:
  - `backend/app/api/recognize.py` - Routes face matching to enclave
  - `backend/app/api/enroll.py` - Routes secure embedding storage to enclave
- Created development mock (`backend/enclave_mock.py`) for local testing

## Current Status

### Frontend
- **Language**: TypeScript 4.9.5
- **Framework**: React 18.2.0 with Material-UI 7.3.4
- **State Management**: React Context API (AuthContext)
- **API Communication**: Enhanced Axios service with error handling and retry logic
- **Stripe Integration**: `@stripe/stripe-js` and `@stripe/react-stripe-js` for secure payment processing

### Backend
- **Language**: Python 3.12
- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL 15 with pgvector and Row-Level Security (RLS)
- **Authentication**: JWT with distributed revocation (Redis-backed)
- **Security**: MFA/TOTP, OAuth2 (Azure AD, Google), ethical governor, policy engine
- **ML Infrastructure**: ONNX Runtime, PyTorch pipelines, FAISS + pgvector hybrid search
- **Services**: WebSocket manager, Redis Pub/Sub, gRPC server, Celery queues

### Infrastructure
- **Containerization**: Docker (development and production)
- **Orchestration**: Kubernetes (EKS/GKE) ready with Helm charts
- **Infrastructure as Code**: Terraform (AWS)
- **Monitoring**: Prometheus + Grafana, Alertmanager, Sentry error tracking
- **Scaling**: HPA autoscaling (3 → 50 pods)

### Testing
- **Unit Tests**: pytest for backend components (billing, payments, webhooks)
- **E2E Tests**: Cypress for critical user flows
- **Test Coverage**: Improved for billing, webhook, and payment systems

## Known Limitations
- TEE implementation requires AWS account with Nitro Enclaves support for full deployment
- Performance benchmarks for TEE integration not yet measured
- Some compliance certifications (SOC 2 Type II, ISO 27001) are in progress
- Air-gapped deployment not yet validated

## Next Steps
1. Deploy TEE implementation in AWS Nitro Enclaves environment
2. Implement data flow hardening (encryption before enclave transfer)
3. Implement key management (AWS KMS with attestation-based release)
4. Implement remote attestation for enclave verification
5. Conduct performance validation with enclave integration
6. Apply security hardening and validate against side-channel attacks
7. Achieve compliance certifications through external audits

## Repository Structure
```
AI-f/
├── backend/                 # FastAPI backend
│   ├── app/                 # Application code
│   ├── enclave/             # TEE enclave application (AWS Nitro Enclaves)
│   ├── tests/               # Unit and integration tests
│   ├── infra/               # Infrastructure as code (Terraform, Helm, Docker)
│   └── requirements.txt     # Python dependencies
├── ui/                      # Frontend application
│   └── react-app/           # React TypeScript application
│       ├── src/             # Source code (all TypeScript)
│       ├── cypress/         # E2E tests
│       ├── package.json     # Node.js dependencies and scripts
│       └── tsconfig.json    # TypeScript configuration
├── docs/                    # Documentation
└── README.md                # This file
```

## How to Run
### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd ui/react-app
npm install
npm start
```

### E2E Tests
```bash
cd ui/react-app
npm run cypress:open   # Open Cypress test runner
npm run cypress:run    # Run tests in headless mode
```

## License
MIT

## Contact
For questions or support, please refer to the project documentation.