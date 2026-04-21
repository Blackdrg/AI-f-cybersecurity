import React, { useState } from 'react';
import { Box, Grid, Paper, Typography, Tab, Tabs, Alert, CircularProgress } from '@mui/material';
import { CameraAlt, PhotoLibrary } from '@mui/icons-material';
import WebcamCapture from '../components/WebcamCapture';
import UploadBox from '../components/UploadBox';
import ResultCard from '../components/ResultCard';
import { recognize } from '../services/api';

const RecognizePage = () => {
  const [tab, setTab] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [timeTaken, setTimeTaken] = useState(0);

  const handleRecognize = async (file) => {
    setIsProcessing(true);
    setError(null);
    setResult(null);
    
    try {
      const start = performance.now();
      const res = await recognize(file);
      const end = performance.now();
      
      setResult(res.data);
      setTimeTaken((end - start) / 1000);
    } catch (err) {
      setError(err.message || "Failed to recognize face");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Face Recognition</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <Paper sx={{ p: 2 }}>
            <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 2 }}>
              <Tab icon={<CameraAlt />} label="Webcam" />
              <Tab icon={<PhotoLibrary />} label="Upload" />
            </Tabs>
            
            {tab === 0 ? (
              <WebcamCapture onCapture={handleRecognize} isProcessing={isProcessing} />
            ) : (
              <UploadBox onUpload={handleRecognize} isProcessing={isProcessing} />
            )}
            
            {isProcessing && (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mt: 4, flexDirection: 'column' }}>
                <CircularProgress sx={{ mb: 2 }} />
                <Typography>Analyzing face characteristics...</Typography>
              </Box>
            )}
            
            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
            )}
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={5}>
          <Paper sx={{ p: 3, height: '100%', minHeight: 400 }}>
            <Typography variant="h6" gutterBottom>Recognition Results</Typography>
            {result ? (
              <ResultCard data={result} timeTaken={timeTaken} />
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '80%', opacity: 0.5, flexDirection: 'column' }}>
                <CameraAlt sx={{ fontSize: 48, mb: 2 }} />
                <Typography>Results will appear here</Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default RecognizePage;
