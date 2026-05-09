# AIFace SDK for Android

Kotlin client for the LEVI-AI face recognition platform.

## Requirements

- Android API 24+ (Android 7.0 Nougat)
- Kotlin 1.8+
- Java 11+

## Setup

### Gradle (Kotlin DSL)

```kotlin
dependencies {
    implementation("com.aif.sdk:android-sdk:2.1.0")
}
```

### Maven

```xml
<dependency>
    <groupId>com.aif.sdk</groupId>
    <artifactId>android-sdk</artifactId>
    <version>2.1.0</version>
</dependency>
```

## Usage

```kotlin
import com.aif.sdk.AIFaceClient
import com.aif.sdk.AIFaceConfig

// Initialize
val config = AIFaceConfig(
    apiBaseUrl = "https://api.example.com",
    apiKey = "your-api-key",
    offlineMode = false,
    context = applicationContext
)

val client = AIFaceClient.initialize(config)

// Enroll a face (async with CompletableFuture)
val imageFile = File("/path/to/face.jpg")
client.enroll(imageFile, "person-123", "John Doe")
    .thenAccept { result ->
        Log.i("AIFace", "Enrollment success: ${result.templateId}")
    }
    .exceptionally { error ->
        Log.e("AIFace", "Enrollment failed", error)
        null
    }

// Recognize a face
client.recognize(imageFile)
    .thenAccept { result ->
        Log.i("AIFace", "Matched: ${result.personId} (${result.confidence})")
    }
```

## Status

**v2.1 Scaffold** — Initial package structure and API surface defined. Full REST client implementation pending.

## Upcoming

- TFLite on-device inference for offline recognition
- Camera2 API integration for real-time enrollment/recognition
- Biometric template encryption using Android Keystore
- WorkManager for background model updates
