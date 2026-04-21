from fastapi import APIRouter, HTTPException, Form, Query, Depends
from ..db.db_client import get_db
from ..schemas import PersonResponse, RevokeRequest, DeleteResponse, MetricsResponse, ConsentVaultRequest, BiasReport, LogsResponse, LogEntry, ModelVersion, OTADownload, AnalyticsResponse
from ..security import require_admin, require_operator, require_auth
from ..metrics import recognition_count, enroll_count, recognition_latency, false_accepts, false_rejects, index_size
from ..models.bias_detector import BiasDetector
from typing import List
from datetime import datetime

router = APIRouter()


@router.get("/status")
async def get_status():
    return {"status": "admin service running", "version": "1.0.0"}


@router.get("/persons/{person_id}", response_model=PersonResponse)
async def get_person(person_id: str, user: dict = Depends(require_admin)):
    db = await get_db()
    person = await db.get_person(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return PersonResponse(**person)


@router.post("/persons/{person_id}/revoke")
async def revoke_person(person_id: str, request: RevokeRequest, user: dict = Depends(require_admin)):
    # Mark for deletion; in production, implement soft delete
    # For POC, just log
    return {"message": "Revoke logged", "person_id": person_id}


@router.delete("/persons/{person_id}", response_model=DeleteResponse)
async def delete_person(person_id: str, user: dict = Depends(require_admin)):
    db = await get_db()
    deleted = await db.delete_person(person_id)
    return DeleteResponse(deleted=deleted, message="Person deleted")


@router.post("/index/rebuild")
async def rebuild_index(user: dict = Depends(require_admin)):
    # Rebuild ANN index; for pgvector, may not be needed, but placeholder
    return {"message": "Index rebuilt"}


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(user: dict = Depends(require_admin)):
    # Aggregate metrics; in production, query Prometheus
    return MetricsResponse(
        recognition_count=int(recognition_count._value.get()),
        enroll_count=int(enroll_count._value.get()),
        avg_latency_ms=recognition_latency._sum.get() / recognition_latency._count.get() if recognition_latency._count.get() > 0 else 0,
        false_accepts=int(false_accepts._value.get()),
        false_rejects=int(false_rejects._value.get()),
        index_size=int(index_size._value.get())
    )


@router.post("/consent_vault")
async def manage_consent_vault(request: ConsentVaultRequest, user=Depends(require_auth)):
    db = await get_db()
    user_id = user['user_id']
    if request.action == 'grant':
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO consent_vault (user_id, biometric_type, granted) 
                VALUES ($1, $2, TRUE)
                ON CONFLICT (user_id, biometric_type) DO UPDATE SET granted = TRUE
            """, user_id, request.biometric_type)
        return {"message": "Consent granted"}
    elif request.action == 'revoke':
        async with db.pool.acquire() as conn:
            await conn.execute("UPDATE consent_vault SET granted = FALSE WHERE user_id = $1 AND biometric_type = $2", user_id, request.biometric_type)
        return {"message": "Consent revoked"}
    elif request.action == 'view':
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT biometric_type, granted FROM consent_vault WHERE user_id = $1", user_id)
        return {"consents": [dict(row) for row in rows]}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


@router.get("/bias_report", response_model=BiasReport)
async def get_bias_report(user=Depends(require_operator)):
    db = await get_db()
    async with db.pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM audit_log WHERE action = 'recognize' ORDER BY timestamp DESC LIMIT 1000")
        recent_recognitions = [dict(row) for row in rows]
    bias_detector = BiasDetector()
    bias_metrics = bias_detector.detect_bias(recent_recognitions)
    return BiasReport(**bias_metrics)


@router.post("/feedback")
async def submit_feedback(
    person_id: str = Form(...),
    recognition_id: str = Form(...),
    correct_person_id: str = Form(...),
    confidence_score: float = Form(...),
    feedback_type: str = Form(...),
    user: dict = Depends(require_admin)
):
    db = await get_db()
    success = await db.submit_feedback(person_id, recognition_id, correct_person_id, confidence_score, feedback_type)
    return {"message": "Feedback submitted", "success": success}


@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    start_date: str = Query(
        None, description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(None, description="End date in YYYY-MM-DD format"),
    action: str = Query(
        None, description="Filter by action (e.g., 'recognize', 'enroll')"),
    limit: int = Query(100, description="Maximum number of logs to return"),
    user: dict = Depends(require_admin)
):
    db = await get_db()
    base_query = "SELECT timestamp, action, person_id, details FROM audit_log"
    conditions = []
    params = []
    
    if start_date:
        conditions.append(f"DATE(timestamp) >= ${len(params)+1}")
        params.append(start_date)
    if end_date:
        conditions.append(f"DATE(timestamp) <= ${len(params)+1}")
        params.append(end_date)
    if action:
        conditions.append(f"action = ${len(params)+1}")
        params.append(action)
    
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
    base_query += f" ORDER BY timestamp DESC LIMIT ${len(params)+1}"
    params.append(limit)
    
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(base_query, *params)
    logs = [LogEntry(timestamp=str(row['timestamp']), action=row['action'],
                     person_id=row['person_id'], details=row['details']) for row in rows]
    return LogsResponse(logs=logs)


@router.post("/models/upload")
async def upload_model(model: ModelVersion, user: dict = Depends(require_admin)):
    db = await get_db()
    version_id = model.version_id
    async with db.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO model_versions (version_id, model_data, description)
            VALUES ($1, $2, $3)
        """, version_id, model.model_data, model.description)
    return {"message": "Model uploaded", "version_id": version_id}


@router.get("/models/download")
async def download_model(request: OTADownload, user: dict = Depends(require_admin)):
    db = await get_db()
    async with db.pool.acquire() as conn:
        model = await conn.fetchrow("SELECT model_data FROM model_versions WHERE version_id = $1", request.model_version)
        if not model:
            raise HTTPException(status_code=404, detail="Model version not found")
        await conn.execute("UPDATE edge_devices SET model_version = $1 WHERE device_id = $2", request.model_version, request.device_id)
    return {"model_data": model['model_data'].hex()}


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(user: dict = Depends(require_admin)):
    db = await get_db()
    # Time-series data: daily recognitions/enrollments
    time_series = await db.fetch("""
        SELECT DATE(timestamp) as date, action, COUNT(*) as count
        FROM audit_log
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(timestamp), action
        ORDER BY date
    """)
    ts_data = []
    for row in time_series:
        ts_data.append({
            'date': str(row['date']),
            'recognitions': row['count'] if row['action'] == 'recognize' else 0,
            'enrollments': row['count'] if row['action'] == 'enroll' else 0
        })

    # Bias trends: recent bias reports
    bias_trends = await db.fetch("""
        SELECT DATE(timestamp) as date, details->>'demographic_parity_difference' as dpd
        FROM audit_log
        WHERE action = 'bias_report' AND timestamp >= NOW() - INTERVAL '30 days'
        ORDER BY date
    """)
    bias_data = [{'date': str(row['date']), 'dpd': float(row['dpd'])}
                 for row in bias_trends]

    # Device stats
    device_stats = await db.fetch("SELECT device_id, status, last_seen FROM edge_devices")
    dev_data = [dict(row) for row in device_stats]

    return AnalyticsResponse(time_series=ts_data, bias_trends=bias_data, device_stats=dev_data)
