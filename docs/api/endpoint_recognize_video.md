# Video Batch Recognition API (`POST /api/recognize_video`)

## Purpose

Process entire video files to extract all face recognition events. Ideal for:
- Uploading surveillance footage for forensic analysis
- Batch processing security camera recordings
- Generating daily activity reports from stored video

**Endpoint:** `POST /api/recognize_video`  
**Authentication:** Required (JWT Bearer)  
**Content-Type:** `multipart/form-data`

---

## Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `video` | file (multipart) | **Yes** | Video file (MP4, AVI, MOV, MKV) |
| `top_k` | integer | No | Number of top matches per face (default: 1, max: 10) |
| `threshold` | float | No | Recognition threshold 0.0–1.0 (default: 0.6) |
| `camera_id` | string | No | Associate with camera (for audit) |
| `frame_interval` | integer | No | Process every Nth frame (default: 30 ≈ 1 fps @ 30fps) |
| `enable_spoof_check` | boolean | No | Run anti-spoof detection (default: true) |
| `notify_completion` | boolean | No | Send webhook when done (default: false) |
| `callback_url` | string | No | Webhook URL for async completion (if notify_completion=true) |

---

## Supported Video Formats

| Container | Video Codec | Audio | Notes |
|-----------|-------------|-------|-------|
| MP4 | H.264 (AVC) | AAC | **Recommended** - best compatibility |
| MP4 | H.265 (HEVC) | AAC | Supported if hardware decoder available |
| AVI | MJPEG | PCM | Uncompressed - large files |
| MOV | H.264 | AAC | QuickTime container |
| MKV | H.264/H.265 | Vorbis/Opus | Matroska - variable bitrate OK |

**Maximum file size:** 2 GB (for memory safety). Larger files should be split.

**Maximum duration:** 1 hour recommended (processing time ~2-10× realtime depending on hardware).

---

## Processing Pipeline

```
Uploaded video file
      ↓
OpenCV VideoCapture decode
      ↓
Frame extraction (every frame_interval)
      ↓
Resize to 640×480 (optional speed/accuracy tradeoff)
      ↓
Face detection per frame
      ↓
For each face:
    - Align & crop
    - Extract embedding (512-d)
    - Compare to database (cosine similarity)
    - Spoof check (if enabled)
    - Record match
      ↓
Aggregate: group matches by person across frames
      ↓
Return results array (one entry per processed frame)
```

---

## Response Format

**Status:** `200 OK` (synchronous processing; for large videos, use `notify_completion=true` for async webhook)

**Body:** Array of `RecognizeResponse` objects, one per processed frame.

```json
[
  {
    "faces": [
      {
        "face_box": [125, 340, 210, 280],
        "face_embedding_id": "emb_frame001_face0",
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
        "spoof_score": 0.12
      }
    ]
  },
  {
    "faces": []
  },
  {
    "faces": [
      {
        "face_box": [130, 345, 208, 275],
        "matches": [
          {
            "person_id": "pers_001",
            "name": "John Doe",
            "score": 0.938,
            "distance": 0.062
          }
        ],
        "inference_ms": 87.2,
        "is_unknown": false
      }
    ]
  }
]
```

**Total frames processed:** `len(response_array)`

**Frames with matches:** `sum(1 for frame in response if frame["faces"])`

---

## Asynchronous Mode (Large Videos)

For videos > 100 MB or > 10 minutes duration, use async:

**Request:**
```bash
POST /api/recognize_video
?notify_completion=true
&callback_url=https://your-server.com/api/video-complete
```

**Response (202 Accepted):**
```json
{
  "job_id": "job_abc123def",
  "status": "queued",
  "estimated_completion_seconds": 3600,
  "callback_url": "https://your-server.com/api/video-complete"
}
```

**Webhook payload when done:**
```json
{
  "job_id": "job_abc123def",
  "status": "completed",
  "video_path": "/tmp/uploaded_video.mp4",
  "total_frames": 18000,
  "recognitions_found": 142,
  "results_url": "https://api.example.com/api/video_results/job_abc123def",
  "download_url": "https://api.example.com/api/video_results/job_abc123def/download"
}
```

You can then `GET` the results:

```bash
GET /api/video_results/{job_id}
```

Returns same format as synchronous response but paginated (if large).

---

