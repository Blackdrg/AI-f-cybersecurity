import React, { useState, useEffect } from 'react';
import { Box, Typography, Grid, Paper, Card, CardContent, Tabs, Tab } from '@mui/material';
import ExplainableAIPanel from '../components/ExplainableAIPanel';
import API from '../services/api';

function ExplanationTab() {
  const [explanations, setExplanations] = useState([]);
  const [selectedExplanation, setSelectedExplanation] = useState(null);

  useEffect(() => {
    // Generate sample data if API not available
    const sampleData = {
      summary: 'This recognition decision was made using a multi-modal approach combining facial recognition (62%), voice analysis (25%), and gait analysis (13%).',
      factors: [
        { name: 'Face Recognition', contribution: 62, confidence: 94 },
        { name: 'Voice Analysis', contribution: 25, confidence: 88 },
        { name: 'Gait Analysis', contribution: 13, confidence: 76 }
      ],
      metrics: {
        overallAccuracy: 94.2,
        biasScore: 0.95,
        confidenceVariance: 0.03
      },
      decisions: [
        { type: 'allow', confidence: 0.92, timestamp: new Date().toISOString() }
      ]
    };
    setExplanations([sampleData]);
    setSelectedExplanation(sampleData);
  }, []);

  const [tabValue, setTabValue] = useState(0);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" fontWeight="bold" gutterBottom>
        Explainable AI Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" gutterBottom>
        Comprehensive decision breakdowns, visual attribution maps, and bias detection
      </Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="Decision Breakdown" />
          <Tab label="Visual Attribution" />
          <Tab label="Counterfactuals" />
          <Tab label="Bias Detection" />
          <Tab label="Calibration" />
        </Tabs>
      </Box>

      {selectedExplanation && <ExplainableAIPanel explanation={selectedExplanation} />}

      {!selectedExplanation && (
        <Card sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
          <Typography>Loading explanation data...</Typography>
        </Card>
      )}
    </Box>
  );
}

export default ExplanationTab;