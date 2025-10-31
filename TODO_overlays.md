# TODO: Add Real-Time Overlays on Webcam Video Feed

## Step 1: Modify RecognizeView.js
- [x] Add a canvas element positioned absolutely over the video element
- [x] Implement drawOverlays function to draw bounding boxes on faces
- [x] Display name and confidence score for matched faces
- [x] Display emotion, age, gender if available
- [x] Update overlays whenever streamResults change
- [x] Style overlays with colors based on emotion or match status

## Step 2: Test Overlays
- [ ] Test bounding box drawing accuracy
- [ ] Test text display (name, confidence, etc.)
- [ ] Test real-time updates
- [ ] Test on different screen sizes

## Step 3: UI Enhancements
- [x] Add toggle for overlay visibility
- [x] Adjust overlay opacity/transparency
- [ ] Handle multiple faces overlapping
