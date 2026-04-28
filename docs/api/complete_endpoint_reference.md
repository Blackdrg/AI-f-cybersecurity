# AI-f API Reference (Complete Endpoint Catalog)

**Base URL:** `https://api.example.com/api` (production)
**Staging:** `https://staging.example.com/api`
**Local:** `http://localhost:8000/api`

**Authentication:** All endpoints require JWT Bearer token except `/enroll`, `/recognize`

**Envelope:** Standard response format `{success, data, error}`

---

## Table of Contents

1. [Identity Management](#1-identity-management)
2. [Real-Time Streaming](#2-real-time-streaming)
3. [SaaS & Users](#3-saas--users)
4. [Organizations (Multi-Tenant)](#4-organizations-multi-tenant)
5. [Cameras & Devices](#5-cameras--devices)
6. [Admin & Operations](#6-admin--operations)
7. [Compliance (GDPR/CCPA/BIPA)](#7-compliance-gdprccpabipa)
8. [Analytics & AI](#8-analytics--ai)
9. [Billing (SaaS)](#9-billing-saas)
10. [Federated Learning & OTA](#10-federated-learning--ota)
11. [Consent Management](#11-consent-management)

---

## 1. Identity Management

### POST `/api/enroll`

Public endpoint — no authentication required.

**Purpose:** Enroll a new person with biometric data (face, optional voice/gait).

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | files[] | **Yes** | 3-5 face images (JPEG/PNG). Minimum 200×200px. |
| `name` | string | No | Person's display name |
| `consent` | boolean | **Yes** | BIPA consent obtained (must be true) |
| `camera_id` | string | No | Camera where enrollment occurred |
| `voice_files` | files[] | No | Voice samples for voice embedding |
| `gait_video` | file | No | Walking video for gait analysis |
| `age` | integer | No | Age (for analytics only, not used in matching) |
| `gender` | string | No | `male`/`female`/`non-binary` |
| `metadata` | JSON string | No | Arbitrary metadata (max 1KB) |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "person_id": "pers_abc123def456",
    "num_embeddings": 3,
    "example_embedding_id": "emb_xyz789",
    "confidence": 0.95,
    "message": "Enrollment successful – biometric template created"
  }
}
```

**Error codes:**
- `400`: Invalid image (unreadable, wrong format)
- `422`: No face detected in any image
- `429`: Rate limit (10 enrollments/day for free tier)
- `500`: Model loading error

**Notes:**
- Requires valid BIPA consent token (in future, will require `/consent/enroll` first)
- Creates entries in `persons`, `embeddings`, and `consent_logs` tables
- ZKP proof generated and stored in audit log

---

### POST `/api/recognize`

Public endpoint — recognizes faces in uploaded image.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | file | **Yes** | Query image containing face(s) |
| `top_k` | integer | No | Number of top matches (default: 1, max: 10) |
| `threshold` | float | No | Similarity threshold 0.0–1.0 (default: 0.6) |
| `camera_id` | string | No | Origin camera for audit |
| `enable_spoof_check` | boolean | No | Run anti-spoof detection (default: true) |
| `enable_emotion` | boolean | No | Extract emotion (default: true) |
| `enable_age_gender` | boolean | No | Extract age/gender (default: true) |
| `enable_behavior` | boolean | No | Extract behavioral signals (default: true) |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "faces": [
      {
        "face_box": [125, 340, 210, 280],
        "face_embedding_id": "emb_query_001",
        "matches": [
          {
            "person_id": "pers_abc123",
            "name": "John Doe",
            "score": 0.9473,
            "distance": 0.0527
          }
        ],
        "inference_ms": 89.5,
        "is_unknown": false,
        "spoof_score": 0.08,
        "reconstruction_confidence": 0.92,
        "emotion": {
          "happy": 0.85,
          "neutral": 0.10,
          "surprise": 0.05
        },
        "age": 32,
        "gender": "male",
        "behavior": {
          "fatigue": 0.12,
          "aggression": 0.03,
          "engagement": 0.85
        }
      }
    ]
  }
}
```

**Error codes:**
- `400`: No image provided or invalid format
- `422`: No face detected
- `429`: Rate limited (tier-based limits)
- `503`: Model service unavailable

---

### GET `/api/persons`

Requires `VIEW_IDENTITIES` permission.

**Purpose:** List enrolled persons (paginated).

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `page_size` | integer | 20 | Items per page (max 100) |
| `org_id` | UUID | (user's org) | Filter by organization |
| `search` | string | None | Text search on name |

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "persons": [
      {
        "person_id": "pers_001",
        "name": "John Doe",
        "age": 32,
        "gender": "male",
        "created_at": "2026-04-15T10:30:00Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 42
  }
}
```

---

### GET `/api/persons/{person_id}`

Requires `VIEW_IDENTITIES` permission.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "person_id": "pers_001",
    "name": "John Doe",
    "age": 32,
    "gender": "male",
    "embeddings": ["emb_001", "emb_002"],
    "consent_record": {
      "consent_record_id": "cons_abc123",
      "granted_at": "2026-04-15T10:25:00Z",
      "consent_text_version": "v1"
    },
    "created_at": "2026-04-15T10:30:00Z"
  }
}
```

---

### PUT `/api/persons/{person_id}`

Requires `EDIT_IDENTITY` permission.

**Request Body:**
```json
{
  "name": "Jane Doe",
  "age": 28,
  "gender": "female"
}
```

**Response:** Updated person object.

---

### DELETE `/api/persons/{person_id}`

Requires `DELETE_IDENTITY` permission.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "deleted": true,
    "person_id": "pers_001",
    "message": "Person and all associated data permanently deleted"
  }
}
```

**Note:** Triggers GDPR erasure — also deletes embeddings, audit logs (anonymized), and recognition events.

---

### POST `/api/identities/merge`

Requires `MERGE_IDENTITIES` permission.

**Purpose:** Merge duplicate person records.

**Request:**
```json
{
  "source_person_id": "pers_001",
  "target_person_id": "pers_002",
  "merge_reason": "duplicate_enrollment"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "merged_person_id": "pers_002",
    "source_deleted": true,
    "embeddings_merged": 5
  }
}
```

---

## 2. Real-Time Streaming

### WebSocket `/ws/recognize_stream`

**Query Parameters:**
- `top_k` (default: 1)
- `threshold` (default: 0.4)
- `camera_id` (optional)

**Message Format:** See [WebSocket Message Format Specification](./websocket_message_format.md)

**Connection Example (Python):**
```python
import asyncio, websockets, json, base64

async def stream():
    async with websockets.connect(
        "ws://localhost:8000/ws/recognize_stream?top_k=1&threshold=0.4&camera_id=cam_01"
    ) as ws:
        while True:
            frame = capture_camera()
            b64 = base64.b64encode(frame).decode()
            await ws.send(json.dumps({
                "type": "frame",
                "data": b64,
                "timestamp": datetime.utcnow().isoformat(),
                "frame_number": frame_num
            }))
            result = await ws.recv()
            print(json.loads(result))

asyncio.run(stream())
```

---

### POST `/api/stream_recognize`

**Legacy endpoint** — use WebSocket for new integrations.

Accepts multi-camera batch and returns synchronized results.

---

### POST `/api/video_recognize` (Doc: endpoint actually `/recognize_video`)

> **Note:** Current implementation endpoint: `POST /api/recognize_video`
> (Should be renamed or documented as-is).

**Purpose:** Batch recognition on video file.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `video` | file | **Yes** | Video file (MP4, AVI, MOV) |
| `top_k` | integer | No | Number of matches (default: 1) |
| `threshold` | float | No | Recognition threshold (default: 0.4) |
| `camera_id` | string | No | Associated camera ID |
| `frame_interval` | integer | No | Process every N frames (default: 30 ≈ 1 fps @ 30fps video) |

**Response (200 OK):**
```json
[
  {
    "faces": [
      {
        "face_box": [100, 200, 150, 180],
        "matches": [
          {
            "person_id": "pers_001",
            "name": "John Doe",
            "score": 0.92
          }
        ],
        "inference_ms": 95.3,
        "is_unknown": false
      }
    ]
  },
  {
    "faces": [...]
  }
]
```

**Error Codes:**
- `400`: Invalid video format or unreadable
- `422`: Video has no valid frames with faces
- `500`: Decoding error (unsupported codec)

**Notes:**
- Processes at most 1 frame per `frame_interval` to limit compute
- Results array length equals number of processed frames
- Each frame yields 0+ face detections

---

## 3. SaaS & Users

### POST `/api/users`

Self-registration (no auth required).

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "Jane Doe",
  "password": "securePassword123!"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "user_id": "usr_xyz123",
    "email": "user@example.com",
    "name": "Jane Doe",
    "subscription_tier": "free"
  }
}
```

---

### GET `/api/users/me`

Requires authentication.

**Response:** Current user profile.

---

### PUT `/api/users/me`

Update current user profile.

---

### DELETE `/api/users/me`

GDPR right to erasure (account deletion).

---

### POST `/api/auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "def50200..."
  }
}
```

**JWT Claims (access_token):**
```json
{
  "user_id": "usr_abc123",
  "role": "operator",
  "org_id": "org_org123",
  "subscription_tier": "pro",
  "iat": 1714125600,
  "exp": 1714129200,
  "mfa_verified": true  // only if MFA passed
}
```

---

### POST `/api/auth/refresh`

Refresh access token using refresh token.

---

## 4. Organizations (Multi-Tenant)

### GET `/api/organizations`

List organizations (admin only).

---

### POST `/api/organizations`

Requires `super_admin` role.

---

### GET `/api/orgs/{org_id}/members`

Requires `VIEW_MEMBERS` permission.

**Response:**
```json
{
  "members": [
    {
      "user_id": "usr_001",
      "email": "user@example.com",
      "name": "John Doe",
      "role": "operator",
      "joined_at": "2026-04-10T08:00:00Z"
    }
  ]
}
```

---

### POST `/api/orgs/{org_id}/members`

Requires `MANAGE_MEMBERS` permission.

**Request:**
```json
{
  "user_id": "usr_002",
  "role": "viewer"
}
```

---

## 5. Cameras & Devices

### POST `/api/{org_id}/cameras`

Requires `MANAGE_CAMERAS` (admin/operator).

**Request Body:**
```json
{
  "name": "Main Entrance Camera",
  "rtsp_url": "rtsp://cam-ip:554/stream",
  "location": "Building A, Main Entrance"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "camera_id": "cam_abc123",
    "org_id": "org_xyz",
    "name": "Main Entrance Camera",
    "rtsp_url": "rtsp://cam-ip:554/stream",
    "location": "Building A, Main Entrance",
    "status": "offline",
    "created_at": "2026-04-28T12:00:00Z"
  }
}
```

**RTSP URL Format:**
```
rtsp://<username>:<password>@<camera-ip>:<port>/<path>
```
- Default port: 554
- Path varies by camera: `/live`, `/stream1`, `/video`, etc.
- Username/password required for authenticated cameras
- Example: `rtsp://admin:secret@192.168.1.100:554/live`

**Supported Codecs:**
- H.264 (preferred)
- H.265 (if supported by GPU)
- MJPEG (fallback, higher bandwidth)

**Frame Extraction Pipeline:**
1. RTSP stream opened via OpenCV `VideoCapture`
2. Frames decoded at configured FPS (default: 10 FPS)
3. BGR → RGB conversion
4. Face detection on each frame
5. Results published to Redis pub/sub for downstream consumers

---

### GET `/api/{org_id}/cameras`

List all cameras for organization.

---

### POST `/api/{org_id}/cameras/test-connection`

Test RTSP URL validity (without saving).

**Request:**
```json
{
  "rtsp_url": "rtsp://192.168.1.100:554/live"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Stream connection verified"
}
```

---

### POST `/api/{org_id}/cameras/{camera_id}/start`

Start RTSP stream ingestion.

**Status Code:** 204 No Content on success.

---

### GET `/api/{org_id}/cameras/{camera_id}/status`

Get camera health and stream info.

**Response:**
```json
{
  "camera_id": "cam_001",
  "status": "streaming",
  "fps": 10.2,
  "frames_processed": 15420,
  "last_frame_at": "2026-04-28T12:05:00Z",
  "uptime_seconds": 86400
}
```

---

### GET `/api/{org_id}/cameras/status`

Get status of all organization cameras.

---

## 6. Admin & Operations

### GET `/api/admin/metrics`

Requires `VIEW_METRICS` permission.

**Response:**
```json
{
  "recognition_count": 15432,
  "enroll_count": 892,
  "avg_latency_ms": 145.2,
  "false_accepts": 0,
  "false_rejects": 12,
  "index_size": 89345
}
```

---

### GET `/api/admin/logs`

Requires `VIEW_AUDIT_LOGS` permission.

**Query Parameters:**
- `start_date` (YYYY-MM-DD)
- `end_date` (YYYY-MM-DD)
- `action` (e.g., `recognize`, `enroll`)
- `limit` (default: 100, max: 1000)

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2026-04-28T10:00:00Z",
      "action": "recognize",
      "person_id": "pers_001",
      "details": {
        "camera_id": "cam_01",
        "confidence": 0.947,
        "threshold": 0.6,
        "model_version": "v2.1.0"
      }
    }
  ]
}
```

---

### POST `/api/admin/index/rebuild`

Requires `MANAGE_INDEX` permission.

Rebuilds HNSW vector index (non-blocking background job).

**Response:**
```json
{
  "message": "Index rebuild started",
  "task_id": "task_abc123"
}
```

---

### GET `/api/admin/policies`

Requires `MANAGE_POLICIES`.

List all active policy rules.

**Response:**
```json
{
  "total_rules": 5,
  "default_effect": "deny",
  "rules": [
    {
      "rule_id": "admin_enroll_only",
      "name": "Admin Enroll Only",
      "effect": "allow",
      "priority": 100,
      "enabled": true,
      "resources": ["enroll"],
      "subject_types": ["admin"]
    }
  ]
}
```

---

### PUT `/api/admin/policies/{policy_id}`

Enable/disable or update policy rule.

---

## 7. Compliance (GDPR/CCPA/BIPA)

### GET `/api/compliance/export/{person_id}`

GDPR Article 20 — Right to data portability.

**Response:**
```json
{
  "export_timestamp": "uuid-here",
  "data": {
    "person": { /* person record */ },
    "embeddings": [ /* all biometric vectors */ ],
    "recognition_events": [ /* all recognition history */ ],
    "audit_log": [ /* all audit entries affecting this person */ ]
  }
}
```

**Formats:** JSON, CSV, or Parquet (Accept header controls).

---

### DELETE `/api/compliance/delete/{person_id}`

GDPR Article 17 — Right to erasure.

**Response:**
```json
{
  "message": "Data successfully erased from all systems",
  "person_id": "pers_001",
  "zkp_proof": { /* ZKP of deletion for audit */ }
}
```

**What gets deleted:**
- Person record (`persons`)
- All embeddings (`embeddings`)
- Recognition events (`recognition_events`)
- Audit logs anonymized (kept for legal retention)

**What gets retained (anonymized):**
- Audit log entries (person_id set to `anon_deleted_pers_001`)
- Aggregated analytics (no PII)

---

### GET `/api/compliance/status`

Returns compliance posture.

**Response:**
```json
{
  "gdpr_compliant": true,
  "ccpa_compliant": true,
  "bipa_compliant": true,
  "soc2_type_ii": true,
  "features": [
    "Right to Erasure",
    "Data Portability",
    "Consent Vault",
    "Immutable Audit Chain",
    "ZKP Verification"
  ]
}
```

---

### GET `/api/audit/verify`

Verify integrity of the entire hash chain.

**Query Parameters:**
- `start_id` (optional, default: all)
- `end_id` (optional)

**Response:**
```json
{
  "total_logs": 154321,
  "chain_valid": true,
  "broken_links": [],
  "invalid_proofs": 0,
  "verified_at": "2026-04-28T12:10:00Z"
}
```

---

## 8. Analytics & AI

### GET `/api/analytics`

Requires `VIEW_ANALYTICS` permission.

**Response:**
```json
{
  "time_series": [
    {
      "date": "2026-04-27",
      "recognitions": 1543,
      "enrollments": 12,
      "unique_persons": 892
    }
  ],
  "bias_trends": [
    {
      "date": "2026-04-27",
      "demographic_parity_difference": 0.02,
      "equalized_odds_difference": 0.015
    }
  ],
  "device_stats": [
    {
      "device_id": "edge_001",
      "status": "online",
      "last_seen": "2026-04-28T12:05:00Z"
    }
  ],
  "top_recognitions": [
    {
      "person_id": "pers_001",
      "name": "John Doe",
      "count": 142
    }
  ]
}
```

---

### GET `/api/analytics/bias-trends`

Requires `VIEW_BIAS_REPORTS` permission.

**Response:**
```json
{
  "bias_trends": [
    {
      "report_date": "2026-04-28",
      "demographic_parity_difference": 0.018,
      "equalized_odds_difference": 0.012,
      "false_positive_rate": {
        "male": 0.001,
        "female": 0.0012
      }
    }
  ],
  "overall_fairness": "good"
}
```

---

### POST `/api/ai/assistant`

Requires authentication.

**Request:**
```json
{
  "query": "How does facial recognition handle aging?"
}
```

**Response:**
```json
{
  "query": "How does facial recognition handle aging?",
  "response": "Facial recognition systems experience some degradation over time...",
  "model_used": "gpt-4",
  "sources": ["docs/faq/aging.md"]
}
```

**Note:** Premium users (enterprise tier) get GPT-4; others get GPT-3.5-turbo.

---

### GET `/api/explanations/{explanation_id}`

Requires `VIEW_EXPLANATIONS` permission.

**Purpose:** Retrieve XAI (Explainable AI) decision breakdown for a specific recognition.

**Response:**
```json
{
  "explanation_id": "exp_abc123",
  "person_id": "pers_001",
  "event_id": "event_xyz789",
  "method": "SHAP",
  "feature_importance": [
    {
      "feature": "left_eye_region",
      "importance": 0.23,
      "contribution": "positive"
    },
    {
      "feature": "nose_bridge",
      "importance": 0.18,
      "contribution": "positive"
    }
  ],
  "confidence_score": 0.947,
  "decision_threshold": 0.6,
  "verification_zkp": { /* proof that explanation matches decision */ }
}
```

---

## 9. Billing (SaaS)

### GET `/api/plans`

Public endpoint.

**Response:**
```json
{
  "plans": [
    {
      "plan_id": "free",
      "name": "Free Starter",
      "price": 0.00,
      "features": [
        "Basic Recognition",
        "10 Enrollments",
        "Standard Support"
      ],
      "limits": {
        "recognitions": 100,
        "enrollments": 10
      }
    },
    {
      "plan_id": "pro",
      "name": "Pro Developer",
      "price": 29.00,
      "features": [
        "Advanced Recognition",
        "1000 Enrollments",
        "Priority Support",
        "Public Enrichment"
      ],
      "limits": {
        "recognitions": 10000,
        "enrollments": 1000
      }
    },
    {
      "plan_id": "enterprise",
      "name": "Enterprise Scale",
      "price": 199.00,
      "features": [
        "Unlimited Recognition",
        "Infinite Enrollments",
        "24/7 Dedicated Support",
        "Advanced Analytics",
        "ZKP Security"
      ],
      "limits": {
        "recognitions": -1,
        "enrollments": -1
      }
    }
  ]
}
```

---

### POST `/api/subscriptions`

Requires authentication.

**Request:**
```json
{
  "plan_id": "pro"
}
```

**Response:**
```json
{
  "subscription_id": "sub_abc123",
  "user_id": "usr_001",
  "plan_id": "pro",
  "status": "active",
  "created_at": "2026-04-28T12:00:00Z",
  "expires_at": null
}
```

---

### GET `/api/subscriptions/me`

Current user's subscription.

---

### POST `/api/payments/create-session`

Create Stripe Checkout session.

**Request:**
```json
{
  "plan_id": "pro"
}
```

**Response:**
```json
{
  "session_url": "https://checkout.stripe.com/pay/..."
}
```

Redirect user to `session_url` to complete payment.

---

### POST `/api/payments/webhook`

Stripe webhook endpoint (idempotent).

**Events handled:**
- `checkout.session.completed` — activate subscription
- `invoice.payment_failed` — downgrade to free, notify user
- `customer.subscription.deleted` — cancel subscription
- `invoice.payment_succeeded` — extend subscription

**Response:** `200 OK` with `{"status": "success"}`

---

### GET `/api/usage/current`

Current billing period usage.

**Response:**
```json
{
  "user_id": "usr_001",
  "period_start": "2026-04-01T00:00:00Z",
  "period_end": "2026-05-01T00:00:00Z",
  "recognitions_used": 542,
  "recognitions_limit": 10000,
  "enrollments_used": 5,
  "enrollments_limit": 1000
}
```

---

## 10. Federated Learning & OTA

### POST `/api/federated/update`

Secure aggregation endpoint for federated learning clients.

**Authentication:** Service token (not user JWT)

**Request (encrypted):**
```json
{
  "round_id": "fl_round_001",
  "client_id": "org_123",
  "encrypted_gradients": {
    "ciphertext": "...",
    "nonce": "...",
    "tag": "..."
  },
  "num_samples": 1250,
  "model_version": "v1.0",
  "zkp_proof": { /* proof of correct gradient computation */ }
}
```

**Response:**
```json
{
  "status": "accepted",
  "round_id": "fl_round_001",
  "aggregation_id": "agg_xyz789"
}
```

---

### GET `/api/models/download`

OTA model download for edge devices.

**Query Parameters:**
- `version` (required): Model version string
- `platform` (optional): `linux`, `android`, `ios`

**Response:** Binary model file (application/octet-stream)

**Headers:**
```
Content-Disposition: attachment; filename="face-embedder-v2.1.0.onnx"
X-Model-Version: v2.1.0
X-Model-Checksum-SHA256: abc123...
X-Model-Size-Bytes: 52428800
```

---

## 11. Consent Management

### POST `/api/consent/enroll`

Record biometric consent (BIPA).

**Request:**
```json
{
  "consent_text_version": "v1",
  "purpose": "authentication",
  "valid_until": "2027-04-28T00:00:00Z",
  "include_zkp": true
}
```

**Response:**
```json
{
  "consent_id": "consent_abc123",
  "consent_token": "sha256:...",
  "consent_text_version": "v1",
  "granted_at": "2026-04-28T12:15:00Z",
  "expires_at": "2027-04-28T00:00:00Z",
  "zkp_proof": { /* ZKP of consent for audit */ },
  "message": "Consent recorded successfully"
}
```

**Usage:** Present `consent_token` when calling `/api/enroll`.

---

### GET `/api/consent/verify?token=...`

Verify consent token validity.

**Response:**
```json
{
  "valid": true,
  "consent_id": "consent_abc123",
  "subject_id": "usr_001",
  "granted_at": "2026-04-28T12:15:00Z",
  "expires_at": "2027-04-28T00:00:00Z",
  "purpose": "authentication"
}
```

---

### POST `/api/consent/revoke`

Revoke previously given consent.

**Request:**
```json
{
  "consent_id": "consent_abc123",
  "reason": "No longer need authentication feature"
}
```

**Response:**
```json
{
  "revoked": true,
  "consent_id": "consent_abc123",
  "revoked_at": "2026-04-28T14:30:00Z",
  "message": "Consent revoked successfully"
}
```

**Note:** Does not delete already-collected biometric data; separate deletion request required.

---

### GET `/api/consent/history?subject_id=...`

Get consent history for a subject.

---

## Common Error Responses

All endpoints may return:

**401 Unauthorized:**
```json
{
  "success": false,
  "error": "Invalid or expired token"
}
```

**403 Forbidden:**
```json
{
  "success": false,
  "error": "Insufficient permissions"
}
```

**429 Too Many Requests:**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "retry_after": 45,
    "limit": 100,
    "window": "1 minute"
  }
}
```

**Headers (on 429):**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1714129200
X-RateLimit-Window: 60
```

---

## Rate Limits by Tier

| Endpoint Category | Free | Pro | Enterprise |
|-------------------|------|-----|------------|
| **/api/recognize** | 50/min | 500/min | 2000/min |
| **/api/enroll** | 10/day | 100/day | 500/day |
| **/api/admin/*** | 5/min | 50/min | 200/min |
| **/api/stream/** | N/A | 10 concurrent | 50 concurrent |

**Burst:** All tiers allow 2× sustained rate for 10 seconds.

---

## SDKs

| Language | Package | Status |
|----------|---------|--------|
| **Python** | `ai-f-sdk` | ✅ Production |
| **Node.js** | `ai-f-sdk` | ✅ Production |
| **Go** | `github.com/owner/ai-f-backend/sdk/go/ai_f_sdk` | ✅ Production (v2.0+) |

---

## OpenAPI Specification

Full OpenAPI 3.0 spec available at:
- **Production:** `https://api.example.com/api/openapi.json`
- **Local:** `http://localhost:8000/api/openapi.json`
- **Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)
- **ReDoc:** `http://localhost:8000/redoc`

Spec size: ~122 KB, covering 200+ endpoints with full schema definitions.
