# TODO - Implementation Plan

## GAP 6: Spoof Detector Test Signature Fix
- [x] Read and analyze current test file
- [x] Read enhanced_spoof.py to understand detect() signature
- [ ] Update test_spoof_detection.py to use 3-arg detect() calls
- [ ] Add fallback handling in detect() for backward compatibility

## GAP 3: CI/CD and Test Infrastructure Fix
- [ ] Create proper test fixtures in conftest.py
- [ ] Fix test role assignments (user → viewer)
- [ ] Fix async/await issues in tests
- [ ] Mock external service dependencies

## GAP 10: Federated Learning Fix
- [ ] Update test endpoints in test_federated_learning.py
- [ ] Fix Pydantic v2 method (.dict() → .model_dump())
- [ ] Add proper client registration tests
- [ ] Fix model upload/download tests

## Verification
- [ ] Run pytest to verify fixes
- [ ] Update TODO_CRITICAL_GAPS.md with completion status
