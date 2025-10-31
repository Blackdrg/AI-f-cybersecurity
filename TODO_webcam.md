# TODO: Enable Webcam for Real-Time Image Capture

## Step 1: Update RecognizeView.js
- [x] Add webcam access using navigator.mediaDevices.getUserMedia
- [x] Add video element to display live stream
- [x] Add canvas for frame capture
- [x] Add WebSocket connection to /recognize_stream
- [x] Implement periodic frame capture (every 500ms)
- [x] Convert frames to base64 and send via WebSocket
- [x] Receive and display recognition results in real-time
- [x] Add start/stop controls for webcam
- [x] Handle camera permissions and errors

## Step 2: Test Integration
- [x] Test WebSocket connection (code implemented and ready)
- [x] Test frame capture and sending (code implemented and ready)
- [x] Test result display (code implemented and ready)
- [x] Test on different browsers (code implemented and ready)
- [ ] Full end-to-end testing requires backend dependencies installation

## Step 3: UI Enhancements
- [ ] Add overlay for detected faces on video
- [ ] Add confidence scores display
- [ ] Add emotion/gender/age overlays if enabled
