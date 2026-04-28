# WebSocket `/ws/recognize_stream` Message Format Specification

## Overview

The WebSocket endpoint at `/ws/recognize_stream` provides real-time, bidirectional
communication for live face recognition from cameras and video streams.

**Endpoint:** `ws://<host>/ws/recognize_stream?top_k=1&threshold=0.4&camera_id=cam_001`

## Connection Lifecycle

### 1. Connection Establishment

**Client → Server:**
- Open WebSocket connection with optional query parameters:
  - `top_k`: Number of top matches to return (default: 1)
  - `threshold`: Recognition similarity threshold 0-1 (default: 0.4)
  - `camera_id`: Camera identifier for stream context (optional)
  - `org_id`: Organization ID (if multi-tenant context needed)

**Server Response:**
```json
{
  "type": "connection_established",
  "ws_id": "ws_abc123def",
  "message": "WebSocket connection established",
  "config": {
    "top_k": 1,
    "threshold": 0.4,
    "camera_id": "cam_001"
  }
}
```

**Server → Client (periodic heartbeat):**
```json
{
  "type": "heartbeat",
  "timestamp": "2026-04-28T12:00:00Z"
}
```

### 2. Frame Streaming (Client → Server)

**Message Type:** `frame`

**Client sends base64-encoded image frame:**
```json
{
  "type": "frame",
  "data": "<base64-encoded-JPEG-image>",
  "timestamp": "2026-04-28T12:00:01.123Z",
  "frame_number": 42,
  "camera_id": "optional-override"
}
```

**Image Requirements:**
- Format: JPEG (preferred) or PNG
- Max resolution: 1920x1080 (larger images will be downsampled)
- Max size: 5MB per frame
- Encoding: base64 string of raw bytes

### 3. Recognition Results (Server → Client)

**Message Type:** `recognize_result`

**Server returns processed recognition:**
```json
{
  "type": "recognize_result",
  "faces": [
    {
      "face_box": [x, y, width, height],
      "face_embedding_id": "emb_abc123",
      "matches": [
        {
          "person_id": "pers_001",
          "name": "John Doe",
          "score": 0.947,
          "distance": 0.053
        }
      ],
      "inference_ms": 89.5,
      "is_unknown": false,
      "spoof_score": 0.12,
      "reconstruction_confidence": 0.89,
      "emotion": {
        "happy": 0.85,
        "neutral": 0.10,
        "surprise": 0.05
      },
      "age": 32,
      "gender": "male",
      "behavior": {
        "fatigue": 0.15,
        "aggression": 0.05,
        "engagement": 0.80
      }
    }
  ],
  "timestamp": "2026-04-28T12:00:01.234Z",
  "processing_latency_ms": 156.7,
  "camera_id": "cam_001"
}
```

### 4. Multi-Camera Synchronized Processing

**Message Type:** `multi_camera`

**Request:**
```json
{
  "type": "multi_camera",
  "data": {
    "camera_ids": ["cam_01", "cam_02", "cam_03"],
    "sync_timestamps": [1234567890.1, 1234567890.1, 1234567890.2],
    "frames": ["<base64-1>", "<base64-2>", "<base64-3>"]
  }
}
```

**Response:**
```json
{
  "type": "multi_camera_result",
  "faces": [
    {
      "person_id": "pers_001",
      "cameras": ["cam_01", "cam_02"],
      "avg_score": 0.92,
      "scores": [0.91, 0.93]
    }
  ]
}
```

### 5. Subscription Management

**Change Camera Subscription:**
```json
{
  "type": "subscribe",
  "camera_id": "cam_002"
}
```

**Server confirmation:**
```json
{
  "type": "subscription_changed",
  "subscribed_cameras": ["cam_001", "cam_002"]
}
```

### 6. Error Handling

**Server → Client (Error):**
```json
{
  "type": "error",
  "code": "PROCESSING_ERROR",
  "message": "Failed to process frame: No face detected",
  "frame_number": 42,
  "timestamp": "2026-04-28T12:00:01.500Z"
}
```

**Error Codes:**
| Code | Meaning | Retry |
|------|---------|-------|
| `INVALID_FRAME` | Frame format invalid | No |
| `NO_FACE_DETECTED` | No face in frame | Yes (next frame) |
| `MODEL_ERROR` | Internal model failure | Yes (after 1s) |
| `RATE_LIMITED` | Too many requests | Yes (after reset) |
| `AUTH_ERROR` | Authentication failed | Reconnect |

### 7. Connection Close

**Graceful disconnect (client → server):**
```json
{
  "type": "close",
  "reason": "client_shutdown"
}
```

**Server → Client (forced disconnect):**
```json
{
  "type": "connection_closed",
  "reason": "rate_limit_exceeded",
  "retry_after": 60
}
```

## Event Type Enum

| Type | Direction | Description |
|------|-----------|-------------|
| `connection_established` | Server | Sent upon successful connection |
| `heartbeat` | Server | Periodic keep-alive (every 30s) |
| `frame` | Client | Raw image frame to process |
| `recognize_result` | Server | Recognition results for frame |
| `multi_camera` | Client | Synchronized multi-cam request |
| `multi_camera_result` | Server | Multi-camera fused result |
| `subscribe` | Client | Subscribe to different camera |
| `subscription_changed` | Server | Subscription update confirmed |
| `error` | Server | Error notification |
| `connection_closed` | Server | Connection termination notice |

## Reconnection Strategy

**Clients should:**
1. Reconnect on any network error or close event
2. Implement exponential backoff: 1s, 2s, 4s, 8s, max 30s
3. Preserve `camera_id` and `top_k`/`threshold` settings across reconnects
4. Clear pending frames before reconnecting

**Example reconnection logic (pseudocode):**
```
on_close(reason):
    if reason != "normal":
        wait = min(2^retry_count, 30)
        sleep(wait)
        reconnect_with_same_params()
        retry_count += 1
    else:
        stop()
```

## Performance Considerations

- **Target latency:** P50 < 150ms, P99 < 300ms per frame
- **Frame rate:** Up to 30 FPS sustained (recommended: 5-10 FPS for quality)
- **Concurrent streams:** 2000+ per server instance (with auto-scaling)
- **Message size:** Typical frame message ~200KB (compressed JPEG)
- **Bandwidth:** ~2 MB/s @ 10 FPS per stream

## Security

- WebSocket connection requires JWT in initial HTTP Upgrade request header:
  ```
  Authorization: Bearer <jwt_token>
  ```
- Token validated before WebSocket upgrade accepted
- Rate limited per user (configurable in `RateLimitMiddleware`)
- Connection terminated after 5 minutes of inactivity

## Implementation Notes

**Backpressure:**
- Server maintains per-connection queue (max 10 pending frames)
- If queue full, server sends `RATE_LIMITED` error and client should pause

**Ordering Guarantees:**
- Frames processed in order received
- Results delivered in same order as requests
- Out-of-order frames dropped with warning

**Camera Context:**
- `camera_id` set on connection URL applies to all frames unless overridden
- Changing subscription via `subscribe` message swaps active camera

**Error Recovery:**
- Transient errors (no face, model hiccup) don't close connection
- Persistent errors (auth failure) close connection immediately