## Frame Extraction Details

**Frame interval logic:**
```
For video at 30 fps:
  frame_interval = 30   → 1 frame per second
  frame_interval = 10   → 3 frames per second
  frame_interval = 1    → every frame (30 fps); NOT recommended
```

**Why skip frames?**
- Face recognition is compute-intensive (~150ms per frame)
- Persons don't change appearance between consecutive frames
- Reduces storage & processing by 30× with minimal recall loss

**Adaptive extraction:** Future version will use motion detection to only extract frames when movement detected.

---

## Output Post-Processing

The raw frame-by-frame results can be aggregated:

```python
results = api.recognize_video("surveillance.mp4", top_k=1, frame_interval=30)

# Aggregate: person -> list of sightings
sightings = {}
for frame_idx, frame_result in enumerate(results):
    for face in frame_result["faces"]:
        if face["matches"]:
            person_id = face["matches"][0]["person_id"]
            if person_id not in sightings:
                sightings[person_id] = []
            sightings[person_id].append({
                "frame": frame_idx,
                "confidence": face["matches"][0]["score"],
                "timestamp_estimate": frame_idx / fps * frame_interval
            })

# person "pers_001" appeared at frames [30, 90, 150, 210] → ~7-second appearances
```

---

## Performance

**Processing speed:** ~2-10× realtime on GPU, ~0.5× on CPU

| Hardware | 1-hour video @ 30fps (processed 1 fps) | Est. Time |
|----------|----------------------------------------|-----------|
| T4 GPU (cloud) | 3600 frames → 6 min | 6 min |
| M2 Pro (Mac) | 3600 frames → 12 min | 12 min |
| CPU-only (8 core) | 3600 frames → 90 min | 90 min |

**Tips:**
- Use `frame_interval=60` for long videos (0.5 fps is enough)
- Disable spoof detection (`enable_spoof_check=false`) for archival footage
- Pre-process to lower resolution (720p → 480p) if accuracy can tolerate

---

## Error Handling

**400 Invalid video file:**
```json
{
  "detail": "Invalid video file: could not decode"
}
```
→ Check codec support. Re-encode to H.364 baseline.

**422 No valid faces:**
```json
{
  "detail": "Video processing completed but no faces were detected in any frame"
}
```
→ Not an error — just empty result array returned.

**413 Payload too large:**
→ File exceeds 2 GB limit. Split video.

**504 Gateway Timeout:**
→ Video processing exceeded 10-minute HTTP timeout. Use async mode (`notify_completion=true`).

---

## Best Practices

1. **Chunk long videos** into < 10 min segments for reliability
2. **Use async mode** for anything > 500 MB
3. **Set appropriate `frame_interval`** based on scene motion:
   - Static security cam: interval=60 (0.5 fps)
   - Active lobby: interval=15 (2 fps)
4. **Provide `camera_id`** for audit trail and analytics
5. **Don't enable spoof_check** for archival/search use cases (wastes CPU)

---

## CLI Example

```bash
# Synchronous (small video < 50 MB)
curl -X POST "http://localhost:8000/api/recognize_video" \
  -H "Authorization: Bearer $TOKEN" \
  -F "video=@/path/to/clip.mp4" \
  -F "top_k=3" \
  -F "threshold=0.5" \
  -F "frame_interval=30" \
  | jq .

# Asynchronous (large video)
curl -X POST "http://localhost:8000/api/recognize_video?notify_completion=true&callback_url=https://my.webhook/handler" \
  -H "Authorization: Bearer $TOKEN" \
  -F "video=@@ surveillance_full_day.mp4" \
  -F "frame_interval=60"
```

---

## Implementation Notes

**Current limitations:**
- No GPU-accelerated decoding (CPU fallback only)
- Single-threaded per request (future: parallel frame batches)
- No face tracking across frames (duplicate detections possible)
- Results not deduplicated (same person detected in consecutive frames appears multiple times)

**Future improvements:**
- Tracker-based deduplication (DeepSORT)
- Adaptive frame selection based on motion
- Distributed processing (split video across workers)
- Streaming mode (WebSocket) for live video files

---

## Related Endpoints

- `POST /api/recognize` — single image
- `WS /ws/recognize_stream` — live camera stream
- `POST /api/video/analyze` (future) — video with audio + voice embedding fusion
