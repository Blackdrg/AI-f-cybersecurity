# Developer Experience Audit Fix Plan

Based on the DX Audit Report (Score: 2/10), this document tracks fixes to achieve DX score of 8/10.

---

## Audit Issues & Status

### Setup Clarity (Target: 8/10)

| Issue | Status | Fix |
|-------|--------|-----|
| PyTorch version doesn't exist | ✅ FIXED | Changed to torch>=2.0.0,<2.5.0 |
| Rate limiter crashes | ✅ FIXED | Fixed async/sync mismatch |
| No working demo credentials | 🔧 FIX | Add seeded demo user in DB + docs |
| No working curl sequence | 🔧 FIX | Add working curl guide to README |

### API Usability (Target: 7/10) 

| Issue | Status | Fix |
|-------|--------|-----|
| Auth contradiction /enroll, /recognize | ✅ FIXED | Clear auth requirements in docs |
| OpenAPI spec not committed | 🔧 FIX | Generate and commit openapi.json |
| No Postman collection | 🔧 FIX | Expand postman_collection.json |
| No API playground docs | 🔧 FIX | Document /docs endpoint |

### Integration Readiness (Target: 7/10)

| Issue | Status | Fix |
|-------|--------|-----|
| Go SDK incomplete | 🔧 FIX | Complete go/ai_f_sdk/client.go |
| Python SDK issues | 🔧 FIX | Fix issues in python/ai_f_sdk/client.py |
| Node.js SDK stub | 🔧 FIX | Expand nodejs/index.js |
| No webhook verification | 🔧 FIX | Add webhook example to docs |

### Missing Schemas (Target: 8/10)

| Issue | Status | Fix |
|-------|--------|-----|
| Admin schemas missing | 🔧 FIX | Document /api/admin/* endpoints |
| Analytics schemas missing | 🔧 FIX | Document /api/analytics/* endpoints |
| Federated schemas missing | 🔧 FIX | Document /api/federated/* endpoints |
| Alert schemas missing | 🔧 FIX | Document /api/alerts/* endpoints |

### Missing Examples (Target: 8/10)

| Issue | Status | Fix |
|-------|--------|-----|
| No end-to-end curl | 🔧 FIX | Add curl sequence to README |
| No Postman working | 🔧 FIX | Fix collection variables |
| No integration guide | 🔧 FIX | Add working walkthrough |

---

## Fix Implementation Plan

### Phase 1: Demo Credentials & Quick Start (Priority: HIGH)

1. **Create demo seed data**:
   - Add SQL script in `backend/scripts/seed_demo.sql`
   - Create demo users with different roles
   - Document credentials in README

2. **Working curl sequence**:
   - Add complete curl example to README
   - Include: login → enroll → recognize → logout

### Phase 2: SDK Completeness (Priority: HIGH)

1. **Fix Python SDK** (`backend/sdk/python/ai_f_sdk/client.py`):
   - Fix syntax errors (list brackets)
   - Add all missing methods
   - Add proper error handling

2. **Expand Node.js SDK** (`backend/sdk/nodejs/index.js`):
   - Add enroll method
   - Add person management methods
   - Add analytics methods

3. **Complete Go SDK** (`backend/sdk/go/ai_f_sdk/client.go`):
   - Implement REST client methods
   - Add proper error handling

### Phase 3: API Documentation (Priority: MEDIUM)

1. **Commit OpenAPI spec**:
   - Generate from running server
   - Save to `docs/openapi.json`
   - Reference in README

2. **Expand Postman collection**:
   - Add all 30+ endpoints
   - Fix variable handling
   - Add auth flow

3. **Add webhook example**:
   - Create `docs/webhook_verification.md`
   - Show HMAC signature verification

### Phase 4: Working Integration Guide (Priority: MEDIUM)

1. **Add curl walkthrough** to README:
   ```bash
   # 1. Login
   curl -X POST http://localhost:8000/api/auth/login \
     -d "email=demo@example.com&password=password"
   
   # 2. Enroll
   curl -X POST http://localhost:8000/api/enroll \
     -H "Authorization: Bearer $TOKEN" \
     -F "images=@photo.jpg" \
     -F "name=John Doe" \
     -F "consent=true"
   
   # 3. Recognize  
   curl -X POST http://localhost:8000/api/recognize \
     -H "Authorization: Bearer $TOKEN" \
     -F "image=@test.jpg"
   ```

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `backend/scripts/seed_demo.sql` | CREATE | Seed demo data |
| `backend/sdk/python/ai_f_sdk/client.py` | FIX | Python SDK fixes |
| `backend/sdk/nodejs/index.js` | EXPAND | Node.js SDK |
| `backend/sdk/go/ai_f_sdk/client.go` | COMPLETE | Go SDK |
| `docs/openapi.json` | CREATE | API spec |
| `docs/webhook_verification.md` | CREATE | Webhook example |
| `README.md` | UPDATE | Add curl guide |
| `postman_collection.json` | EXPAND | Full collection |

---

## Verification Commands

After fixes, verify with:

```bash
# 1. Start services
cd infra && docker-compose up -d

# 2. Seed demo data
docker-compose exec -T postgres psql -U postgres -d face_recognition < backend/scripts/seed_demo.sql

# 3. Test curl sequence
./scripts/test_curl_sequence.sh

# 4. Verify SDKs work
cd backend/sdk/python && python -c "from ai_f_sdk.client import AIFClient; print('SDK OK')"
cd backend/sdk/nodejs && node -e "const AIF = require('./index.js'); console.log('SDK OK')"
```

---

## Target DX Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Setup clarity | 4/10 | 8/10 |
| API usability | 3/10 | 7/10 |
| Integration readiness | 2/10 | 7/10 |
| Missing schemas | 0/10 | 8/10 |
| Missing examples | 2/10 | 8/10 |
| **Overall DX** | **2/10** | **8/10** |
