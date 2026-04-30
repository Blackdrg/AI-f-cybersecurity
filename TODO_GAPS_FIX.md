# GAPS Fix Plan

## GAP 3: 77.3% Test Failure - CI/CD Fixes

### Issues Identified:
1. Tests lacking proper authentication setup
2. Missing test fixtures and database mocking
3. API tests not using correct TestClient pattern

### Fix Plan:
- Fix backend/test_integration.py to use proper test client with auth
- Add conftest.py with pytest fixtures for authentication
- Ensure all tests can run independently

## GAP 6: Spoof Detector Test Signature Mismatch

### Issues Identified:
1. Tests expect 'method' key but it's mapped from spoof_type
2. Some tests expect different number of returned keys
3. The 3-arg signature vs 1-arg backward compatibility

### Fix Plan:
- Fix EnhancedSpoofDetector to always include 'method' key in result
- Add backward compatibility notes in docstring
- Update tests to handle both 1-arg and 3-arg calls properly

## GAP 10: Federated Learning Non-Functional

### Issues Identified:
1. require_admin blocks client registration (should be require_auth for register)
2. No actual edge clients - all mock data
3. Missing database persistence
4. Async run_round() called without await in API

### Fix Plan:
- Change require_admin to require_auth for /register endpoint
- Add client registration with proper auth
- Add database persistence for federated learning tables
- Fix async/await in the federated_learning API
- Add proper Celery task integration for federated rounds

## Files to Edit:
1. backend/tests/test_integration.py - Fix CI/CD tests
2. backend/app/models/enhanced_spoof.py - Fix signature/return values
3. backend/app/api/federated_learning.py - Fix auth and async issues
4. backend/app/federated_learning.py - Add persistence methods
5. Create backend/tests/conftest.py - Add test fixtures
