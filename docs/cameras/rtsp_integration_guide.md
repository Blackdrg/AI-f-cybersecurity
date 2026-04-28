# Camera Integration & RTSP Pipeline

## Overview

AI-f supports real-time video ingestion from RTSP cameras for live face recognition.
This document covers camera configuration, RTSP URL formats, codec requirements,
and the end-to-end ingestion pipeline.

---

## RTSP URL Format

### Standard RTSP

```
rtsp://<username>:<password>@<camera-ip>:<port>/<path>
```

**Examples:**
```
rtsp://admin:secret@192.168.1.100:554/live
rtsp://user:pass@10.0.0.50:8554/stream1
rtsp://camera-ip:554/VideoInputPrimary  # no auth
```

### Components

| Part | Description | Default |
|------|-------------|---------|
| `username` | Camera login username | — |
| `password` | Camera login password | — |
| `camera-ip` | IPv4 address or hostname | — |
| `port` | RTSP port (usually 554) | 554 |
| `path` | Stream endpoint (camera-specific) | `/live`, `/stream1`, `/video`, `/cam/realmonitor` |

---

## Path Conventions by Vendor

| Vendor | Common Paths | Notes |
|--------|--------------|-------|
| **Hikvision** | `/ISAPI/Streaming/Channels/101` | 101 = main stream, 102 = sub-stream |
| **Dahua** | `/cam/realmonitor?channel=1&subtype=0` | subtype=0=main, 1=sub |
| **Axis** | `/axis-media/media.amp` | May require `?resolution=...` |
| **Amcrest** | `/mpeg4/1/video.sdp` | H.264 over RTSP |
| **Ubiquiti (UniFi)** | `/RtspTranslator.01` | UniFi Protect |
| **ONVIF-compliant** | `/onvif/streaming/...` | Standard ONVIF URI |

**Discovery:** Use ONVIF Device Manager or vendor tool to get exact URI.

---

## Authentication

### Basic Auth (most common)

Embedded in URL: `rtsp://user:pass@ip:554/path`

**Security:** Credentials sent plaintext within RTSP session (TLS not standard for RTSP). Use VPN or network isolation.

### Digest Auth

OpenCV's `VideoCapture` handles both Basic and Digest automatically.

### Token-based (Azure Media, some cloud cameras)

```
rtsp://<ip>:554/path?token=abc123...
```

Pass token as query parameter.

---

## Codec Requirements

### Preferred: H.264 (AVC)

| Parameter | Value |
|-----------|-------|
| Profile | High or Main |
| Level | 4.0 or 4.1 |
| Bitrate | 2-8 Mbps (1080p @ 30fps) |
| Keyframe interval | 1-2 seconds (important for I-frame alignment) |

**Why:** Widely supported, hardware acceleration on most GPUs, good compression.

---

### Supported: H.265 (HEVC)

| Parameter | Value |
|-----------|-------|
| Profile | Main |
| Level | 5.0 (Main10 not supported) |
| Bitrate | 1-4 Mbps (1080p @ 30fps) |

**Caution:** Higher CPU decode cost if GPU not available. Check `cv2.CAP_PROP_HW_ACCELERATION`.

---

### Fallback: MJPEG

Uncompressed frames — very high bandwidth (20-50 Mbps for 1080p). Only recommended for LAN testing.

---

## Camera Configuration Checklist

Before adding camera to AI-f:

1. **Network reachability:** Ping camera IP from backend server
2. **RTSP URL validate:** Use `ffprobe` or VLC:
   ```bash
   ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name -of json rtsp://...
   ```
3. **Credentials:** Verify username/password (test with VLC)
4. **Frame rate:** Camera FPS should match ingestion FPS (default 10 fps)
5. **Resolution:** 720p (1280×720) or 1080p (1920×1080) recommended
6. **Bandwidth:** Ensure upstream bandwidth can handle all camera streams
7. **Timezone:** Set camera timestamp correctly (used in audit logs)
8. **NTP sync:** All cameras should sync to same NTP server

---

## Ingestion Pipeline

