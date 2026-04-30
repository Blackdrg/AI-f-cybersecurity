# Webhook Signature Verification Guide

This guide shows how to verify webhook signatures from AI-f for secure webhook integration.

## Webhook Payload Example

When AI-f sends a webhook, it includes headers for signature verification:

```http
POST /your-webhook-endpoint HTTP/1.1
Host: your-server.com
Content-Type: application/json
X-AIF-Signature: sha256=<signature>
X-AIF-Timestamp: 1714125600
X-AIF-Event: recognition.match
```

### Example Payload

```json
{
  "event": "recognition.match",
  "timestamp": "2026-04-27T10:00:00Z",
  "data": {
    "event_id": "evt_abc123",
    "person_id": "pers_xyz789",
    "person_name": "John Doe",
    "confidence": 0.947,
    "camera_id": "cam_lobby",
    "camera_name": "Lobby Camera",
    "organization_id": "org_demo"
  }
}
```

## Signature Verification

### Python Example

```python
import hmac
import hashlib
import time

def verify_webhook_signature(
    payload: bytes,
    signature: str,
    timestamp: str,
    secret: str
) -> bool:
    """
    Verify AI-f webhook signature.
    
    Args:
        payload: Raw request body
        signature: Value from X-AIF-Signature header
        timestamp: Value from X-AIF-Timestamp header
        secret: Your webhook secret from AI-f dashboard
    
    Returns:
        True if signature is valid
    """
    # Check timestamp is within 5 minutes
    if abs(time.time() - int(timestamp)) > 300:
        return False
    
    # Compute expected signature
    message = timestamp + "." + payload.decode('utf-8')
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    return hmac.compare_digest(signature, expected_signature)


# Flask example
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_SECRET = "your-webhook-secret-from-dashboard"

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    payload = request.get_data()
    signature = request.headers.get('X-AIF-Signature', '')
    timestamp = request.headers.get('X-AIF-Timestamp', '')
    
    # Remove 'sha256=' prefix if present
    if signature.startswith('sha256='):
        signature = signature[7:]
    
    if not verify_webhook_signature(
        payload, 
        signature, 
        timestamp,
        WEBHOOK_SECRET
    ):
        return jsonify({"error": "Invalid signature"}), 401
    
    # Process webhook payload
    event = request.json
    if event['event'] == 'recognition.match':
        person_name = event['data']['person_name']
        confidence = event['data']['confidence']
        print(f"Recognized: {person_name} ({confidence:.1%})")
    
    return jsonify({"status": "ok"}), 200
```

### Node.js Example

```javascript
const crypto = require('crypto');
const express = require('express');

const app = express();
const WEBHOOK_SECRET = 'your-webhook-secret-from-dashboard';

app.use(express.json({
    verify: (req, res, buf) => {
        req.rawBody = buf;
    }
}));

function verifyWebhookSignature(payload, signature, timestamp) {
    // Check timestamp
    if (Math.abs(Date.now() / 1000 - parseInt(timestamp)) > 300) {
        return false;
    }
    
    // Compute signature
    const message = timestamp + '.' + payload.toString('utf-8');
    const expectedSignature = crypto
        .createHmac('sha256', WEBHOOK_SECRET)
        .update(message, 'utf-8')
        .digest('hex');
    
    // Constant-time comparison
    return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignature)
    );
}

app.post('/webhook', (req, res) => {
    const signature = (req.headers['x-aif-signature'] || '').replace('sha256=', '');
    const timestamp = req.headers['x-aif-timestamp'] || '';
    
    if (!verifyWebhookSignature(req.rawBody, signature, timestamp)) {
        return res.status(401).json({ error: 'Invalid signature' });
    }
    
    // Process webhook
    if (req.body.event === 'recognition.match') {
        console.log(`Recognized: ${req.body.data.person_name}`);
    }
    
    res.json({ status: 'ok' });
});
```

### Go Example

```go
package main

import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "time"
    
    "github.com/gin-gonic/gin"
)

const webhookSecret = "your-webhook-secret"

func verifySignature(payload []byte, signature, timestamp string) bool {
    // Check timestamp
    ts, _ := strconv.ParseInt(timestamp, 10, 64)
    if time.Since(time.Unix(ts, 0)) > 5*time.Minute {
        return false
    }
    
    // Compute signature
    message := timestamp + "." + string(payload)
    mac := hmac.New(sha256.New, []byte(webhookSecret))
    mac.Write([]byte(message))
    expected := hex.EncodeToString(mac.Sum(nil))
    
    // Constant-time comparison
    return hmac.Equal([]byte(signature), []byte(expected))
}

func webhookHandler(c *gin.Context) {
    payload, _ := c.GetRawData()
    signature := c.GetHeader("X-AIF-Signature")
    timestamp := c.GetHeader("X-AIF-Timestamp")
    
    if signature != "" {
        signature = strings.TrimPrefix(signature, "sha256=")
    }
    
    if !verifySignature(payload, signature, timestamp) {
        c.JSON(401, gin.H{"error": "Invalid signature"})
        return
    }
    
    c.JSON(200, gin.H{"status": "ok"})
}
```

## Supported Events

| Event | Description |
|-------|-------------|
| `recognition.match` | Person recognized |
| `recognition.no_match` | No match found |
| `spoof.detected` | Spoof attempt detected |
| `enrollment.complete` | New person enrolled |
| `alert.triggered` | Alert triggered |
| `subscription.created` | Subscription created |
| `subscription.expiring` | Subscription expiring soon |

## Testing Webhooks

Use the AI-f dashboard to:
1. Configure webhook URL
2. Get your webhook secret
3. Test with sample events

## Best Practices

1. **Always verify signatures** - Never process unverified webhooks
2. **Check timestamps** - Reject old payloads (>5 minutes)
3. **Acknowledge quickly** - Return 200 within 5 seconds
4. **Queue for processing** - Process in background after acknowledgment
5. **Handle duplicates** - Use event_id for idempotency
