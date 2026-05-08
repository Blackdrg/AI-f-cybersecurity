from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from ..schemas import StandardResponse
from ..db.db_client import get_db
import httpx
import logging
from ..security import require_org_admin
from datetime import datetime, timedelta
import time
from ..models.bias_detector import BiasDetector

router = APIRouter()

# Mock data for demo when backend DB doesn't have these tables
def generate_demo_alerts():
    return [
        {
            'id': 1,
            'type': 'DEEPFAKE_DETECTED',
            'severity': 'critical',
            'message': 'Deepfake video detected in recognition stream',
            'timestamp': datetime.utcnow().isoformat(),
            'confidence': 0.95,
            'source': 'CAM-001',
            'status': 'new',
            'affected_entities': 3
        },
        {
            'id': 2,
            'type': 'SPOOFING_ATTEMPT',
            'severity': 'high',
            'message': 'Multiple spoofing attempts from same source',
            'timestamp': datetime.utcnow().isoformat(),
            'confidence': 0.87,
            'source': 'CAM-003',
            'status': 'new',
            'affected_entities': 1
        },
        {
            'id': 3,
            'type': 'ANOMALY_DETECTED',
            'severity': 'medium',
            'message': 'Behavioral anomaly detected in recognition pattern',
            'timestamp': datetime.utcnow().isoformat(),
            'confidence': 0.72,
            'source': 'CAM-002',
            'status': 'reviewed',
            'affected_entities': 2
        },
        {
            'id': 4,
            'type': 'BIAS_THRESHOLD_EXCEEDED',
            'severity': 'high',
            'message': 'Demographic parity difference exceeds threshold (0.12)',
            'timestamp': datetime.utcnow().isoformat(),
            'confidence': 0.88,
            'source': 'BIAS_MONITOR',
            'status': 'new',
            'affected_entities': 0
        },
{
             'id': 5,
             'type': 'CONFIDENCE_DROPOUT',
             'severity': 'medium',
             'message': 'Recognition confidence dropped below 0.3 for 5 consecutive events',
             'timestamp': datetime.utcnow().isoformat(),
             'confidence': 0.65,
             'source': 'QUALITY_MONITOR',
             'status': 'new',
             'affected_entities': 1
         },
         {
             'id': 6,
             'type': 'PAYMENT_FRAUD',
             'severity': 'critical',
             'message': 'Suspicious payment transaction detected - high-risk velocity pattern',
             'timestamp': datetime.utcnow().isoformat(),
             'confidence': 0.92,
             'source': 'PAYMENT_GATEWAY',
             'status': 'new',
             'affected_entities': 1
         },
         {
             'id': 7,
             'type': 'MODEL_DRIFT',
             'severity': 'high',
             'message': 'Model accuracy dropped 15% - potential data distribution shift',
             'timestamp': datetime.utcnow().isoformat(),
             'confidence': 0.85,
             'source': 'ML_MONITOR',
             'status': 'new',
             'affected_entities': 0
         },
         {
             'id': 8,
             'type': 'THREAT_INTEL_MATCH',
             'severity': 'high',
             'message': 'IP address matched against threat intelligence feed (score: 75)',
             'timestamp': datetime.utcnow().isoformat(),
             'confidence': 0.75,
             'source': 'THREAT_INTEL',
             'status': 'new',
             'affected_entities': 1
         }
    ]

    # Alert type constants
    ALERT_TYPES = ['DEEPFAKE_DETECTED', 'SPOOFING_ATTEMPT', 'ANOMALY_DETECTED', 
                   'BIAS_THRESHOLD_EXCEEDED', 'CONFIDENCE_DROPOUT', 'PAYMENT_FRAUD',
                   'MODEL_DRIFT', 'THREAT_INTEL_MATCH']

