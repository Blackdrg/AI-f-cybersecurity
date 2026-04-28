# Rate Limiting & Throttling

## Overview

AI-f implements **multi-tier rate limiting** at multiple layers:

1. **NGINX Ingress:** Global per-IP burst limit (L7)
2. **FastAPI Middleware:** Per-user/organization sliding window (Redis-backed)
3. **Database Connection Pool:** Hard limit on concurrent DB connections

All rate limit responses include standardized headers for client visibility.

---

## Architecture

```
Client Request → NGINX (100 r/s IP limit) → FastAPI (per-user limit) → Redis (sliding window) → Endpoint
                                                                        ↓
                                                              X-RateLimit-* headers on response
```

---

## Limit Matrix

### By Subscription Tier

| Tier | Global RPM | Recognitions/min | Enrollments/day | Admin API/min | WebSocket Streams |
|------|-----------|------------------|-----------------|---------------|-------------------|
| **Free** | 100 | 50 | 10 | 5 | 1 |
| **Pro** | 1,000 | 500 | 100 | 50 | 10 |
| **Enterprise** | 5,000 | 2,000 | 500 | 200 | 50 |

**RPM = Requests per minute (rolling window)**

### Endpoint-Specific Limits

| Endpoint Pattern | Free | Pro | Enterprise | Window |
|------------------|------|-----|------------|--------|
| `POST /api/recognize` | 50 | 500 | 2,000 | 1 min |
| `POST /api/enroll` | 10/day | 100/day | 500/day | 24h |
| `GET /api/persons/*` | 100 | 500 | 2,000 | 1 min |
| `POST /api/admin/*` | 5 | 50 | 200 | 1 min |
| `WS /ws/recognize_stream` | 1 stream | 10 streams | 50 streams | concurrent |
| `GET /api/analytics` | 10 | 50 | 200 | 1 min |

**Burst Allowance:** 2× sustained rate for 10 seconds (burst bucket)

---

## Implementation Details

### Redis Sorted Set Algorithm

Uses **sliding window log** with Redis sorted sets for accuracy:

```python
# Key: "rate_limit:{user_id}"
ZADD key {timestamp: timestamp}  # Add request timestamp
ZREMRANGEBYSCORE key 0 (now - window_seconds)  # Remove old entries
ZCARD key  # Count = current requests in window
```

**T+1 Property:** Count reflects exact number of requests in sliding window, unlike fixed-window counters.

**Example:**
```
Window: 60 seconds
User makes requests at:
  T=10s, T=20s, T=30s, T=40s, T=50s, T=60s (5 requests in last 60s at T=60)
At T=61: oldest (10s) expires → 5 requests still in window
At T=70: oldest (20s) expires → 4 requests remain
```

---

## Rate Limit Headers

Every API response includes these headers (except errors before rate-limit check):

```
X-RateLimit-Limit: 100          # Max requests per window
X-RateLimit-Remaining: 7        # Requests left in current window
X-RateLimit-Reset: 1714129260   # Unix timestamp when window resets
X-RateLimit-Window: 60          # Window size in seconds
```

**Example:**
```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1714129260
X-RateLimit-Window: 60
Retry-After: 45
```

### `Retry-After` Header

When `429` returned, `Retry-After` indicates seconds to wait:
- **Integer:** Wait N seconds before retrying
- **HTTP-date:** Retry at specified time (RFC 7231)

---

