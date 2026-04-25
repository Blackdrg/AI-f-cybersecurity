# AI-f Python SDK

Official Python SDK for the AI-f Enterprise Face Recognition Platform.

[![Version](https://img.shields.io/badge/version-2.0.0-blue)](https://pypi.org/project/ai-f-sdk/)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

## Features

- **Face Recognition**: Fast, accurate face matching with multi-modal fusion
- **Multi-Modal Support**: Face, voice, and gait recognition
- **Liveness Detection**: Built-in spoof detection and anti-spoofing
- **Enterprise Security**: API key authentication, audit logging
- **Easy Integration**: Simple, Pythonic interface
- **Type Hints**: Full type annotations for better IDE support

## Installation

### From PyPI

```bash
pip install ai-f-sdk
```

### From Source

```bash
git clone https://github.com/ai-f/ai-f-python-sdk.git
cd ai-f-python-sdk
pip install -e .
```

## Quick Start

### Basic Recognition

```python
from ai_f_sdk.client import AIFClient

# Initialize client
client = AIFClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# Recognize faces in an image
result = client.recognize(
    image_path="path/to/image.jpg",
    top_k=3,
    threshold=0.5,
    enable_spoof_check=True
)

# Process results
for face in result['faces']:
    print(f"Face detected (confidence: {face['detection_confidence']:.2%})")
    for match in face['matches']:
        print(f"  - {match['name']}: {match['score']:.2%} match")
```

### Enrollment

```python
# Enroll a new person
result = client.enroll(
    name="John Doe",
    images=["photo1.jpg", "photo2.jpg", "photo3.jpg"],
    consent=True,
    age=30,
    gender="M"
)

person_id = result['person_id']
print(f"Enrolled person: {person_id}")
```

### Using Image Bytes

```python
import requests

# Download image
response = requests.get("https://example.com/photo.jpg")
image_data = response.content

# Recognize from bytes
result = client.recognize_bytes(
    image_data=image_data,
    filename="downloaded.jpg",
    top_k=5
)
```

### Context Manager

```python
# Automatically closes session when done
with AIFClient(base_url="http://localhost:8000", api_key="key") as client:
    result = client.recognize("photo.jpg")
    print(result)
```

## API Reference

### AIFClient

#### `__init__(base_url, api_key, timeout=30)`

Initialize the client.

- `base_url` (str): Base URL of the AI-f server
- `api_key` (str): API key for authentication
- `timeout` (int): Request timeout in seconds (default: 30)

#### `recognize(image_path, top_k=1, threshold=0.4, camera_id=None, enable_spoof_check=True)`

Perform face recognition on an image file.

- `image_path` (str|Path): Path to image file
- `top_k` (int): Number of top matches to return
- `threshold` (float): Recognition threshold (0-1)
- `camera_id` (str): Optional camera ID filter
- `enable_spoof_check` (bool): Enable liveness detection

Returns: Dict with faces and matches

#### `recognize_bytes(image_data, filename='image.jpg', ...)`

Perform recognition on image bytes (same parameters as `recognize`).

#### `enroll(name, images, consent=True, camera_id=None, metadata=None, age=None, gender=None)`

Enroll a new person.

- `name` (str): Person's name
- `images` (list): List of image file paths
- `consent` (bool): Consent obtained
- `camera_id` (str): Camera ID
- `metadata` (str): Optional metadata JSON
- `age` (int): Person's age
- `gender` (str): Person's gender

Returns: Dict with `person_id`

#### `enroll_bytes(name, image_data_list, filenames=None, ...)`

Enroll from image bytes.

#### `get_person(person_id)`

Get person details.

#### `update_person(person_id, name=None, age=None, gender=None)`

Update person information.

#### `delete_person(person_id)`

Delete a person and all associated data.

#### `search_persons(query, limit=10)`

Search persons by name or metadata.

#### `get_metrics()`

Get system metrics.

#### `get_health()`

Check system health.

#### `get_audit_logs(limit=100, start_date=None, end_date=None, action=None, person_id=None)`

Get audit logs for compliance.

#### `get_usage(user_id=None)`

Get usage statistics and quotas.

#### `close()`

Close the client session.

### Exceptions

- `AIFClientError`: Base exception
- `AuthenticationError`: Authentication/authorization failed
- `APIError`: API returned an error

## Configuration

### Environment Variables

```bash
export AI_F_BASE_URL="http://localhost:8000"
export AI_F_API_KEY="your-api-key"
```

### Configuration File

Create `~/.ai-f/config.ini`:

```ini
[ai-f]
base_url = http://localhost:8000
api_key = your-api-key
timeout = 30
```

## Examples

### Batch Recognition

```python
from ai_f_sdk.client import AIFClient
import glob

client = AIFClient(base_url="http://localhost:8000", api_key="key")

for image_path in glob.glob("images/*.jpg"):
    result = client.recognize(image_path, top_k=1)
    if result['faces']:
        for face in result['faces']:
            if face['matches']:
                print(f"{image_path}: {face['matches'][0]['name']}")
            else:
                print(f"{image_path}: Unknown")
```

### Enroll Multiple People

```python
people = [
    {"name": "Alice", "images": ["alice1.jpg", "alice2.jpg"], "age": 28},
    {"name": "Bob", "images": ["bob1.jpg"], "age": 35},
]

for person in people:
    result = client.enroll(
        name=person['name'],
        images=person['images'],
        age=person['age'],
        consent=True
    )
    print(f"Enrolled {person['name']}: {result['person_id']}")
```

### Check System Health

```python
health = client.get_health()
if health['status'] == 'ok':
    print("System is healthy")
    print(f"Uptime: {health['uptime']}")
else:
    print(f"System issue: {health['issues']}")
```

## Error Handling

```python
from ai_f_sdk.client import AIFClient, AuthenticationError, APIError

client = AIFClient(base_url="...", api_key="...")

try:
    result = client.recognize("image.jpg")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except APIError as e:
    print(f"API error ({e.status_code}): {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Tips

1. **Reuse client**: Create one client and reuse it (uses connection pooling)
2. **Batch operations**: Use context manager for multiple operations
3. **Adjust timeouts**: Increase timeout for large images or slow networks
4. **Use appropriate thresholds**: Lower thresholds for more matches, higher for fewer

## Requirements

- Python 3.8 or higher
- `requests>=2.28.0`
- `httpx>=0.24.0`
- `pydantic>=2.0.0` (optional, for type validation)

## Support

- Documentation: https://docs.ai-f.io/sdk/python
- Issue Tracker: https://github.com/ai-f/ai-f-python-sdk/issues
- Email: sdk-support@ai-f.io

## License

Apache License 2.0

Copyright (c) 2024 AI-f Security Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this license notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
