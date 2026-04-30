# API Integration Guide (cURL)

This guide provides working cURL examples to test the AI-f API locally or in production.

## Prerequisites

1. **Start the services:**
   ```bash
   cd infra
   docker-compose up -d
   ```

2. **Get access token** (see Authentication section below)

## Base URL

| Environment | URL |
|-------------|-----|
| Local | http://localhost:8000 |
| Production | https://api.your-domain.com |

---

## Authentication

### Login to get JWT Token

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "password"}'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**Save the token:**
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Use token from response
```

### Use Token in Requests

All authenticated requests need the Authorization header:
```bash
-H "Authorization: Bearer $TOKEN"
```

---

## Health Check

### Basic Health
```bash
curl -s http://localhost:8000/health
```

**Response:** `{"status":"healthy"}`

### Detailed Health
```bash
curl -s http://localhost:8000/api/health | jq
```

---

## Core Endpoints

### 1. Enroll a Person

```bash
curl -X POST "http://localhost:8000/api/enroll" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "images=@/path/to/photo1.jpg" \
  -F "name=John Doe" \
  -F "consent=true" \
  -F 'metadata={"role": "employee", "department": "engineering"}'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "person_id": "pers_abc123",
    "message": "Person enrolled successfully",
    "embedding_count": 1
  }
}
```

### 2. Recognize a Face

```bash
curl -X POST "http://localhost:8000/api/recognize" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "image=@/path/to/query.jpg" \
  -F "top_k=5" \
  -F "threshold=0.7"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "faces": [
      {
        "face_box": [100, 100, 200, 200],
        "matches": [
          {
            "person_id": "pers_abc123",
            "name": "John Doe",
            "confidence": 0.947
          }
        ],
        "is_unknown": false,
        "spoof_score": 0.02
      }
    ],
    "processing_time_ms": 145,
    "request_id": "req_xyz789"
  }
}
```

### 3. List All Persons

```bash
curl -s "http://localhost:8000/api/persons?limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 4. Get Person Details

```bash
curl -s "http://localhost:8000/api/persons/pers_abc123" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 5. Update Person

```bash
curl -X PUT "http://localhost:8000/api/persons/pers_abc123" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Updated", "metadata": {"department": "sales"}}'
```

### 6. Delete Person

```bash
curl -X DELETE "http://localhost:8000/api/persons/pers_abc123" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Analytics

### Get Dashboard Metrics

```bash
curl -s "http://localhost:8000/api/analytics?timeframe=24h" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Get Risk Metrics

```bash
curl -s "http://localhost:8000/api/analytics/risk-metrics" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Admin Operations

### List API Keys

```bash
curl -s "http://localhost:8000/api/keys" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Create API Key

```bash
curl -X POST "http://localhost:8000/api/keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Key"}' | jq
```

### List Organizations

```bash
curl -s "http://localhost:8000/api/organizations" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Get System Status

```bash
curl -s "http://localhost:8000/api/admin/systems/status" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## WebSocket (Real-time)

### Connect to Live Stream

```javascript
// JavaScript WebSocket client
const ws = new WebSocket('ws://localhost:8000/ws/recognize_stream');

ws.onopen = () => {
  console.log('Connected to stream');
  // Send subscription message
  ws.send(JSON.stringify({
    action: 'subscribe',
    camera_ids: ['cam_lobby', 'cam_entrance']
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Recognition:', data);
};
```

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "details": {}
}
```

### Common Error Codes

| Code | Meaning | HTTP Status |
|------|---------|------------|
| `AUTH_REQUIRED` | Authentication required | 401 |
| `AUTH_INVALID_TOKEN` | Invalid/expired token | 401 |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 |
| `BIO_NO_FACE` | No face detected | 422 |
| `BIO_QUALITY_LOW` | Image quality too low | 422 |
| `PERMISSION_DENIED` | Insufficient permissions | 403 |

---

## Complete Test Sequence

```bash
# 1. Login
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "password"}' | \
  jq -r '.data.access_token')

echo "Token: $TOKEN"

# 2. Check health
curl -s http://localhost:8000/health
echo ""

# 3. Enroll a person (use a real image path)
curl -X POST "http://localhost:8000/api/enroll" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "images=@backend/test_image.jpg" \
  -F "name=Test Person" \
  -F "consent=true"
echo ""

# 4. List persons
curl -s "http://localhost:8000/api/persons" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.persons | length'
echo " persons in system"

# 5. Get analytics
curl -s "http://localhost:8000/api/analytics?timeframe=24h" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.recognition_count'
echo " recognitions in last 24h"
```

---

## Rate Limits

| Tier | /recognize | /enroll | /admin |
|------|------------|---------|--------|
| Free | 50/min | 10/min | 5/min |
| Pro | 500/min | 100/min | 50/min |
| Enterprise | 2000/min | 500/min | 200/min |

---

## Next Steps

- [SDK Documentation](./SDK_README.md)
- [Webhook Verification](./webhook_verification.md)
- [API Reference](./API_REFERENCE.md)
