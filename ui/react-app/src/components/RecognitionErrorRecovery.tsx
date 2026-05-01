import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Alert, Button,
  LinearProgress, Chip, List, ListItem, ListItemText,
  ListItemIcon, Divider, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, Grid, Paper, IconButton, Tooltip
} from '@mui/material';
import {
  Error as ErrorIcon,
  Warning,
  Refresh,
  BugReport,
  Security,
  Info,
  PlayArrow,
  Settings,
  Timeline,
  CompareArrows,
  Description
} from '@mui/icons-material';
import API from '../services/api';

const ERROR_CATEGORIES = {
  SPOOF_DETECTED: {
    icon: <BugReport />,
    color: 'error',
    title: 'Spoof Attack Detected',
    description: 'Liveness check failed - potential fake or replay attack'
  },
  LOW_CONFIDENCE: {
    icon: <Warning />,
    color: 'warning',
    title: 'Low Recognition Confidence',
    description: 'Match confidence below threshold'
  },
  NO_MATCH: {
    icon: <Security />,
    color: 'info',
    title: 'No Identity Match',
    description: 'Face not found in database'
  },
  QUALITY_ISSUE: {
    icon: <Info />,
    color: 'warning',
    title: 'Image Quality Issue',
    description: 'Poor image resolution or lighting'
  },
  MULTI_FACE: {
    icon: <Info />,
    color: 'warning',
    title: 'Multiple Faces Detected',
    description: 'Ambiguous - multiple faces in frame'
  }
};

const RECOVERY_ACTIONS = {
  RETRY_WITH_ADJUSTMENT: {
    label: 'Retry with Adjustments',
    icon: <Refresh />,
    color: 'primary'
  },
  MANUAL_THRESHOLD_ADJUST: {
    label: 'Adjust Threshold',
    icon: <Settings />,
    color: 'secondary'
  },
  MANUAL_RECOGNITION: {
    label: 'Manual Review',
    icon: <Description />,
    color: 'warning'
  },
  RETRY_ORIGINAL: {
    label: 'Retry Original',
    icon: <PlayArrow />,
    color: 'success'
  }
};

