import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, Typography, Grid, Paper, Card, CardContent,
  Button, IconButton, Tooltip, Badge, CircularProgress,
  LinearProgress, Chip, Alert, Dialog, DialogTitle,
  DialogContent, DialogActions, Tabs, Tab, List, ListItem,
  ListItemText, ListItemIcon, Divider, TextField, Select,
  MenuItem, FormControlLabel, Switch, Accordion, AccordionSummary,
  AccordionDetails, Stepper, Step, StepLabel, StepContent,
  Table, TableBody, TableCell, TableHead, TableRow
} from '@mui/material';
import {
  Refresh, Retry, HelpOutline, CheckCircle,
  Error, Warning, Build, psychology, Timeline,
  TrendingUp, People, Security, Memory, AutoAwesome,
  ArrowForward, Settings, History, CompareArrows,
  Insights, BugReport, Download, Upload, Visibility
} from '@mui/icons-material';
import API from '../services/api';

const OperatorWorkflowPanel = ({ recognitionResult, onRetry, onOverride, onEscalate }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [workflowState, setWorkflowState] = useState('idle');
  const [retryCount, setRetryCount] = useState(0);
  const [overrideReason, setOverrideReason] = useState('');
  const [isOverrideDialogOpen, setIsOverrideDialogOpen] = useState(false);
  const [decisionHistory, setDecisionHistory] = useState([]);
  const [recommendedActions, setRecommendedActions] = useState([]);
  const [suggestedThreshold, setSuggestedThreshold] = useState(null);

  useEffect(() => {
    if (recognitionResult) {
      analyzeWorkflowRecommendations();
    }
  }, [recognitionResult]);

  const analyzeWorkflowRecommendations = () => {
    if (!recognitionResult?.faces?.[0]) return;

    const face = recognitionResult.faces[0];
    const actions = [];
    const history = [];

    // Check confidence levels
    if (face.score && face.score < 0.6) {
      actions.push({
        type: 'retry',
        title: 'Retry Recognition',
        description: 'Low confidence score. Consider retrying with better image quality.',
        icon: <Retry />,
        priority: 'high'
      });
    }

    // Check spoof detection
    if (face.spoof_score && face.spoof_score > 0.3) {
      actions.push({
        type: 'investigate',
        title: 'Spoof Investigation',
        description: 'Potential spoof detected. Review liveness indicators.',
        icon: <BugReport />,
        priority: 'critical'
      });
    }

    // Check ambiguity
    if (face.score && face.score >= 0.4 && face.score <= 0.7) {
      actions.push({
        type: 'review',
        title: 'Manual Review',
        description: 'Ambiguous result. Human operator review recommended.',
        icon: <Visibility />,
        priority: 'medium'
      });
    }

    // Add default actions
    actions.push({
      type: 'adjust',
      title: 'Adjust Threshold',
      description: 'Modify sensitivity for this scenario.',
      icon: <Settings />,
      priority: 'low'
    });

    setRecommendedActions(actions);

    // Generate decision history
    history.push({
      action: 'initial_recognition',
      timestamp: new Date().toISOString(),
      confidence: face.score,
      decision: face.score > 0.5 ? 'allow' : 'review'
    });
    setDecisionHistory(history);
  };

  const handleRetry = async (withAdjustments = {}) => {
    setWorkflowState('retrying');
    setRetryCount(prev => prev + 1);

    try {
      if (onRetry) {
        await onRetry(withAdjustments);
      }
      setActiveStep(prev => prev + 1);
      setWorkflowState('success');
    } catch (error) {
      setWorkflowState('error');
    }
  };

  const handleOverride = async () => {
    setIsOverrideDialogOpen(true);
  };

  const confirmOverride = async () => {
    try {
      if (onOverride) {
        await onOverride({ reason: overrideReason, operatorId: 'current-user' });
      }
      setDecisionHistory(prev => [...prev, {
        action: 'operator_override',
        timestamp: new Date().toISOString(),
        reason: overrideReason
      }]);
      setIsOverrideDialogOpen(false);
      setOverrideReason('');
    } catch (error) {
      console.error('Override failed:', error);
    }
  };

  const handleEscalate = async () => {
    try {
      if (onEscalate) {
        await onEscalate({ level: 'supervisor', context: decisionHistory });
      }
      setDecisionHistory(prev => [...prev, {
        action: 'escalated',
        timestamp: new Date().toISOString(),
        target: 'supervisor'
      }]);
    } catch (error) {
      console.error('Escalation failed:', error);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      default: return 'default';
    }
  };

  const steps = [
    { label: 'Initial Recognition', description: 'System processed the biometric input' },
    { label: 'Analysis', description: 'Multi-modal factors evaluated' },
    { label: 'Decision', description: 'Final determination made' }
  ];

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <psychology color="primary" />
          Operator Workflow
        </Typography>
        <Chip
          label={`${retryCount} retries`}
          size="small"
          color={retryCount > 2 ? 'warning' : 'default'}
        />
      </Box>

      {/* Workflow Stepper */}
      <Stepper activeStep={activeStep} orientation="vertical" sx={{ mb: 3 }}>
        {steps.map((step, index) => (
          <Step key={index}>
            <StepLabel>{step.label}</StepLabel>
            <StepContent>
              <Typography variant="body2" color="text.secondary">
                {step.description}
              </Typography>
            </StepContent>
          </Step>
        ))}
      </Stepper>

      {/* Recommended Actions */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>Recommended Actions</Typography>
        <Grid container spacing={1}>
          {recommendedActions.map((action, idx) => (
            <Grid item xs={12} key={idx}>
              <Paper
                sx={{
                  p: 2,
                  cursor: 'pointer',
                  borderLeft: `4px solid`,
                  borderLeftColor: `${getPriorityColor(action.priority)}.main`,
                  bgcolor: action.priority === 'critical' ? 'error.dark' : 'background.paper',
                  '&:hover': { opacity: 0.8 }
                }}
                onClick={() => handleRetry({ type: action.type })}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box sx={{ color: `${getPriorityColor(action.priority)}.main` }}>
                    {action.icon}
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="subtitle2">{action.title}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {action.description}
                    </Typography>
                  </Box>
                  <Chip
                    label={action.priority}
                    size="small"
                    color={getPriorityColor(action.priority)}
                    variant="outlined"
                  />
                </Box>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Decision History */}
      {decisionHistory.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>Decision History</Typography>
          <List dense>
            {decisionHistory.map((entry, idx) => (
              <ListItem key={idx} sx={{ px: 0 }}>
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <History sx={{ fontSize: 16 }} />
                </ListItemIcon>
                <ListItemText
                  primary={entry.action}
                  secondary={new Date(entry.timestamp).toLocaleTimeString()}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {/* Action Buttons */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Button
          variant="contained"
          startIcon={<Retry />}
          onClick={() => handleRetry()}
          disabled={workflowState === 'retrying'}
          fullWidth
        >
          {workflowState === 'retrying' ? 'Retrying...' : 'Retry Recognition'}
        </Button>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<Settings />}
            onClick={() => setSuggestedThreshold(0.5)}
            size="small"
            sx={{ flex: 1 }}
          >
            Adjust Threshold
          </Button>
          <Button
            variant="outlined"
            startIcon={<Visibility />}
            onClick={handleOverride}
            size="small"
            sx={{ flex: 1 }}
          >
            Override
          </Button>
        </Box>

        <Button
          variant="text"
          color="warning"
          startIcon={<Error />}
          onClick={handleEscalate}
          size="small"
        >
          Escalate to Supervisor
        </Button>
      </Box>

      {/* Override Dialog */}
      <Dialog open={isOverrideDialogOpen} onClose={() => setIsOverrideDialogOpen(false)}>
        <DialogTitle>Operator Override</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Please provide a reason for overriding the system decision. This action will be logged.
          </Typography>
          <TextField
            autoFocus
            multiline
            rows={3}
            fullWidth
            label="Override Reason"
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsOverrideDialogOpen(false)}>Cancel</Button>
          <Button onClick={confirmOverride} variant="contained" color="warning">
            Confirm Override
          </Button>
        </DialogActions>
      </Dialog>

      {/* Suggested Threshold Banner */}
      {suggestedThreshold !== null && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            Suggested threshold adjustment: {suggestedThreshold}
            <Button size="small" onClick={() => setSuggestedThreshold(null)} sx={{ ml: 1 }}>
              Dismiss
            </Button>
          </Typography>
        </Alert>
      )}
    </Paper>
  );
};

export default OperatorWorkflowPanel;
