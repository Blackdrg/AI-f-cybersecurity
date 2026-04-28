# ML Pipeline I/O Specifications

This document details the input and output specifications for each stage of the AI-f ML pipeline, including preprocessing steps, file formats, and model expectations.

## Pipeline Overview

The recognition pipeline consists of the following stages:
1. Face Detection
2. Face Embedding
3. Spoof Detection
4. Emotion Detection
5. Age/Gender Estimation
6. Voice Embedding (if provided)
7. Gait Analysis (if provided)
8. Behavioral Analysis (if provided)
9. Multi-Modal Fusion

Each stage processes the output of the previous stage and contributes to the final recognition decision.

---

## 1. Face Detection

**Input:**
- Image: RGB format, any resolution (will be resized internally)
- Accepted file types: JPEG, PNG, BMP, TIFF
- Preprocessing: 
  - Resized to 224x224 pixels (maintaining aspect ratio with padding if necessary)
  - Normalized to [0, 1] range

**Output:**
- Bounding boxes: Array of [x1, y1, x2, y2] coordinates (pixel values)
- Confidence score for each detection
- Model: MTCNN (ResNet-50 backbone)
- File: `models/face_detector.py`

**Notes:**
- Returns the largest face by default if multiple faces are detected
- Minimum face size: 40x40 pixels
- Uses OpenCV for image loading and initial resizing

---

## 2. Face Embedding

**Input:**
- Face image crop: RGB format, from face detection output
- Expected size: 112x112 pixels (will be resized if necessary)
- Preprocessing:
  - Resized to 112x112 pixels
  - Normalized using ImageNet mean and std: 
    - Mean: [0.485, 0.456, 0.406]
    - Std: [0.229, 0.224, 0.225]

**Output:**
- 512-dimensional face embedding vector (float32)
- L2 normalized
- Model: ArcFace (ResNet-100)
- File: `models/face_embedder.py`

**Notes:**
- Output vector is suitable for cosine similarity comparison
- Model trained on MS1M-ArcFace dataset

---

## 3. Spoof Detection

**Input:**
- Face image crop: RGB format, from face detection output
- Expected size: 224x224 pixels (will be resized if necessary)
- Preprocessing:
  - Resized to 224x224 pixels
  - Normalized to [0, 1] range

**Output:**
- Spoof probability: Float between 0.0 (genuine) and 1.0 (spoof)
- Model: CNN texture + depth analysis
- File: `models/spoof_detector.py`

**Notes:**
- Texture analysis uses Local Binary Patterns (LBP)
- Depth analysis uses estimated depth map from monocular depth estimation
- ACER (Average Classification Error Rate) of 0.42% on OULU-NPU dataset

---

## 4. Emotion Detection

**Input:**
- Face image crop: Grayscale format, from face detection output
- Expected size: 48x48 pixels (will be resized if necessary)
- Preprocessing:
  - Converted to grayscale if RGB input
  - Resized to 48x48 pixels
  - Normalized to [0, 1] range

**Output:**
- Probability distribution over 7 emotions: 
  - ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
- Model: VGG-like architecture (FER+ dataset)
- File: `models/emotion_detector.py`

**Notes:**
- F1 score of 0.71 on FER+ dataset
- Output can be used for emotion-based filtering or analytics

---

## 5. Age/Gender Estimation

**Input:**
- Face image crop: RGB format, from face detection output
- Expected size: 112x112 pixels (will be resized if necessary)
- Preprocessing:
  - Resized to 112x112 pixels
  - Normalized using ImageNet mean and std

**Output:**
- Age: Regression output (float, years)
- Gender: Classification output (probability for male/female)
- Model: MobileNetV2
- File: `models/age_gender_estimator.py`

**Notes:**
- Age MAE (Mean Absolute Error) of 3.2 years on Adience dataset
- Gender accuracy approximately 95% on balanced datasets

---

## 6. Voice Embedding

**Input:**
- Audio: 1-second segment of 16kHz mono WAV file
- Accepted formats: WAV (16-bit PCM), MP3 (converted internally)
- Preprocessing:
  - Resampled to 16kHz if necessary
  - Trimmed or padded to exactly 1 second
  - Converted to mel-spectrogram (64 mel bands, 25ms window, 10ms stride)