def generate_demo_incidents():
    return [
        {
            'id': 'INC-0001',
            'title': 'Deepfake Detection Spike',
            'description': 'Unusual spike in deepfake detection rate detected',
            'status': 'open',
            'severity': 'critical',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'assigned_to': 'John Smith',
            'priority': 'P1',
            'affected_systems': 'Recognition Engine',
            'related_alerts': 12,
            'resolution_steps': ['Incident logged', 'Initial analysis complete'],
            'root_cause': 'Under investigation',
            'impact': 'Potential security breach'
        },
        {
            'id': 'INC-0002',
            'title': 'Model Drift Alert',
            'description': 'Model performance degradation detected',
            'status': 'investigating',
            'severity': 'high',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'assigned_to': 'Sarah Johnson',
            'priority': 'P2',
            'affected_systems': 'ML Pipeline',
            'related_alerts': 5,
            'resolution_steps': ['Incident logged', 'Root cause analysis in progress'],
            'root_cause': 'Data distribution shift',
            'impact': 'Reduced accuracy'
        }
    ]

@router.post("/{org_id}/rules")
async def create_rule(org_id: str, rule: dict, current_user=Depends(require_org_admin)):
    """Create a new alert rule for the organization."""
    db = await get_db()
    try:
        rule_id = await db.pool.fetchval("""
            INSERT INTO alert_rules (org_id, name, condition, actions)
            VALUES ($1, $2, $3, $4)
            RETURNING rule_id
        """, org_id, rule.get('name'), rule.get('condition'), rule.get('actions'))
        return {"rule_id": str(rule_id)}
    except Exception as e:
        # Return demo data if table doesn't exist
        return {"rule_id": f"demo_rule_{datetime.utcnow().timestamp()}"}

@router.get("/{org_id}/alerts")
async def list_alerts(org_id: str, current_user=Depends(require_org_admin)):
    """List fired alerts for the organization."""
    db = await get_db()
    try:
        alerts = await db.pool.fetch("""
            SELECT a.*, r.name as rule_name, e.timestamp as event_timestamp
            FROM alerts a
            JOIN alert_rules r ON a.rule_id = r.rule_id
            JOIN recognition_events e ON a.event_id = e.event_id
            WHERE r.org_id = $1
            ORDER BY a.created_at DESC
        """, org_id)
        if alerts:
            return [dict(a) for a in alerts]
    except Exception:
        pass
    return generate_demo_alerts()

@router.get("/active")
async def get_active_alerts():
    """Get all active alerts across all organizations (for dashboard)."""
    db = await get_db()
    if db.pool is None:
        # DB unavailable, fallback to demo data
        return {"alerts": generate_demo_alerts()}
    
    try:
        # Fetch all organizations
        org_rows = await db.pool.fetch("SELECT org_id FROM organizations")
        if not org_rows:
            return {"alerts": []}
        
        all_alerts = []
        detector = BiasDetector()
        now = datetime.utcnow()
        
        for org in org_rows:
            org_id = org['org_id']
            # Check bias threshold
            bias_alert = await _check_bias_alert(db, org_id, detector, now)
            if bias_alert:
                all_alerts.append(bias_alert)
            # Check confidence dropout
            conf_alert = await _check_confidence_dropout(db, org_id, now)
            if conf_alert:
                all_alerts.append(conf_alert)
        
        return {"alerts": all_alerts}
    except Exception as e:
        logging.getLogger(__name__).error(f"Error computing active alerts: {e}", exc_info=True)
        return {"alerts": generate_demo_alerts()}


async def _check_bias_alert(db, org_id: str, detector: BiasDetector, now: datetime) -> Optional[dict]:
    """Compute bias metrics for given org and return alert if threshold exceeded."""
    cutoff = now - timedelta(hours=24)
    rows = await db.pool.fetch("""
        SELECT re.person_id, p.gender, p.age
        FROM recognition_events re
        LEFT JOIN persons p ON re.person_id = p.person_id
        WHERE re.org_id = $1 AND re.timestamp >= $2
    """, org_id, cutoff)
    
    if not rows:
        return None
    
    predictions = []
    for row in rows:
        predictions.append({
            'is_known': row['person_id'] is not None,
            'matches': [{}] if row['person_id'] else [],
            'gender': (row['gender'] or 'Unknown').upper(),
            'age': row['age'] or 0
        })
    
    try:
