# Face Recognition Python SDK

A Python SDK for interacting with the Face Recognition Service.

## Installation

```bash
pip install face-recognition-sdk
```

## Usage

```python
from face_recognition_sdk import FaceRecognitionSDK

# Initialize SDK
sdk = FaceRecognitionSDK(base_url="http://localhost:8000", api_key="your-api-key")

# Enroll a person
with open("person.jpg", "rb") as f:
    image_data = f.read()

result = sdk.enroll_person(
    name="John Doe",
    images=[image_data],
    consent=True
)
print(f"Enrolled person: {result['person_id']}")

# Recognize faces
with open("test_image.jpg", "rb") as f:
    test_image = f.read()

result = sdk.recognize_faces(test_image, top_k=3, threshold=0.5)
for face in result['faces']:
    print(f"Detected face with matches: {len(face['matches'])}")
```

## API Reference

### FaceRecognitionSDK

- `__init__(base_url="http://localhost:8000", api_key=None)`
- `enroll_person(name, images, consent=True, camera_id=None, metadata=None)`
- `recognize_faces(image, top_k=1, threshold=0.4, camera_id=None)`
- `get_person(person_id)`
- `delete_person(person_id)`
- `get_metrics()`
- `get_audit_logs(limit=100, start_date=None, end_date=None, action=None)`
