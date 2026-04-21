#!/usr/bin/env python3
"""
Integration Test Suite for Face Recognition System

Tests:
1. Database connectivity
2. Model loading (with fallbacks)
3. Enrollment API
4. Recognition API
5. Scoring Engine
6. Policy Engine
7. Continuous Evaluation
8. Hybrid Search (when FAISS available)
"""

import asyncio
import sys
import numpy as np
from datetime import datetime


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None


async def test_database():
    """Test database connectivity."""
    result = TestResult("Database Connectivity")
    try:
        from app.db.db_client import get_db
        db = await get_db()
        if db and db.pool:
            result.passed = True
            print("✓ Database connected")
        else:
            result.error = "No pool"
            print("✗ Database not connected")
    except Exception as e:
        result.error = str(e)
        print(f"✗ Database error: {e}")
    return result


def test_models():
    """Test model loading."""
    result = TestResult("Model Loading")
    try:
        from app.models.face_detector import FaceDetector
        from app.models.face_embedder import FaceEmbedder
        from app.models.spoof_detector import SpoofDetector
        
        detector = FaceDetector()
        embedder = FaceEmbedder()
        
        # Test with mock image
        test_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        faces = detector.detect_faces(test_img, check_spoof=False)
        
        result.passed = True
        print(f"✓ Models loaded ({len(faces)} faces detected)")
    except Exception as e:
        result.error = str(e)
        print(f"✗ Model loading error: {e}")
    return result


def test_scoring_engine():
    """Test identity scoring engine."""
    result = TestResult("Scoring Engine")
    try:
        from app.scoring_engine import scoring_engine, IdentityScoringEngine
        
        # Test with mock results
        scoring_result = scoring_engine.score_identity(
            face_result={"faces": [{"matches": [{"person_id": "test_001", "name": "Test User", "score": 0.85}]}]},
            liveness_result={"spoof_score": 0.1}
        )
        
        if scoring_result.identity_score > 0:
            result.passed = True
            print(f"✓ Scoring engine working (score: {scoring_result.identity_score:.2f})")
        else:
            result.error = "No score"
    except Exception as e:
        result.error = str(e)
        print(f"✗ Scoring error: {e}")
    return result


def test_policy_engine():
    """Test policy engine."""
    result = TestResult("Policy Engine")
    try:
        from app.policy_engine import policy_engine, SubjectType, ResourceType
        
        decision = policy_engine.evaluate(
            "user_001",
            SubjectType.USER,
            ResourceType.RECOGNIZE
        )
        
        if decision.allowed is not None:
            result.passed = True
            print(f"✓ Policy engine working (allowed: {decision.allowed})")
        else:
            result.error = "No decision"
    except Exception as e:
        result.error = str(e)
        print(f"✗ Policy error: {e}")
    return result


def test_evaluation():
    """Test continuous evaluation."""
    result = TestResult("Continuous Evaluation")
    try:
        from app.continuous_evaluation import evaluation_pipeline
        
        evaluation_pipeline.log_evaluation(
            query_id="test_001",
            predicted_id="person_001",
            ground_truth="person_001",
            scores={
                "identity_score": 0.85,
                "face_score": 0.9,
                "voice_score": 0.0,
                "gait_score": 0.0,
                "spoof_score": 0.1
            },
            decision="allow",
            metadata={"environment": "office"}
        )
        
        report = evaluation_pipeline.get_report(period="1h")
        result.passed = True
        print(f"✓ Evaluation pipeline working")
    except Exception as e:
        result.error = str(e)
        print(f"✗ Evaluation error: {e}")
    return result


def test_hybrid_search():
    """Test hybrid search (FAISS if available)."""
    result = TestResult("Hybrid Search")
    try:
        from app.hybrid_search import HybridSearchEngine
        
        engine = HybridSearchEngine(num_shards=2)
        
        # Add test embeddings
        test_emb = np.random.randn(512).astype(np.float32)
        test_emb = test_emb / np.linalg.norm(test_emb)
        
        # Note: In production, this would use actual embedding
        # For now just test initialization
        metrics = engine.get_metrics()
        
        result.passed = True
        print(f"✓ Hybrid search initialized (type: {metrics.index_type})")
    except Exception as e:
        result.error = str(e)
        print(f"✗ Hybrid search error: {e}")
    return result


async def test_api_endpoints():
    """Test main API endpoints."""
    result = TestResult("API Endpoints")
    try:
        from app.main import app
        
        # Get routes
        routes = [r.path for r in app.routes]
        
        required_routes = [
            "/api/enroll",
            "/api/recognize",
            "/api/admin/metrics",
            "/api/users",
            "/api/usage/current",
            "/api/plans"
        ]
        
        missing = [r for r in required_routes if r not in routes]
        
        if not missing:
            result.passed = True
            print(f"✓ API endpoints registered ({len(routes)} routes)")
        else:
            result.error = f"Missing: {missing}"
            print(f"✗ Missing routes: {missing}")
    except Exception as e:
        result.error = str(e)
        print(f"✗ API error: {e}")
    return result


async def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Face Recognition System - Integration Tests")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print()
    
    results = []
    
    # Run tests
    print("Running tests...")
    print("-" * 40)
    
    results.append(await test_database())
    results.append(test_models())
    results.append(test_scoring_engine())
    results.append(test_policy_engine())
    results.append(test_evaluation())
    results.append(test_hybrid_search())
    results.append(await test_api_endpoints())
    
    print()
    print("=" * 60)
    print("Results Summary")
    print("=" * 60)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    for r in results:
        status = "✓ PASS" if r.passed else "✗ FAIL"
        print(f"  {status}: {r.name}")
        if r.error:
            print(f"       Error: {r.error}")
    
    print()
    if passed == total:
        print("✓ All integration tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)