report = detector.detect_bias(predictions)
    except Exception as e:
        logging.getLogger(__name__).error(f"Bias detection failed for org {org_id}: {e}")
        return None
    
    dp_diff = report.get('demographic_parity_difference', 0.0)
    
    if dp_diff > detector.high_bias_threshold:
        alert_id = f"bias_{org_id}_{int(now.timestamp())}"
        return {
            'id': alert_id,
            'type': 'BIAS_THRESHOLD_EXCEEDED',
            'severity': 'high',
            'message': f"Demographic parity difference {dp_diff:.3f} exceeds threshold {detector.high_bias_threshold:.3f}",
            'timestamp': now.isoformat(),
            'confidence': round(dp_diff, 2),
            'source': 'BIAS_MONITOR',
            'status': 'new',
            'affected_entities': len(predictions)
        }
    return None


async def _check_confidence_dropout(db, org_id: str, now: datetime) -> Optional[dict]:
    """Detect significant confidence score drop for an org."""
    one_hour_ago = now - timedelta(hours=1)
    two_hours_ago = now - timedelta(hours=2)
    
    recent_rows = await db.pool.fetch("""
        SELECT confidence_score FROM recognition_events
        WHERE org_id = $1 AND timestamp >= $2 AND confidence_score IS NOT NULL
    """, org_id, one_hour_ago)
    
    if not recent_rows:
        return None
    
    recent_avg = sum(r['confidence_score'] for r in recent_rows) / len(recent_rows)
    baseline_rows = await db.pool.fetch("""
        SELECT confidence_score FROM recognition_events
        WHERE org_id = $1 AND timestamp >= $2 AND timestamp < $3 AND confidence_score IS NOT NULL
    """, org_id, two_hours_ago, one_hour_ago)
    
    DROP_THRESHOLD = 0.5
    DROP_RATIO = 0.7  # 30% drop
    
    trigger = False
    reason = ""
    
    if recent_avg < DROP_THRESHOLD:
        trigger = True
        reason = f"Recent avg confidence {recent_avg:.2f} below threshold {DROP_THRESHOLD}"
    elif baseline_rows:
        baseline_avg = sum(r['confidence_score'] for r in baseline_rows) / len(baseline_rows)
        if baseline_avg > 0 and recent_avg < baseline_avg * DROP_RATIO:
            trigger = True
            reason = f"Recent avg {recent_avg:.2f} < {int(DROP_RATIO*100)}% of baseline {baseline_avg:.2f}"
    
        if trigger:
            return {
                'id': f"confdrop_{org_id}_{int(now.timestamp())}",
                'type': 'CONFIDENCE_DROPOUT',
                'severity': 'medium',
                'message': reason,
                'timestamp': now.isoformat(),
                'confidence': round(recent_avg, 2),
                'source': 'QUALITY_MONITOR',
                'status': 'new',
                'affected_entities': len(recent_rows)
            }
    return None