```
RTSP Stream (H.264)
    ↓
OpenCV VideoCapture (cv2.CAP_FFMPEG)
    ↓
Hardware Decode (if NVIDIA GPU available) → CUDA GPU memory
    ↓
Software Fallback (libavcodec) → CPU memory
    ↓
Frame Extraction (1 frame per second or on-demand)
    ↓
BGR → RGB conversion (OpenCV uses BGR)
    ↓
Face Detection Model (MTCNN/RetinaFace ONNX)
    ↓
Results → Redis Pub/Sub → Recognition API / WebSocket clients
```

### Pipeline Stages

**1. Stream Connection**
- Open RTSP via `cv2.VideoCapture(rtsp_url)`
- Timeout: 10 seconds, retry 3×
- On failure: Mark camera offline, alert

**2. Frame Decoding**
- Prefer GPU decoding if `CUDA_VISIBLE_DEVICES >= 0`
- Use `cv2.CAP_PROP_HW_ACCELERATION` to query
- Fallback to CPU FFmpeg

**3. Frame Sampling**
- Default: 1 frame per second (FPS of camera irrelevant)
- Configurable per camera: `frame_interval` (e.g., every 30 frames = 1 fps @ 30fps camera)
- Adaptive sampling: Increase during low activity, decrease on high motion

**4. Processing**
- Each frame → Face detection → Recognition
- Results timestamped with camera's timestamp or server time
- Publish to Redis channel `camera:{camera_id}`

---

## Adding a Camera (API)

### Step 1: Register Camera

```bash
POST /api/orgs/{org_id}/cameras
{
  "name": "Main Entrance",
  "rtsp_url": "rtsp://admin:secret@192.168.1.100:554/live",
  "location": "Building A, Main Door"
}
```

**Response:**
```json
{
  "camera_id": "cam_abc123",
  "org_id": "org_xyz",
  "name": "Main Entrance",
  "rtsp_url": "rtsp://...",
  "status": "offline",
  "created_at": "2026-04-28T12:00:00Z"
}
```

---

### Step 2: Test Connection

```bash
POST /api/orgs/{org_id}/cameras/test-connection
{
  "rtsp_url": "rtsp://admin:secret@192.168.1.100:554/live"
}
```

Returns `{"status": "success", "message": "Stream connection verified"}` if reachable.

---

### Step 3: Start Ingestion

```bash
POST /api/orgs/{org_id}/cameras/{camera_id}/start
```

No body. Returns `204 No Content` on success.

**Camera status changes to `streaming`.**

---

### Step 4: Monitor Status

```bash
GET /api/orgs/{org_id}/cameras/{camera_id}/status
```

Response:
```json
{
  "camera_id": "cam_abc123",
  "status": "streaming",  // streaming | offline | error
  "fps": 9.8,
  "frames_processed": 15432,
  "last_frame_at": "2026-04-28T12:05:00Z",
  "uptime_seconds": 86400
}
```

---

## Camera Management Operations

### Stop Stream

```bash
POST /api/orgs/{org_id}/cameras/{camera_id}/stop
```

---

### Update Camera Config

```bash
PUT /api/orgs/{org_id}/cameras/{camera_id}
{
  "name": "New Name",
  "location": "New Location",
  "frame_interval": 15  // process every 15 frames
}
```

---

### List All Cameras

```bash
GET /api/orgs/{org_id}/cameras
```

---

### Delete Camera

```bash
DELETE /api/orgs/{org_id}/cameras/{camera_id}
```

**Note:** Does **not** delete associated recognition events — retains history.

---

## Troubleshooting

### "Could not connect to RTSP stream"

**Diagnosis:**
1. Ping camera IP
2. Use VLC: `Media → Open Network Stream → rtsp://...`
3. Check firewall rules (port 554 open?)
4. Verify credentials

---

### "Stream disconnects frequently"

**Causes:**
- Network packet loss (WiFi unreliable — use wired Ethernet)
- Camera reboots daily (check camera uptime)
- IP conflict on network
- Bandwidth saturated

**Fixes:**
- Enable RTSP keepalive (OpenCV default is 60s)
- Increase `cv2.CAP_PROP_BUFFERSIZE` (default: 1, increase for buffering)
- Use lower resolution / bitrate on camera
- Switch to H.264 baseline profile (less error-prone)