const RecognitionErrorRecovery = ({
  recognitionResult,
  onRecoveryComplete,
  onEscalate,
  onErrorResolve
}) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [recoveryDialogOpen, setRecoveryDialogOpen] = useState(false);  const [selectedError, setSelectedError] = useState(null);
  const [recoveryPlan, setRecoveryPlan] = useState([]);
  const [suggestedActions, setSuggestedActions] = useState([]);
  const [diagnostics, setDiagnostics] = useState(null);
  const [resolutionDialogOpen, setResolutionDialogOpen] = useState(false);
  const [resolutionNote, setResolutionNote] = useState('');

  useEffect(() => {
    if (recognitionResult?.faces?.[0]) {
      analyzeError(recognitionResult.faces[0]);
    }
  }, [recognitionResult]);

  const analyzeError = async (face) => {
    setIsAnalyzing(true);
    
    const errors = [];
    const suggestedActions = [];

    // Check for spoof detection
    if (face.spoof_score > 0.5) {
      errors.push({
        category: 'SPOOF_DETECTED',
        severity: 'critical',
        score: face.spoof_score,
        message: `Spoof detected with ${(face.spoof_score * 100).toFixed(1)}% confidence`,
        details: {
          liveness_score: 1 - face.spoof_score,
          reconstruction_confidence: face.reconstruction_confidence
        }
      });
      
      suggestedActions.push({
        ...RECOVERY_ACTIONS.MANUAL_RECOGNITION,
        action: 'manual_review',
        reason: 'Spoof detection requires human verification'
      });
    }

    // Check confidence levels
    if (face.score < 0.4) {
      errors.push({
        category: 'NO_MATCH',
        severity: 'info',
        score: face.score,
        message: `No match found (confidence: ${(face.score * 100).toFixed(1)}%)`,
        details: { match_count: face.matches?.length || 0 }
      });
      
      suggestedActions.push({
        ...RECOVERY_ACTIONS.RETRY_WITH_ADJUSTMENT,
        action: 'retry_lower_threshold',
        threshold_suggestion: 0.3,
        reason: 'Consider lowering threshold for broader search'
      });
    } else if (face.score < 0.6) {
      errors.push({
        category: 'LOW_CONFIDENCE',
        severity: 'warning',
        score: face.score,
        message: `Low confidence match (${(face.score * 100).toFixed(1)}%)`,
        details: { threshold_breach: 0.6 - face.score }
      });
      
      suggestedActions.push(
        {
          ...RECOVERY_ACTIONS.RETRY_WITH_ADJUSTMENT,
          action: 'request_better_image',
          reason: 'Request higher quality image'
        },
        {
          ...RECOVERY_ACTIONS.MANUAL_THRESHOLD_ADJUST,
          action: 'adjust_threshold',
          threshold_suggestion: 0.5,
          reason: 'Temporarily lower threshold for verification'
        }
      );
    }

    // Check image quality indicators
    if (face.reconstruction_confidence && face.reconstruction_confidence < 0.7) {
      errors.push({
        category: 'QUALITY_ISSUE',
        severity: 'warning',
        score: face.reconstruction_confidence,
        message: 'Poor 3D reconstruction quality',
        details: { reconstruction_confidence: face.reconstruction_confidence }
      });
      
      suggestedActions.push({
        ...RECOVERY_ACTIONS.RETRY_WITH_ADJUSTMENT,
        action: 'request_better_lighting',
        reason: 'Suggest better lighting conditions'
      });
    }

    // If no specific error but still unclear
    if (errors.length === 0 && face.score && face.score < 0.7) {
      errors.push({
        category: 'AMBIGUOUS',
        severity: 'warning',
        score: face.score,
        message: 'Ambiguous recognition result',
        details: { confidence_range: '0.4 - 0.7' }
      });
      
      suggestedActions.push({
        ...RECOVERY_ACTIONS.MANUAL_RECOGNITION,
        action: 'manual_review',
        reason: 'Result requires human judgment'
      });
    }

    setDiagnostics({
      total_errors: errors.length,
      max_severity: errors.length > 0 ? 
        errors.reduce((max, e) => {
          const order = { critical: 4, high: 3, medium: 2, low: 1, info: 0, warning: 2 };
          return (order[e.severity] || 0) > (order[max] || 0) ? e.severity : max;
        }, 'info') : 'success',
      error_categories: [...new Set(errors.map(e => e.category))]
    });

    setRecoveryPlan(errors);
    setSuggestedActions(suggestedActions);
    setIsAnalyzing(false);
  };

  const getSeverityColor = (severity) => {
    const colors = {
      critical: '#ef4444',
      high: '#f59e0b',
      medium: '#fbbf24',
      low: '#10b981',
      info: '#3b82f6',
      warning: '#f59e0b',
      success: '#10b981'
    };
    return colors[severity] || colors.info;
  };

  const handleRecoveryAction = async (action) => {
    setRecoveryDialogOpen(false);
    
    try {
      let result;
      switch (action.action) {
        case 'retry_lower_threshold':
          result = await API.post('/api/recognize/retry', {
            original_request: recognitionResult?.request,
            threshold: action.threshold_suggestion || 0.3
          });
          break;
        case 'manual_review':
          result = await API.post('/api/review/queue', {
            recognition_id: recognitionResult?.request_id,
            reason: action.reason
          });
          break;
        case 'adjust_threshold':
          result = await API.post('/api/recognize/override', {
            recognition_id: recognitionResult?.request_id,
            new_threshold: action.threshold_suggestion
          });
          break;
        default:
          result = await API.post('/api/recognize/retry', {
            original_request: recognitionResult?.request
          });
      }
      
      onRecoveryComplete && onRecoveryComplete(result.data);
    } catch (err) {
      console.error('Recovery action failed:', err);
    }
  };

  const handleEscalation = async () => {
    try {
      await API.post('/api/escalations/create', {
        recognition_id: recognitionResult?.request_id,
        errors: recoveryPlan,
        suggested_actions: suggestedActions,
        level: 'supervisor'
      });
      
      onEscalate && onEscalate({
        errors: recoveryPlan,
        level: 'supervisor'
      });
    } catch (err) {
      console.error('Escalation failed:', err);
    }
  };

  const resolveError = async () => {
    setResolutionDialogOpen(false);
    try {
      await API.post('/api/errors/resolve', {
        recognition_id: recognitionResult?.request_id,
        resolution: resolutionNote,
        resolved_by: 'operator'
      });
      
      onErrorResolve && onErrorResolve({
        id: recognitionResult?.request_id,
        resolved: true,
        note: resolutionNote
      });
    } catch (err) {
      console.error('Resolution failed:', err);
    }
  };

  if (!recognitionResult || !recoveryPlan.length) {
    return null;
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Card sx={{ mb: 2, borderLeft: `4px solid ${getSeverityColor(diagnostics?.max_severity)}` }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {diagnostics?.max_severity === 'success' ? (
                <ErrorIcon color="success" />
              ) : (
                <BugReport color={getSeverityColor(diagnostics?.max_severity)} />
              )}
              <Typography variant="h6">
                {diagnostics?.max_severity === 'success' 
                  ? 'Recognition Successful' 
                  : `Issues Detected (${diagnostics?.total_errors})`
                }
              </Typography>
            </Box>
            {isAnalyzing && <CircularProgress size={20} />}
          </Box>

          {/* Error List */}
          <Stack spacing={1} sx={{ mb: 2 }}>
            {recoveryPlan.map((error, idx) => {
              const category = ERROR_CATEGORIES[error.category] || ERROR_CATEGORIES.QUALITY_ISSUE;
              return (
                <Alert
                  key={idx}
                  severity={error.severity}
                  icon={category.icon}
                  sx={{ 
                    borderLeft: `4px solid ${getSeverityColor(error.severity)}`,
                    '& .MuiAlert-icon': {
                      color: getSeverityColor(error.severity)
                    }
                  }}
                >
                  <Box sx={{ width: '100%' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                      <Typography variant="subtitle2">{category.title}</Typography>
                      <Chip
                        label={`${(error.score * 100).toFixed(1)}%`}
                        size="small"
                        sx={{
                          bgcolor: `${getSeverityColor(error.severity)}33`,
                          color: getSeverityColor(error.severity)
                        }}
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {category.description}
                    </Typography>
                    {error.message !== category.title && (
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                        {error.message}
                      </Typography>
                    )}
                  </Box>
                </Alert>
              );
            })}
          </Stack>

          {/* Suggested Actions */}
          {suggestedActions.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Suggested Actions
              </Typography>
              <Grid container spacing={1}>
                {suggestedActions.map((action, idx) => (
                  <Grid item key={idx}>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={action.icon}
                      onClick={() => {
                        setSelectedError(action);
                        setRecoveryDialogOpen(true);
                      }}
                      sx={{
                        textTransform: 'none',
                        fontSize: '0.8rem',
                        py: 0.5
                      }}
                    >
                      {action.label}
                    </Button>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}

          {/* Action Buttons */}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              startIcon={<Refresh />}
              size="small"
              onClick={() => {
                setSelectedError(RECOVERY_ACTIONS.RETRY_ORIGINAL);
                setRecoveryDialogOpen(true);
              }}
            >
              Retry
            </Button>
            <Button
              variant="outlined"
              startIcon={<Settings />}
              size="small"
              onClick={() => {
                setSelectedError(RECOVERY_ACTIONS.MANUAL_THRESHOLD_ADJUST);
                setRecoveryDialogOpen(true);
              }}
            >
              Adjust Settings
            </Button>
            <Button
              variant="outlined"
              startIcon={<BugReport />}
              size="small"
              color="warning"
              onClick={handleEscalation}
            >
              Escalate
            </Button>
            <Button
              variant="outlined"
              startIcon={<Description />}
              size="small"
              onClick={() => setResolutionDialogOpen(true)}
            >
              Mark Resolved
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Recovery Action Dialog */}
      <Dialog open={recoveryDialogOpen} onClose={() => setRecoveryDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Recovery Action</DialogTitle>
        <DialogContent>
          {selectedError && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Action: {selectedError.label}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {selectedError.reason}
              </Typography>
              {selectedError.threshold_suggestion !== undefined && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Suggested threshold: {selectedError.threshold_suggestion}
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRecoveryDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => handleRecoveryAction(selectedError)}
            startIcon={<PlayArrow />}
          >
            Execute
          </Button>
        </DialogActions>
      </Dialog>

      {/* Resolution Dialog */}
      <Dialog open={resolutionDialogOpen} onClose={() => setResolutionDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Mark as Resolved</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Document the resolution for audit purposes
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Resolution Note"
            value={resolutionNote}
            onChange={(e) => setResolutionNote(e.target.value)}
            placeholder="Describe how this recognition issue was resolved..."
            size="small"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResolutionDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={resolveError} disabled={!resolutionNote.trim()}>
            Confirm Resolution
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RecognitionErrorRecovery;
