# AI-F Critical Gaps Fix TODO
Breakdown of approved plan into steps. Progress tracked here.

## 1. System Stability [x]
- [x] Create backend/requirements-cpu.txt (faiss-cpu/torch-cpu)
- [x] Update backend/Dockerfile (multi-stage, HEALTHCHECK, GPU variant)
- [x] Create backend/tests/conftest.py (db/stripe/openai/redis mocks)
- [x] Fix enhanced_spoof.py signature compatibility (already good with 'method' key)
- [ ] `cd backend && pip install -r requirements-cpu.txt && pytest -v --cov --cov-fail-under=95`

## 2. Production Deployment [ ]
- [ ] Extend .github/workflows/backend-ci.yml (add UI/deploy stages)
- [ ] Update infra/helm/ai-f/values.yaml (dev/staging/prod envs, monitoring)

## 3. Test Quality [ ]
- [ ] Enhance backend/run_full_suite.py (95% cov, GPU matrix)
- [ ] Update backend/pytest.ini (add markers if needed)

## 4. Packaging/Distribution [ ]
- [ ] Create scripts/setup.sh (one-command Docker/helm)
- [ ] Create infra/docker-compose.full.yml (unified services)
- [ ] Create docs/DEPLOY.md (guide + health checks)
- [ ] Add /healthz endpoint to backend/app/main.py

## Verification [ ]
- [ ] `bash scripts/setup.sh`
- [ ] `helm install ai-f infra/helm/ai-f/ --dry-run`
- [ ] Full CI run in GitHub Actions

*Updated after each step.*