---

### "Low FPS / laggy"

**Diagnosis:**
1. Check CPU usage: `top` / `htop`
2. GPU utilization: `nvidia-smi`
3. Network: `iftop` or `nethogs`

**Solutions:**
- Reduce `frame_interval` → process fewer frames
- Enable GPU decoding (install NVIDIA drivers + CUDA)
- Scale horizontally (more backend pods)
- Use lower-resolution stream (if camera supports multiple streams)

---

### "No faces detected"

**Likely causes:**
- Camera angle too high/low
- Poor lighting (backlit, dark)
- Resolution too low (< 200px face size)
- Face detector model not loaded

**Check:**
```bash
# Test single frame manually
python -c "
import cv2
cap = cv2.VideoCapture('rtsp://...')
ret, frame = cap.read()
print('Frame shape:', frame.shape if ret else 'failed')
"
```

---

## Multi-Camera Synchronization

For cross-camera fusion (same person seen by multiple cameras simultaneously):

**POST `/ws/recognize_stream` with `multi_camera` message:**

```json
{
  "type": "multi_camera",
  "data": {
    "camera_ids": ["cam_01", "cam_02", "cam_03"],
    "sync_timestamps": [1620000000.1, 1620000000.1, 1620000000.15],
    "frames": ["<base64>", "<base64>", "<base64>"]
  }
}
```

**Server returns matched person across cameras with timestamp alignment.**

---

## Security Considerations

### Network Isolation

- Cameras on separate VLAN (no direct internet access)
- Backend only initiates RTSP (camera cannot call back)
- VPN tunnel for remote sites

### Credential Storage

- RTSP URLs encrypted at rest in database (AES-256-GCM)
- Key rotated quarterly
- Access to camera credentials logged in audit

### RTSP over TLS (RTSPS)

Not widely supported by cameras. If required:
- Use stunnel on camera or NVR to wrap RTSP in TLS
- URL becomes: `rtsps://...:322`

---

## Performance Tuning

### Optimal Settings

| Metric | Recommended |
|--------|-------------|
| Camera resolution | 1280×720 (720p) |
| Frame rate at camera | 15-30 fps |
| Ingestion frame rate | 5-10 fps (adjust via `frame_interval`) |
| Keyframe interval | 1 second (camera setting) |
| Bitrate | 2048 kbps (H.264) |
| Profile | Main (not High, reduces decode cost) |

---

### Capacity Planning

**Per camera bandwidth:**
- 720p @ 10 fps H.264 ≈ 1.5 Mbps
- 100 cameras ≈ 150 Mbps network

**Per camera compute:**
- Face detection per frame: ~45ms CPU, ~12ms GPU
- 1 fps → 45ms CPU per camera
- 100 cameras @ 1 fps = 4.5s CPU per second (→ need 5 dedicated CPU cores)

**Formula:**
```
Required CPU cores = (num_cameras × frames_per_sec × ms_per_frame) / 1000
e.g., 100 cameras × 1 × 45ms = 4.5 cores
```

---

## Appendix: Sample Camera Configs

### Hikvision DS-2CD2147G2-LSU

```
RTSP: rtsp://admin:password@192.168.1.100:554/ISAPI/Streaming/Channels/101
Codec: H.264 High
Resolution: 1920×1080 @ 20fps
Bitrate: 4096 kbps
```

### Dahua IPC-HDW3849T-AS

```
RTSP: rtsp://admin:password@192.168.1.101:554/cam/realmonitor?channel=1&subtype=0
Codec: H.264 Main
Resolution: 3840×2160 @ 15fps (downscale to 1080p recommended)
```

### Axis P1367-E

```
RTSP: rtsp://root:password@192.168.1.102:554/axis-media/media.amp?resolution=1920x1080
Codec: H.264 High
Resolution: 1920×1080 @ 30fps
```

---

## Next Steps

- [ ] Auto-discovery via ONVIF (`/api/cameras/discover`)
- [ ] ONVIF event subscription (motion-triggered stream pull)
- [ ] Camera health monitoring (SNMP traps)
- [ ] Failover: secondary RTSP URL per camera
- [ ] Re-recording from camera NVR on demand
