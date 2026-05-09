# AIFace SDK for iOS/macOS

Swift package for the LEVI-AI face recognition platform.

## Requirements

- iOS 14+ / macOS 11+
- Xcode 13+
- Swift 5.5+

## Installation

### Swift Package Manager

```swift
dependencies: [
    .package(url: "https://github.com/owner/ai-f.git", from: "2.1.0")
]
```

## Usage

```swift
import AIFaceSDK

let config = AIFaceConfig(
    apiBaseURL: URL(string: "https://api.example.com")!,
    apiKey: "your-api-key",
    offlineMode: false
)

let client = AIFaceClient(config: config)

// Enroll a face
let imageData = try Data(contentsOf: faceImageURL)
let result = try await client.enroll(
    imageData: imageData,
    personId: "person-123",
    name: "John Doe"
)

// Recognize a face
let recognition = try await client.recognize(imageData: imageData)
print("Matched: \(recognition.personId), confidence: \(recognition.confidence)")
```

## Status

**v2.1 Scaffold** — This SDK provides type definitions and method signatures. Full REST client implementation pending.

## Upcoming

- Core ML on-device face detection & embedding (offline mode)
- TFLite model support for iOS (via Core ML conversion)
- Biometric template protection with on-device encryption
- Local enrollment caching for offline-first operation
