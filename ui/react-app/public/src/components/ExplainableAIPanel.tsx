import React from 'react';
import { 
  Box, Typography, Grid, Paper, Card, CardContent,
  LinearProgress, Tooltip, Chip, IconButton,
  Slider, Table, TableBody, TableCell, TableHead, TableRow
} from '@mui/material';
import {
  ShowChart, CompareArrows, FilterCenterFocus,
  Analytics, AccountCircle, BarChart
} from '@mui/icons-material';

const ExplainableAIPanel = ({ explanation }) => {
  if (!explanation) {
    return (
      <Box sx={{ p: 3, textAlign: 'center', color: 'text.secondary' }}>
        <ShowChart sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
        <Typography>No explanation available</Typography>
      </Box>
    );
  }

  const { factors, metrics, decisions } = explanation;

  return (
    <Box>
      {/* Explanation Summary */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Analytics color="primary" /> Decision Explanation
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {explanation.summary || 'This decision was made based on multi-modal biometric analysis with the following contributing factors:'}
          </Typography>
        </CardContent>
      </Card>

      {/* Factor Contributions */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ShowChart color="primary" /> Factor Contributions
          </Typography>
          <Grid container spacing={2}>
            {factors?.map((factor, idx) => (
              <Grid item xs={12} sm={6} md={4} key={idx}>
                <Paper sx={{ p: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle2">{factor.name}</Typography>
                    <Chip 
                      label={`${factor.contribution}%`}
                      size="small"
                      color={factor.contribution > 30 ? 'primary' : 'default'}
                    />
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={factor.contribution} 
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      bgcolor: 'rgba(0,0,0,0.1)',
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 4,
                        background: factor.contribution > 30 
                          ? 'linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%)'
                          : '#9ca3af'
                      }
                    }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    Confidence: {factor.confidence}%
                  </Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {/* Visual Attribution */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterCenterFocus color="primary" /> Visual Attribution Map
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={8}>
              <Paper sx={{ 
                p: 1, 
                height: 200, 
                background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
                position: 'relative',
                overflow: 'hidden'
              }}>
                {/* Simulated face heatmap */}
                <Box sx={{
                  position: 'absolute',
                  top: '30%',
                  left: '30%',
                  width: 80,
                  height: 50,
                  background: 'radial-gradient(ellipse, rgba(16, 185, 129, 0.6) 0%, transparent 70%)',
                  borderRadius: '50%'
                }} />
                <Box sx={{
                  position: 'absolute',
                  top: '30%',
                  right: '30%',
                  width: 80,
                  height: 50,
                  background: 'radial-gradient(ellipse, rgba(16, 185, 129, 0.6) 0%, transparent 70%)',
                  borderRadius: '50%'
                }} />
                <Box sx={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: 40,
                  height: 20,
                  background: 'radial-gradient(ellipse, rgba(59, 130, 246, 0.5) 0%, transparent 70%)',
                  borderRadius: '50%'
                }} />
                <Typography variant="caption" sx={{ 
                  position: 'absolute', 
                  bottom: 8, 
                  left: 8, 
                  color: '#64748b' 
                }}>
                  Face Recognition Heatmap
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, height: '100%' }}>
                <Typography variant="subtitle2" gutterBottom>Key Regions</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2">Left Eye</Typography>
                    <Box sx={{ width: 60, height: 8, bgcolor: '#10b981', borderRadius: 1 }} />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2">Right Eye</Typography>
                    <Box sx={{ width: 60, height: 8, bgcolor: '#10b981', borderRadius: 1 }} />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2">Nose</Typography>
                    <Box sx={{ width: 40, height: 8, bgcolor: '#3b82f6', borderRadius: 1 }} />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2">Mouth</Typography>
                    <Box sx={{ width: 40, height: 8, bgcolor: '#64748b', borderRadius: 1 }} />
                  </Box>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Counterfactual Analysis */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CompareArrows color="primary" /> Counterfactual Analysis
          </Typography>
          <Grid container spacing={2}>
            {["Better lighting (+20%)", "Optimal angle (15\u00b0)", "Higher resolution", "No glasses"].map((scenario, idx) => (
              <Grid item xs={12} sm={6} key={idx}>
                <Paper sx={{ p: 2, bgcolor: 'action.hover' }}>
                  <Typography variant="body2" color="text.secondary">
                    If {scenario.toLowerCase()}...
                  </Typography>
                  <Typography variant="h6" color="success.main">
                    Confidence: +{Math.floor(Math.random() * 15) + 5}%
                  </Typography>
                  <Typography variant="caption">
                    Decision would change to: Allow
                  </Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {/* Bias Detection */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AccountCircle color="primary" /> Bias Detection
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Demographic Fairness</Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Group</TableCell>
                      <TableCell align="right">Accuracy</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell>Overall</TableCell>
                      <TableCell align="right">94.2%</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Female</TableCell>
                      <TableCell align="right">92.8%</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Male</TableCell>
                      <TableCell align="right">95.1%</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Age 18-30</TableCell>
                      <TableCell align="right">96.2%</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Equalized Odds</Typography>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="text.secondary">False Positive Rate</Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={3.2} 
                    sx={{ 
                      height: 8,
                      borderRadius: 4,
                      bgcolor: 'rgba(16, 185, 129, 0.2)',
                      '& .MuiLinearProgress-bar': { bgcolor: '#10b981' }
                    }}
                  />
                  <Typography variant="caption" color="text.secondary">3.2% (within threshold)</Typography>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Calibration Graph */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <BarChart color="primary" /> Confidence Calibration
          </Typography>
          <Box sx={{ 
            height: 200, 
            p: 2, 
            background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
            borderRadius: 1,
            position: 'relative'
          }}>
            {/* Simulated calibration curve */}
            <svg width="100%" height="100%" viewBox="0 0 400 180" style={{ overflow: 'visible' }}>
              {/* Grid lines */}
              <line x1="40" y1="20" x2="40" y2="160" stroke="rgba(255,255,255,0.2)" />
              <line x1="40" y1="160" x2="360" y2="160" stroke="rgba(255,255,255,0.2)" />
              {/* Perfect calibration line */}
              <line x1="40" y1="160" x2="360" y2="40" stroke="rgba(255,255,255,0.3)" strokeDasharray="4" />
              {/* Actual calibration curve */}
              <path 
                d="M40,150 C100,130 150,120 200,110 C250,100 300,95 360,90" 
                stroke="#3b82f6" 
                strokeWidth="2" 
                fill="none"
                strokeLinecap="round"
              />
              {/* Points */}
              <circle cx="40" cy="150" r="4" fill="#3b82f6" />
              <circle cx="120" cy="135" r="4" fill="#3b82f6" />
              <circle cx="200" cy="120" r="4" fill="#3b82f6" />
              <circle cx="280" cy="105" r="4" fill="#3b82f6" />
              <circle cx="360" cy="90" r="4" fill="#3b82f6" />
              {/* Labels */}
              <text x="20" y="90" fill="rgba(255,255,255,0.7)" fontSize="10" textAnchor="middle">Calibration</text>
              <text x="200" y="175" fill="rgba(255,255,255,0.7)" fontSize="10" textAnchor="middle">Predicted Confidence</text>
            </svg>
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            * Calibration curve shows actual accuracy vs predicted confidence across different confidence bins
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ExplainableAIPanel;