**Output:**
- 192-dimensional voice embedding vector (float32)
- L2 normalized
- Model: ECAPA-TDNN
- File: `models/voice_embedder.py`

**Notes:**
- EER (Equal Error Rate) of 1.8% on VoxCeleb1 dataset
- Requires voice activity detection (VAD) preprocessing to ensure speech presence

---

## 7. Gait Analysis

**Input:**
- Video: 30 frames of grayscale video (any resolution, will be processed)
- Accepted formats: MP4, AVI, MOV (converted to grayscale internally)
- Preprocessing:
  - Each frame resized to 64x64 pixels
  - Normalized to [0, 1] range
  - OpenPose used to extract key points (if available) or optical flow for motion

**Output:**
- 7-dimensional Hu moments vector (float32)
- Describes gait shape invariants
- Model: OpenPose + Hu moments
- File: `models/gait_analyzer.py`

**Notes:**
- 94.1% accuracy on CASIA-B dataset (subject identification)
- Hu moments are invariant to translation, scale, and rotation
- Requires consistent walking direction (side-view preferred)

---

## 8. Behavioral Analysis

**Input:**
- Temporal sequence: Variable-length sequence of feature vectors from previous frames
- Expected features: 
  - Face movement trajectories
  - Blink rate
  - Head pose variations
  - Micro-expression dynamics
- Preprocessing:
  - Sequences padded or trimmed to fixed length (typically 30 frames)
  - Features normalized per dimension

**Output:**
- 256-dimensional behavior vector (float32)
- Model: LSTM sequence model
- File: `models/behavioral_predictor.py`

**Notes:**
- Trained on spontaneous behavior vs. scripted behavior datasets
- Captures micro-temporal patterns indicative of liveness or intent
- No public accuracy metric available (internal metric only)

---

## 9. Multi-Modal Fusion

**Input:**
- Face similarity score: Float [0, 1] (from face embedding comparison)
- Voice similarity score: Float [0, 1] (if voice provided, else 0)
- Gait similarity score: Float [0, 1] (if gait provided, else 0)
- Behavioral similarity score: Float [0, 1] (if behavior provided, else 0)
- Spoof probability: Float [0, 1] (lower is better, converted to similarity as 1 - spoof_prob)
- Emotion, age/gender: Used for contextual weighting (not directly in fusion score)

**Processing:**
- Weighted sum fusion (weights learned from validation set):
  ```
  final_score = 
      0.6 * face_similarity +
      0.25 * voice_similarity +
      0.15 * gait_similarity
  ```
- Behavioral and other modalities used for risk adjustment and policy decisions
- Spoof detection acts as a gate: if spoof_prob > 0.5, recognition is rejected regardless of similarity

**Output:**
- Final similarity score: Float [0, 1]
- Match decision: Boolean (based on threshold, default 0.6)
- Confidence level: Derived from score distribution
- File: `backend/app/api/recognize.py` (fusion logic)

**Notes:**
- Weights are configurable per organization via policy engine
- Fusion can be adapted to include more modalities as they become available
- Default threshold of 0.6 provides FAR 0.001% and FRR 0.2% (face only)

---

## Data Flow Summary

1. Raw input (image/audio/video) → Preprocessing per modality
2. Face detection → Face crop
3. Face crop → Face embedding, spoof detection, emotion, age/gender
4. Audio → Voice embedding
5. Video → Gait analysis, behavioral analysis
6. All embeddings/scores → Fusion engine
7. Fusion result → Decision engine (threshold + policy checks)
8. Final output → Recognition result with metadata

## Model Versioning

All models are versioned in the `model_versions` database table. The pipeline uses the version marked as `production` for each model type. OTA updates are supported via the model registry.

## Error Handling

Each stage returns specific error codes if input is invalid or processing fails:
- 400: Invalid input format or dimensions
- 422: Semantic error (e.g., no face detected)
- 500: Internal model error
- 503: Model not available (loading failed)

See `docs/error_codes.md` for detailed error code explanations.