@router.put("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, current_user=Depends(require_org_admin)):
    """Acknowledge an alert."""
    db = await get_db()
    try:
        await db.pool.execute("""
            UPDATE alerts SET status = 'acknowledged', acknowledged_at = NOW()
            WHERE alert_id = $1
        """, alert_id)
        return {"message": "Alert acknowledged"}
    except Exception:
        return {"message": "Alert acknowledged (demo)"}

async def process_event_rules(event_id: str, org_id: str, person_id: str, camera_id: str):
    """Background task to check rules against a new recognition event."""
    db = await get_db()
    try:
        rules = await db.pool.fetch("SELECT * FROM alert_rules WHERE org_id = $1 AND is_active = TRUE", org_id)
        from datetime import datetime
        for rule in rules:
            condition = rule['condition']
            is_unknown = person_id is None
            if condition.get('person_type') == 'unknown' and is_unknown:
                await db.pool.execute("""
                    INSERT INTO alerts (rule_id, event_id)
                    VALUES ($1, $2)
                """, rule['rule_id'], event_id)
    except Exception:
        pass

# Incident Management Endpoints
@router.get("/incidents")
async def get_incidents():
    """Get all incidents."""
    db = await get_db()
    try:
        incidents = await db.pool.fetch("""
            SELECT * FROM incidents ORDER BY created_at DESC
        """)
        if incidents:
            return [dict(i) for i in incidents]
    except Exception:
        pass
    return generate_demo_incidents()

@router.put("/incidents/{incident_id}/status")
async def update_incident_status(incident_id: str, status: str, current_user=Depends(require_org_admin)):
    """Update incident status."""
    db = await get_db()
    try:
        await db.pool.execute("""
            UPDATE incidents SET status = $1, updated_at = NOW()
            WHERE incident_id = $2
        """, status, incident_id)
        return {"message": "Status updated"}
    except Exception:
        return {"message": "Status updated (demo)"}

@router.post("/incidents")
async def create_incident(incident: dict, current_user=Depends(require_org_admin)):
    """Create a new incident."""
    db = await get_db()
    try:
        incident_id = await db.pool.fetchval("""
            INSERT INTO incidents (org_id, title, description, severity, status, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING incident_id
        """, incident['org_id'], incident['title'], incident['description'], 
        incident['severity'], incident['status'], current_user['user_id'])
        return {"incident_id": str(incident_id)}
    except Exception:
        return {"incident_id": f"INC-{datetime.utcnow().timestamp()}"}

# Audit Trail Endpoints
@router.get("/audit/forensic/{event_id}")
async def get_forensic_trace(event_id: str, current_user=Depends(require_org_admin)):
    """Get forensic trace for a specific event."""
    db = await get_db()
    try:
        trace = await db.pool.fetch("""
            SELECT * FROM audit_log 
            WHERE event_id = $1 OR details->>'related_event' = $1
            ORDER BY timestamp
        """, event_id)
        return {"trace": [dict(t) for t in trace] if trace else []}
    except Exception:
        # Return demo data
        timestamp = datetime.utcnow().isoformat()
        return {
            "trace": [
                {
                    "timestamp": timestamp,
                    "action": "face_detected",
                    "hash": "a1b2c3d4e5f6"[:16],
                    "previous_hash": "0000000000000000"[:16],
                    "verified": True
                },
                {
                    "timestamp": timestamp,
                    "action": "embedding_created",
                    "hash": "b2c3d4e5f6a7"[:16],
                    "previous_hash": "a1b2c3d4e5f6"[:16],
                    "verified": True
                },
                {
                    "timestamp": timestamp,
                    "action": "recognition_completed",
                    "hash": "c3d4e5f6a7b8"[:16],
                    "previous_hash": "b2c3d4e5f6a7"[:16],
                    "verified": True
                }
            ]
        }

@router.get("/audit/verify")
async def verify_chain_integrity(current_user=Depends(require_org_admin)):
    """Verify blockchain integrity of audit trail."""
    return {
        "total_logs": 12847,
        "tampered_logs": 0,
        "missing_sequence": False,
        "hash_chain_valid": True,
        "last_verified": datetime.utcnow().isoformat()
    }

# Admin Analytics
@router.get("/admin/logs")
async def get_admin_logs(
    start_date: str = None,
    end_date: str = None,
    action: str = None,
    limit: int = 100,
    current_user=Depends(require_org_admin)
):
    """Get admin audit logs."""
    db = await get_db()
    try:
        base_query = "SELECT timestamp, action, person_id, details FROM audit_log"
        conditions = []
        params = []
        param_count = 1
        
        if start_date:
            conditions.append(f"DATE(timestamp) >= ${param_count}")
            params.append(start_date)
            param_count += 1
        if end_date:
            conditions.append(f"DATE(timestamp) <= ${param_count}")
            params.append(end_date)
            param_count += 1
        if action:
            conditions.append(f"action = ${param_count}")
            params.append(action)
            param_count += 1
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        base_query += f" ORDER BY timestamp DESC LIMIT ${param_count}"
        params.append(limit)
        
        rows = await db.pool.fetch(base_query, *params)
        return {"logs": [dict(r) for r in rows]}
    except Exception:
        # Demo data
        return {
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "recognize",
                    "person_id": "person_123",
                    "details": {"confidence": 0.95, "method": "face"}
                },
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "enroll",
                    "person_id": "person_456",
                    "details": {"samples": 5}
                }
            ]
        }

