# TODO - Critical Fixes for AI-F Backend Test Suite

## Phase 1: Test Suite Configuration (Critical)
- [ ] 1.1 Create pytest.ini with PYTHONPATH=backend
- [ ] 1.2 Check and fix role name "user" → "viewer" in conftest.py
- [ ] 1.3 Fix spoof detector call signature (add missing args)
- [ ] 1.4 Run tests to verify fixes

## Phase 2: Backend Bug Fixes
- [ ] 2.1 Fix async/await bug in rate_limit.py
- [ ] 2.2 Implement in-memory fallback for rate limiter (global state)
- [ ] 2.3 Audit await patterns across middleware

## Phase 3: Database & Integration Tests
- [ ] 3.1 Set up SQLite → PostgreSQL configuration
- [ ] 3.2 Add integration tests for missing API routers
- [ ] 3.3 Add Stripe/OpenAI mocks for CI

## Progress Tracking
- Phase 1 started: [ ]
- Phase 2 started: [ ]
- Phase 3 started: [ ]