## Error Response (429)

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "retry_after": 45,
    "limit": 50,
    "window": 60,
    "reset_at": "2026-04-28T12:01:00Z"
  }
}
```

**HTTP Status:** `429 Too Many Requests`

---

## Client-Side Handling

**Best Practices:**

1. **Check headers on every response**
   ```python
   remaining = int(response.headers.get("X-RateLimit-Remaining", "100"))
   if remaining < 5:
       time.sleep(1)  # Slow down proactively
   ```

2. **On 429: exponential backoff + jitter**
   ```python
   retry_after = int(response.headers.get("Retry-After", "60"))
   sleep_time = retry_after + random.uniform(0, 1)  # jitter
   time.sleep(sleep_time)
   ```

3. **Token bucket for outbound requests**
   ```python
   from ratelimit import limits, sleep_and_retry
   
   @sleep_and_retry
   @limits(calls=50, period=60)
   def call_api():
       client.recognize(...)
   ```

---

## Bypassing Rate Limits

**Enterprise customers** can request higher limits:

```bash
# Contact support@ai-f.security with:
# - Organization ID
# - Expected peak RPS
# - Use case description
# - Current rate limit headers observed
```

**On-prem deployments** can adjust limits in `values-prod.yaml` under `rateLimit` section.

---

## Monitoring & Alerts

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `rate_limit_exceeded_total` | Counter | Number of 429 responses |
| `rate_limit_remaining_bucket` | Gauge | Avg remaining quota across users |
| `redis_rate_limit_ops` | Histogram | Latency of rate-limit check in Redis |

**Alert Rules:**

```yaml
# High rate-limit rejection rate (> 5%)
- alert: HighRateLimitErrors
  expr: rate(rate_limit_exceeded_total[5m]) > 0.05
  for: 2m
  
# Almost all users rate-limited
- alert: GlobalRateLimitPressure
  expr: percentile(X-RateLimit-Remaining, 50) < 10
  for: 5m
```

---

## Configuration

Adjust limits in `values-prod.yaml`:

```yaml
rateLimit:
  default: 100
  byTier:
    free: 100
    pro: 1000
    enterprise: 5000
  byEndpoint:
    recognize:
      free: 50
      pro: 500
      enterprise: 2000
    enroll:
      free: 10
      pro: 100
      enterprise: 500
  burstMultiplier: 2.0        # Allow 2× burst for 10s
  burstWindow: 10
  strict: false               # Return 429 vs warning logs
```

---

## Special Cases

### API Keys (Machine-to-Machine)

API keys bypass user-based limits but have their own:

```
X-RateLimit-Limit: 10000        # Per API key per day
X-RateLimit-Remaining: 9876
```

Tracked separately per organization API key.

### WebSocket Connections

WebSocket connections count towards **concurrent stream limit**, not RPM:

| Tier | Concurrent Streams |
|------|-------------------|
| Free | 1 |
| Pro | 10 |
| Enterprise | 50 |

**Exceeding limit:** Server sends `{type: "error", code: "STREAM_LIMIT_EXCEEDED"}` and closes connection.

---

### Internal Health Checks

Health check endpoint (`GET /api/health`) is **exempt** from rate limiting.

---

## FAQ

**Q: Does rate limiting apply per IP or per user?**
A: Both. Unauthenticated requests use IP. Authenticated use user_id + org tier.

**Q: Do failed requests count against limit?**
A: Yes, all requests except `OPTIONS` and `/health` count before auth check.

**Q: Can I buy more rate limit capacity?**
A: Enterprise tier includes highest limits. Custom limits available on dedicated hosting.

**Q: How are burst limits enforced?**
A: Token bucket with capacity = `limit × burstMultiplier`. Refills at `limit / window` per second.

**Q: Do WebSocket frames count?**
A: No, only initial WebSocket upgrade request counts as 1 request. Frames are data messages.

**Q: What about batch `/api/video_recognize`?**
A: Counts as 1 request regardless of number of frames processed.

---

## Security Rationale

Rate limiting exists to prevent:
1. **Denial-of-Service (DoS):** Resource exhaustion
2. **Credential stuffing:** Brute-force token guessing
3. **Model poisoning:** Adversarial training data injection
4. **Cost runaway:** Unbilled usage on free tier
5. **Camera feed flooding:** RTSP ingestion overload

All limits are set 3-5× above reasonable human-operated usage to avoid impacting legitimate users.