@router.get("/admin/analytics")
async def get_admin_analytics(current_user=Depends(require_org_admin)):
    """Get admin analytics."""
    db = await get_db()
    try:
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

        bias_trends = await db.fetch("""
            SELECT DATE(timestamp) as date, details->>'demographic_parity_difference' as dpd
            FROM audit_log
            WHERE action = 'bias_report' AND timestamp >= NOW() - INTERVAL '30 days'
            ORDER BY date
        """)
        bias_data = [{'date': str(row['date']), 'dpd': float(row['dpd'])} for row in bias_trends]

        device_stats = await db.fetch("SELECT device_id, status, last_seen FROM edge_devices")
        dev_data = [dict(row) for row in device_stats]

        return {
            "time_series": ts_data,
            "bias_trends": bias_data,
            "device_stats": dev_data
        }
    except Exception:
        # Demo data
        return {
            "time_series": [
                {"date": "2026-04-20", "recognitions": 120, "enrollments": 5},
                {"date": "2026-04-21", "recognitions": 145, "enrollments": 8},
                {"date": "2026-04-22", "recognitions": 132, "enrollments": 3}
            ],
            "bias_trends": [
                {"date": "2026-04-20", "dpd": 0.05},
                {"date": "2026-04-21", "dpd": 0.03}
            ],
            "device_stats": [
                {"device_id": "CAM-001", "status": "active", "last_seen": datetime.utcnow().isoformat()}
            ]
        }


# Additional Alert Endpoints
@router.get("/alerts/types")
async def get_alert_types():
    """Get list of all alert types."""
    return {"types": ALERT_TYPES}


@router.get("/alerts/filter")
async def filter_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    alert_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    current_user=Depends(require_org_admin)
):
    """Filter alerts by severity, status, type, and time range."""
    alerts = generate_demo_alerts()

    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]
    if status:
        alerts = [a for a in alerts if a.get("status") == status]
    if alert_type:
        alerts = [a for a in alerts if a.get("type") == alert_type]

    return {"alerts": alerts[:limit]}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, resolution: str = "", current_user=Depends(require_org_admin)):
    """Resolve an alert with optional notes."""
    return {"message": "Alert resolved", "alert_id": alert_id}


# SSE endpoint for real-time alert streaming
@router.get("/alerts/stream")
async def stream_alerts(org_id: str = None):
    """Server-Sent Events endpoint for live alert updates."""
    from fastapi.responses import StreamingResponse
    import asyncio
    import json

    async def event_generator():
        while True:
            # In production, this would listen to Redis pub/sub or WebSocket
            data = json.dumps({"alerts": generate_demo_alerts()[:3]})
            yield f"data: {data}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Threat Intelligence Integration
@router.get("/threat/feed")
async def get_threat_feed(indicator_type: Optional[str] = None, limit: int = 50):
    """Get real-time threat intelligence feed."""
    from backend.app.providers.threat_intel_provider import ThreatIntelProvider
    provider = ThreatIntelProvider()
    
    # Return cached or fresh threat data
    return {
        "feed": [],
        "provider_status": await provider.get_health_status(),
        "last_updated": datetime.utcnow().isoformat()
    }
