import React, { useState } from 'react';
import API from '../services/api';
import { Stepper, Step, StepLabel, Button, Typography, Box, Paper, TextField } from '@mui/material';

const steps = ['Connect Camera', 'Add Users', 'Configure Alerts', 'Go Live'];

export default function SetupWizard({ onComplete }) {
  const [activeStep, setActiveStep] = useState(0);
  const [rtspUrl, setRtspUrl] = useState('');
  const [testStatus, setTestStatus] = useState(null);

  const handleTestConnection = async () => {
    setTestStatus('testing');
    try {
      await API.post('/api/orgs/cameras/test-connection', { rtsp_url: rtspUrl });
      setTestStatus('success');
    } catch (err) {
      setTestStatus('failed');
    }
  };

  const handleNext = () => {
    if (activeStep === steps.length - 1) {
      if (onComplete) onComplete();
    } else {
      setActiveStep((prev) => prev + 1);
    }
  };
  const handleBack = () => setActiveStep((prev) => prev - 1);

  const getStepContent = (step) => {
    switch (step) {
      case 0:
        return (
          <Box sx={{ mt: 2 }}>
            <Typography>Enter your RTSP Stream URL:</Typography>
            <TextField 
              fullWidth 
              margin="normal" 
              label="RTSP URL" 
              placeholder="rtsp://admin:pass@192.168.1.100:554/live" 
              value={rtspUrl}
              onChange={(e) => setRtspUrl(e.target.value)}
            />
            <Button 
              variant="contained" 
              color={testStatus === 'success' ? 'success' : 'secondary'} 
              sx={{ mt: 1 }}
              onClick={handleTestConnection}
              disabled={testStatus === 'testing'}
            >
              {testStatus === 'testing' ? 'Testing...' : testStatus === 'success' ? 'Connected!' : 'Test Connection'}
            </Button>
            {testStatus === 'failed' && (
              <Typography color="error" variant="caption" display="block" sx={{ mt: 1 }}>
                Connection failed. Please check the URL and credentials.
              </Typography>
            )}
          </Box>
        );
      case 1:
        return (
          <Box sx={{ mt: 2 }}>
            <Typography>Upload CSV or Enroll first user:</Typography>
            <Button variant="outlined" sx={{ mt: 1 }}>Upload Employees CSV</Button>
          </Box>
        );
      case 2:
        return (
          <Box sx={{ mt: 2 }}>
            <Typography>Select notification channels:</Typography>
            <TextField fullWidth margin="normal" label="Slack Webhook" />
            <TextField fullWidth margin="normal" label="Admin Email" />
          </Box>
        );
      case 3:
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="h6" color="success.main">System Ready!</Typography>
            <Typography>Your enterprise face recognition engine is calibrated and active.</Typography>
          </Box>
        );
      default:
        return 'Unknown step';
    }
  };

  return (
    <Paper sx={{ p: 4, maxWidth: 600, mx: 'auto', mt: 4 }}>
      <Typography variant="h4" align="center" gutterBottom>Enterprise Setup Wizard</Typography>
      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {steps.map((label) => (
          <Step key={label}><StepLabel>{label}</StepLabel></Step>
        ))}
      </Stepper>
      <Box sx={{ minHeight: 200 }}>
        {getStepContent(activeStep)}
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 4 }}>
        <Button disabled={activeStep === 0} onClick={handleBack} sx={{ mr: 1 }}>Back</Button>
        <Button variant="contained" onClick={handleNext}>
          {activeStep === steps.length - 1 ? 'Finish' : 'Next'}
        </Button>
      </Box>
    </Paper>
  );
}
