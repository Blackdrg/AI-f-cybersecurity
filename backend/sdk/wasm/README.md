# AIFace SDK for WebAssembly / Browser

TypeScript/JavaScript client for the LEVI-AI face recognition platform, designed for browser-based applications with optional WebAssembly acceleration.

## Requirements

- Modern browser with ES2020+ support
- TypeScript 4.9+
- Optional: WebAssembly runtime for on-device inference (pending)

## Installation

### npm / yarn

```bash
npm install @aif/sdk-wasm
# or
yarn add @aif/sdk-wasm
```

### CDN (Browser global)

```html
<script src="https://unpkg.com/@aif/sdk-wasm/dist/aiface.umd.min.js"></script>
```

## Usage

```typescript
import { createAIFaceClient, AIFaceConfig } from '@aif/sdk-wasm';

const config: AIFaceConfig = {
  apiBaseURL: 'https://api.example.com',
  apiKey: 'your-api-key',
  offlineMode: false
};

const client = createAIFaceClient(config);

// Enroll a face
const imageBlob = await fetch('/face.jpg').then(r => r.blob());
const enrollment = await client.enroll(imageBlob, 'person-123', 'John Doe');
console.log('Enrolled:', enrollment.templateId);

// Recognize a face
const results = await client.recognize(imageBlob, 5);
results.forEach(r => {
  console.log(`Matched ${r.personId}: ${r.confidence * 100:.1f}%`);
});

// Enable offline WASM mode (upcoming)
await client.initWasmModels();
```

## WebAssembly Offline Mode

When `offlineMode: true`, the SDK loads pre-compiled Core ML/TFLite models converted to WASM for on-device inference:

- Face detection via TinyFace / BlazeFace
- Embedding extraction via ResNet-100 (quantized)
- All processing happens locally; no server calls for feature extraction

**Note:** WASM model bundles (~20MB) will be available in v2.1.0 final.

## Status

**v2.1 Scaffold** — TypeScript interface and method signatures defined. REST client implementation pending.

## Upcoming

- Pre-built WASM model bundles via CDN
- WebGL/WebGPU acceleration for matrix operations
- IndexedDB caching of enrolled templates for offline-first operation
- Service Worker integration for PWA support
