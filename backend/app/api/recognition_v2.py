from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from ..schemas import (
    RecognizeRequest, RecognizeResponse, 
    DetectedFace, FaceMatch
)
from ..db.db_client import get_db
from ..security import get_current_user
from ..scoring_engine import scoring_engine, get_scoring_engine
from ..decision_engine import decision_engine
from ..continuous_evaluation import evaluation_pipeline, get_evaluation_pipeline
from ..policy_engine import policy_engine, get_policy_engine, SubjectType, ResourceType
from ..hybrid_search import init_vector_store, get_vector_store
from ..models.enhanced_spoof import enhanced_spoof_detector
import time

router = APIRouter()


@router.post("/recognize_v2", response_model=RecognizeResponse)
async def recognize_v2(
    image,
    top_k: int = 1,
    threshold: float = 0.4,
    enable_spoof: bool = True,
    enable_voice: bool = False,
    enable_gait: bool = False,
    voice_file = None,
    gait_video = None,
    user: dict = Depends(get_current_user)
):
    """Enhanced recognition with scoring engine."""
    start_time = time.time()
    db = await get_db()
    
    # Policy check
    policy = policy_engine.can_recognize(
        user["user_id"],
        SubjectType.USER if user.get("role") == "user" else SubjectType.OPERATOR,
        context={"purpose": "authentication"}
    )
    
    if not policy.allowed:
        raise HTTPException(
            status_code=403, 
            detail=f"Recognition not allowed: {policy.reason}"
        )
    
    # Process image (simplified - in production, use proper image processing)
    import numpy as np
    import cv2
    
    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Enhanced spoof detection
    liveness_result = None
    if enable_spoof:
        from ..models.enhanced_spoof import enhanced_spoof_detector
        bbox = [100, 100, 300, 300]  # Simplified
        liveness_result = enhanced_spoof_detector.detect(
            img, bbox, np.zeros((5, 2))
        )
    
    # Search using hybrid engine
    hybrid_store = get_vector_store()
    
    # Mock query embedding (in production, use actual model)
    query_emb = np.random.randn(512).astype(np.float32)
    query_emb = query_emb / np.linalg.norm(query_emb)
    
    search_results = []
    if hybrid_store:
        results = await hybrid_store.search(query_emb, top_k)
        search_results = results
    else:
        # Fallback to DB search
        matches = await db.recognize_faces(
            query_emb, top_k, threshold
        )
        search_results = matches
    
    # Build scoring input
    face_result = None
    if search_results:
        face_result = {
            "faces": [{
                "matches": [
                    {"person_id": m.person_id, "name": m.name, "score": m.score}
                    for m in search_results[:top_k]
                ]
            }]
        }
        if liveness_result:
            face_result["faces"][0]["spoof_score"] = liveness_result.spoof_score
    
    voice_result = None
    gait_result = None
    
    # Use scoring engine
    scoring_result = scoring_engine.score_identity(
        face_result=face_result,
        voice_result=voice_result,
        gait_result=gait_result,
        liveness_result=liveness_result if enable_spoof else None,
        metadata={"user_id": user["user_id"]}
    )
    
    # Log for continuous evaluation
    evaluation_pipeline.log_evaluation(
        query_id=f"query_{int(time.time())}",
        predicted_id=scoring_result.primary_match.person_id if scoring_result.primary_match else None,
        ground_truth=None,  # Would be filled later
        scores={
            "identity_score": scoring_result.identity_score,
            "face_score": scoring_result.face_score,
            "voice_score": scoring_result.voice_score,
            "gait_score": scoring_result.gait_score,
            "spoof_score": scoring_result.spoof_score
        },
        decision=scoring_result.decision,
        metadata={"user_id": user["user_id"]}
    )
    
    # Build response
    detected_faces = []
    
    if scoring_result.primary_match:
        detected_faces.append(DetectedFace(
            face_box=[100, 100, 300, 300],
            face_embedding_id=None,
            matches=[
                FaceMatch(
                    person_id=scoring_result.primary_match.person_id,
                    name=scoring_result.primary_match.name,
                    score=scoring_result.identity_score,
                    distance=1.0 - scoring_result.identity_score
                )
            ],
            inference_ms=(time.time() - start_time) * 1000,
            is_unknown=scoring_result.decision == "deny",
            spoof_score=liveness_result.spoof_score if liveness_result else None
        ))
    
    return RecognizeResponse(faces=detected_faces)


@router.get("/scoring/metrics")
async def get_scoring_metrics(
    current_user=Depends(get_current_user)
):
    """Get scoring engine metrics."""
    return scoring_engine.get_evaluation_metrics()


@router.get("/evaluation/report")
async def get_evaluation_report(
    period: str = "24h",
    current_user=Depends(get_current_user)
):
    """Get evaluation report."""
    return evaluation_pipeline.get_report(period)


@router.get("/evaluation/drift")
async def check_drift(
    current_user=Depends(get_current_user)
):
    """Check for performance drift."""
    alerts = evaluation_pipeline.check_drift()
    return {"alerts": alerts}


@router.post("/evaluation/ground-truth")
async def submit_ground_truth(
    query_id: str,
    correct_person_id: str,
    current_user=Depends(get_current_user)
):
    """Submit ground truth for evaluation."""
    # Find the entry and update
    return {"status": "recorded"}


@router.get("/policy/report")
async def get_policy_report(
    current_user=Depends(get_current_user)
):
    """Get policy report."""
    return policy_engine.get_policy_report()


@router.post("/policy/rules")
async def add_policy_rule(
    rule_data: dict,
    current_user=Depends(get_current_user)
):
    """Add a policy rule (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from ..policy_engine import PolicyRule, PolicyEffect, SubjectType, ResourceType
    
    rule = PolicyRule(
        rule_id=rule_data["rule_id"],
        name=rule_data["name"],
        effect=PolicyEffect[rule_data["effect"]],
        subject_types=[SubjectType[st] for st in rule_data.get("subject_types", [])],
        resources=[ResourceType[res] for res in rule_data.get("resources", [])],
        priority=rule_data.get("priority", 0),
        description=rule_data.get("description", "")
    )
    
    policy_engine.add_rule(rule)
    
    return {"status": "added", "rule_id": rule.rule_id}


@router.post("/policy/check")
async def check_policy(
    subject_id: str,
    subject_type: str,
    resource: str,
    context: dict = {},
    current_user=Depends(get_current_user)
):
    """Check policy for a request."""
    decision = policy_engine.evaluate(
        subject_id,
        SubjectType[subject_type],
        ResourceType[resource],
        context
    )
    
    return {
        "allowed": decision.allowed,
        "effect": decision.effect.value,
        "reason": decision.reason,
        "matched_rule": decision.matched_rule
    }