import React, { useRef, useState, useCallback } from 'react';
import { Box, Button, Typography, Paper, CircularProgress } from '@mui/material';
import Webcam from 'react-webcam';
import { CameraAlt, Upload, Refresh } from '@mui/icons-material';

const WebcamCapture = ({ onCapture, isProcessing }) => {
  const webcamRef = useRef(null);
  const [imgSrc, setImgSrc] = useState(null);

  const capture = useCallback(() => {
    const imageSrc = webcamRef.current.getScreenshot();
    setImgSrc(imageSrc);
    
    // Convert base64 to File object
    fetch(imageSrc)
      .then(res => res.blob())
      .then(blob => {
        const file = new File([blob], "webcam.jpg", { type: "image/jpeg" });
        onCapture(file);
      });
  }, [webcamRef, onCapture]);

  const retake = () => {
    setImgSrc(null);
  };

  return (
    <Box sx={{ position: 'relative', width: '100%', maxWidth: 640, margin: '0 auto' }}>
      {imgSrc ? (
        <Box sx={{ position: 'relative' }}>
          <img src={imgSrc} alt="Captured" style={{ width: '100%', borderRadius: 8 }} />
          <Button 
            variant="contained" 
            startIcon={<Refresh />} 
            onClick={retake}
            disabled={isProcessing}
            sx={{ position: 'absolute', bottom: 16, right: 16 }}
          >
            Retake
          </Button>
        </Box>
      ) : (
        <Box sx={{ position: 'relative' }}>
          <Webcam
            audio={false}
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            style={{ width: '100%', borderRadius: 8 }}
          />
          <Button 
            variant="contained" 
            startIcon={<CameraAlt />} 
            onClick={capture}
            disabled={isProcessing}
            sx={{ position: 'absolute', bottom: 16, right: 16 }}
          >
            {isProcessing ? <CircularProgress size={24} color="inherit" /> : "Recognize"}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default WebcamCapture;
