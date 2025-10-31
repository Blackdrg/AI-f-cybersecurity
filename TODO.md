# TODO: Make Webcam and Enrollment Features Fully Working

## Step 1: Fix Backend Database Integration
- [ ] Uncomment and fix database calls in `backend/app/api/stream_recognize.py`
- [ ] Ensure asyncpg is properly installed and configured
- [ ] Test database connectivity in stream recognition

## Step 2: Verify Model Dependencies
- [ ] Check if all ML models (face_detector, embedder, etc.) are properly loaded
- [ ] Add fallbacks for missing dependencies in models
- [ ] Ensure OpenCV and other libraries are available

## Step 3: Update Enrollment API
- [ ] Verify enrollment works with database
- [ ] Test multi-modal enrollment (face, voice, gait)
- [ ] Ensure consent handling is correct

## Step 4: Test Integration
- [ ] Run docker-compose to start all services
- [ ] Test enrollment via UI
- [ ] Test webcam recognition via UI
- [ ] Verify WebSocket streaming works

## Step 5: UI Enhancements
- [ ] Add error handling for camera permissions
- [ ] Improve overlays on video stream
- [ ] Add loading states and feedback

## Step 6: End-to-End Testing
- [ ] Enroll a person
- [ ] Use webcam to recognize the person
- [ ] Verify results display correctly
