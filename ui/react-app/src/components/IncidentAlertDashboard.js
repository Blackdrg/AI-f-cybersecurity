import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, Typography, Paper, Grid, Card, CardContent,
  Table, TableBody, TableCell, TableHead, TableRow,
  Chip, IconButton, Tooltip, Button, TextField,
  Select, MenuItem, FormControl, InputLabel, Badge,
  Alert, Dialog, DialogTitle, DialogContent,
  DialogActions, Stepper, Step, StepLabel,
  LinearProgress, List, ListItem, ListItemText,
  ListItemIcon, Divider, Snackbar, Tabs, Tab
} from '@mui/material';
import {
  Warning, Error as ErrorIcon, CheckCircle,
  Info, BugReport, Security, Timeline, Flag,
  PlayArrow, Pause, Escalator, Comment, Send,
  Notifications, Settings, Refresh, Search,
  FilterList, BarChart, AccountTree
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import API from '../services/api';

const COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#10b981', '#8b5cf6', '#ec4899'];

export const IncidentAlertDashboard = () => {
  const [alerts, setAlerts] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [incidentWorkflowOpen, setIncidentWorkflowOpen] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  const severityConfig = {
    critical: { color: '#ef4444', label: 'Critical', icon: <ErrorIcon /> },
    high: { color: '#f59e0b', label: 'High', icon: <Warning /> },
    medium: { color: '#3b82f6', label: 'Medium', icon: <Info /> },
    low: { color: '#10b981', label: 'Low', icon: <CheckCircle /> }
  };

  const statusColors = {
    open: '#ef4444',
    investigating: '#f59e0b',
    resolved: '#10b981',
    closed: '#64748b',
    escalated: '#8b5cf6'
  };

  useEffect(() => {
    fetchAlerts();
    fetchIncidents();
    const interval = setInterval(() => {
      fetchAlerts();
      fetchIncidents();
    }, 30000);
    return () => clearInterval(interval);
  }, [filterSeverity, filterStatus]);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      // Try to fetch from backend
      const res = await API.get('/api/alerts/active').catch(() => ({ data: [] }));
      const backendAlerts = res.data || [];
      
      // If no backend alerts, use demo data
      const demoAlerts = generateDemoAlerts();
      setAlerts(backendAlerts.length > 0 ? backendAlerts : demoAlerts);
    } catch (err) {
      setAlerts(generateDemoAlerts());
    } finally {
      setLoading(false);
    }
  };

  const fetchIncidents = async () => {
    try {
      const res = await API.get('/api/incidents').catch(() => ({ data: [] }));
      const backendIncidents = res.data || [];
      const demoIncidents = generateDemoIncidents();
      setIncidents(backendIncidents.length > 0 ? backendIncidents : demoIncidents);
    } catch (err) {
      setIncidents(generateDemoIncidents());
    }
  };

  const generateDemoAlerts = () => {
    const severities = ['critical', 'high', 'medium', 'low'];
    const types = ['DEEPFAKE_DETECTED', 'SPOOFING_ATTEMPT', 'ANOMALY_DETECTED', 'BIAS_THRESHOLD_EXCEEDED', 'CONFIDENCE_DROPOUT'];
    
    return Array.from({ length: 15 }, (_, i) => ({
      id: `alert_${i + 1}`,
      type: types[i % types.length],
      severity: severities[Math.floor(Math.random() * severities.length)],
      message: getAlertMessage(types[i % types.length]),
      timestamp: new Date(Date.now() - Math.random() * 86400000).toISOString(),
      confidence: Math.random() * 0.5 + 0.5,
      source: `CAM-${String(Math.floor(Math.random() * 10) + 1).padStart(3, '0')}`,
      status: Math.random() > 0.7 ? 'reviewed' : 'new',
      affectedEntities: Math.floor(Math.random() * 5) + 1
    }));
  };

  const generateDemoIncidents = () => {
    const statuses = ['open', 'investigating', 'resolved', 'escalated'];
    const types = ['Security Breach Attempt', 'Model Drift Detected', 'Spoofing Campaign', 'Bias Anomaly', 'System Performance Degradation'];
    
    return Array.from({ length: 8 }, (_, i) => ({
      id: `INC-${String(i + 1).padStart(4, '0')}`,
      title: types[i],
      description: getIncidentDescription(types[i]),
      status: statuses[i % statuses.length],
      severity: ['critical', 'high', 'medium'][i % 3],
      createdAt: new Date(Date.now() - Math.random() * 604800000).toISOString(),
      updatedAt: new Date(Date.now() - Math.random() * 86400000).toISOString(),
      assignedTo: ['John Smith', 'Sarah Johnson', 'Mike Chen', null][i % 4],
      priority: ['P1', 'P2', 'P3'][i % 3],
      affectedSystems: ['Recognition Engine', 'Liveness Detection', 'Multi-Modal Fusion'][i % 3],
      relatedAlerts: Math.floor(Math.random() * 10) + 1,
      resolutionSteps: generateResolutionSteps(statuses[i % statuses.length]),
      rootCause: getRootCause(types[i]),
      impact: getImpact(types[i])
    }));
  };

  const getAlertMessage = (type) => {
    const messages = {
      'DEEPFAKE_DETECTED': 'Deepfake video detected in recognition stream',
      'SPOOFING_ATTEMPT': 'Multiple spoofing attempts from same source',
      'ANOMALY_DETECTED': 'Behavioral anomaly detected in recognition pattern',
      'BIAS_THRESHOLD_EXCEEDED': 'Bias score exceeded threshold for demographic group',
      'CONFIDENCE_DROPOUT': 'Significant confidence score drop detected'
    };
    return messages[type] || 'Unknown alert type';
  };

  const getIncidentDescription = (type) => {
    const descriptions = {
      'Security Breach Attempt': 'Multiple unauthorized access attempts detected across recognition endpoints',
      'Model Drift Detected': 'Significant performance degradation in model accuracy over past 24 hours',
      'Spoofing Campaign': 'Coordinated spoofing attack using presentation attacks',
      'Bias Anomaly': 'Unusual bias patterns detected in recent recognition decisions',
      'System Performance Degradation': 'Latency increased by 300% in recognition pipeline'
    };
    return descriptions[type] || 'Incident description not available';
  };

  const getRootCause = (type) => {
    const causes = {
      'Security Breach Attempt': 'Compromised API credentials',
      'Model Drift Detected': 'Data distribution shift in training data',
      'Spoofing Campaign': 'Sophisticated deepfake tools',
      'Bias Anomaly': 'Imbalanced demographic representation',
      'System Performance Degradation': 'Database query optimization needed'
    };
    return causes[type] || 'Under investigation';
  };

  const getImpact = (type) => {
    const impacts = {
      'Security Breach Attempt': 'High - Potential data exposure',
      'Model Drift Detected': 'Medium - Reduced accuracy',
      'Spoofing Campaign': 'Critical - System integrity compromised',
      'Bias Anomaly': 'Medium - Fairness concerns',
      'System Performance Degradation': 'High - Service degradation'
    };
    return impacts[type] || 'Unknown';
  };

  const generateResolutionSteps = (status) => {
    const steps = {
      open: ['Incident logged', 'Initial triage completed'],
      investigating: ['Root cause analysis in progress', 'Containment measures applied'],
      resolved: ['Root cause identified', 'Fix implemented', 'System tested'],
      escalated: ['Escalated to senior team', 'Emergency response initiated']
    };
    return steps[status] || [];
  };

  const handleIncidentClick = (incident) => {
    setSelectedIncident(incident);
    setIncidentWorkflowOpen(true);
  };

  const handleUpdateStatus = async (incidentId, newStatus) => {
    try {
      await API.put(`/api/incidents/${incidentId}/status`, { status: newStatus });
      setIncidents(prev => prev.map(inc => 
        inc.id === incidentId ? { ...inc, status: newStatus, updatedAt: new Date().toISOString() } : inc
      ));
      setSnackbar({ open: true, message: 'Status updated successfully', severity: 'success' });
    } catch (err) {
      setSnackbar({ open: true, message: 'Failed to update status', severity: 'error' });
    }
  };

  const handleAcknowledgeAlert = async (alertId) => {
    try {
      await API.put(`/api/alerts/${alertId}/acknowledge`);
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, status: 'acknowledged' } : a));
      setSnackbar({ open: true, message: 'Alert acknowledged', severity: 'success' });
    } catch (err) {
      setSnackbar({ open: true, message: 'Failed to acknowledge alert', severity: 'error' });
    }
  };

  const filteredAlerts = useMemo(() => {
    return alerts.filter(a => 
      (filterSeverity === 'all' || a.severity === filterSeverity) &&
      (filterStatus === 'all' || a.status === filterStatus)
    );
  }, [alerts, filterSeverity, filterStatus]);

  const filteredIncidents = useMemo(() => {
    return incidents.filter(i => 
      (filterSeverity === 'all' || i.severity === filterSeverity) &&
      (filterStatus === 'all' || i.status === filterStatus)
    );
  }, [incidents, filterSeverity, filterStatus]);

  const alertSummary = useMemo(() => {
    return alerts.reduce((acc, alert) => {
      acc[alert.severity] = (acc[alert.severity] || 0) + 1;
      acc.total = (acc.total || 0) + 1;
      return acc;
    }, {});
  }, [alerts]);

  const incidentSummary = useMemo(() => {
    return incidents.reduce((acc, incident) => {
      acc[incident.status] = (acc[incident.status] || 0) + 1;
      return acc;
    }, {});
  }, [incidents]);

  const chartData = Object.entries(alertSummary).filter(([key]) => key !== 'total').map(([severity, count]) => ({
    name: severity.charAt(0).toUpperCase() + severity.slice(1),
    value: count,
    color: severityConfig[severity]?.color || '#94a3b8'
  }));

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <BugReport color="error" />
          <Typography variant="h6">Incident & Alert Dashboard</Typography>
          <Badge badgeContent={alerts.filter(a => a.status === 'new').length} color="error">
            <Notifications />
          </Badge>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button size="small" startIcon={<Refresh />} onClick={() => { fetchAlerts(); fetchIncidents(); }}>
            Refresh
          </Button>
          <Button size="small" variant="contained" startIcon={<Settings />}>
            Configure Rules
          </Button>
        </Box>
      </Box>

      {/* Tabs */}
      <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)} sx={{ mb: 3 }}>
        <Tab label={`Alerts (${alerts.length})`} />
        <Tab label={`Incidents (${incidents.length})`} />
        <Tab label="Analytics" />
        <Tab label="Response Workflow" />
      </Tabs>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={3}>
              <TextField
                select
                fullWidth
                size="small"
                label="Severity"
                value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}
              >
                <MenuItem value="all">All Severity</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="low">Low</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={3}>
              <TextField
                select
                fullWidth
                size="small"
                label="Status"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <MenuItem value="all">All Status</MenuItem>
                <MenuItem value="new">New</MenuItem>
                <MenuItem value="acknowledged">Acknowledged</MenuItem>
                <MenuItem value="reviewed">Reviewed</MenuItem>
                <MenuItem value="open">Open</MenuItem>
                <MenuItem value="investigating">Investigating</MenuItem>
                <MenuItem value="resolved">Resolved</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search alerts and incidents..."
                InputProps={{
                  startAdornment: <Search fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />
                }}
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {activeTab === 0 && (
        <>
          {/* Alert Summary Cards */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={3}>
              <Card sx={{ bgcolor: 'error.main', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Critical</Typography>
                  <Typography variant="h4">{alertSummary.critical || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card sx={{ bgcolor: 'warning.main', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>High</Typography>
                  <Typography variant="h4">{alertSummary.high || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card sx={{ bgcolor: 'info.main', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Medium</Typography>
                  <Typography variant="h4">{alertSummary.medium || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card sx={{ bgcolor: 'success.main', color: 'white' }}>
                <CardContent>
                  <Typography variant="body2" sx={{ opacity: 0.8 }}>Low</Typography>
                  <Typography variant="h4">{alertSummary.low || 0}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Alert Chart */}
          <Card sx={{ mb: 3, p: 2 }}>
            <Typography variant="subtitle2" gutterBottom>Alert Distribution</Typography>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>

          {/* Alerts Table */}
          <Card>
            <CardContent>
              <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Warning /> Recent Alerts ({filteredAlerts.length})
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Severity</TableCell>
                    <TableCell>Message</TableCell>
                    <TableCell>Source</TableCell>
                    <TableCell>Confidence</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Time</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredAlerts.map((alert) => (
                    <TableRow key={alert.id}>
                      <TableCell>
                        <Chip label={alert.type} size="small" />
                      </TableCell>
                      <TableCell>
                        <Badge
                          badgeContent=""
                          color={alert.severity === 'critical' ? 'error' : alert.severity === 'high' ? 'warning' : alert.severity === 'medium' ? 'info' : 'success'}
                          sx={{
                            '& .MuiBadge-badge': {
                              bgcolor: severityConfig[alert.severity]?.color,
                              width: 8,
                              height: 8,
                              minWidth: 8
                            }
                          }}
                        >
                          <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                            {alert.severity}
                          </Typography>
                        </Badge>
                      </TableCell>
                      <TableCell>{alert.message}</TableCell>
                      <TableCell>{alert.source}</TableCell>
                      <TableCell>{Math.round(alert.confidence * 100)}%</TableCell>
                      <TableCell>
                        <Chip
                          label={alert.status}
                          size="small"
                          color={alert.status === 'new' ? 'error' : alert.status === 'acknowledged' ? 'warning' : 'success'}
                        />
                      </TableCell>
                      <TableCell>{new Date(alert.timestamp).toLocaleString()}</TableCell>
                      <TableCell>
                        {alert.status === 'new' && (
                          <Button size="small" onClick={() => handleAcknowledgeAlert(alert.id)}>
                            Acknowledge
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      {activeTab === 1 && (
        <>
          {/* Incident Workflow Stepper */}
          {selectedIncident && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Incident Response Workflow</Typography>
                <Stepper activeStep={['open', 'investigating', 'resolved', 'closed'].indexOf(selectedIncident.status)} alternativeLabel>
                  <Step><StepLabel onClick={() => selectedIncident.status !== 'open' && handleUpdateStatus(selectedIncident.id, 'open')}>Open</StepLabel></Step>
                  <Step><StepLabel onClick={() => selectedIncident.status !== 'investigating' && handleUpdateStatus(selectedIncident.id, 'investigating')}>Investigating</StepLabel></Step>
                  <Step><StepLabel onClick={() => selectedIncident.status !== 'resolved' && handleUpdateStatus(selectedIncident.id, 'resolved')}>Resolved</StepLabel></Step>
                  <Step><StepLabel onClick={() => selectedIncident.status !== 'closed' && handleUpdateStatus(selectedIncident.id, 'closed')}>Closed</StepLabel></Step>
                </Stepper>
              </CardContent>
            </Card>
          )}

          {/* Incidents Table */}
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Flag /> Active Incidents ({filteredIncidents.length})
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Title</TableCell>
                    <TableCell>Severity</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Priority</TableCell>
                    <TableCell>Assigned</TableCell>
                    <TableCell>Related Alerts</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredIncidents.map((incident) => (
                    <TableRow key={incident.id} hover onClick={() => handleIncidentClick(incident)} style={{ cursor: 'pointer' }}>
                      <TableCell><Typography variant="body2" fontFamily="monospace">{incident.id}</Typography></TableCell>
                      <TableCell>{incident.title}</TableCell>
                      <TableCell>
                        <Badge
                          badgeContent=""
                          color={incident.severity === 'critical' ? 'error' : incident.severity === 'high' ? 'warning' : 'info'}
                          sx={{
                            '& .MuiBadge-badge': {
                              bgcolor: severityConfig[incident.severity]?.color,
                              width: 8,
                              height: 8,
                              minWidth: 8
                            }
                          }}
                        >
                          <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                            {incident.severity}
                          </Typography>
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={incident.status}
                          size="small"
                          sx={{
                            bgcolor: statusColors[incident.status] + '20',
                            color: statusColors[incident.status],
                            border: `1px solid ${statusColors[incident.status]}`
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip label={incident.priority} size="small" color={incident.priority === 'P1' ? 'error' : incident.priority === 'P2' ? 'warning' : 'default'} />
                      </TableCell>
                      <TableCell>{incident.assignedTo || '-'}</TableCell>
                      <TableCell>{incident.relatedAlerts}</TableCell>
                      <TableCell>{new Date(incident.createdAt).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <Button size="small">Details</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      {activeTab === 2 && (
        <>
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <Card sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Alerts Over Time</Typography>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={[...Array(24).keys()].map(hour => ({
                    hour: `${hour}:00`,
                    alerts: Math.floor(Math.random() * 20) + 5,
                    critical: Math.floor(Math.random() * 5)
                  }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis dataKey="hour" stroke="#94a3b8" fontSize={12} />
                    <YAxis stroke="#94a3b8" fontSize={12} />
                    <RechartsTooltip />
                    <Line type="monotone" dataKey="alerts" stroke="#3b82f6" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="critical" stroke="#ef4444" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card sx={{ p: 2, height: '100%' }}>
                <Typography variant="subtitle2" gutterBottom>Incident Types</Typography>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Security', value: 35, color: '#ef4444' },
                        { name: 'Model Drift', value: 25, color: '#f59e0b' },
                        { name: 'Performance', value: 20, color: '#3b82f6' },
                        { name: 'Bias', value: 20, color: '#8b5cf6' }
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {([{ color: '#ef4444' }, { color: '#f59e0b' }, { color: '#3b82f6' }, { color: '#8b5cf6' }]).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
                <List dense sx={{ mt: 2 }}>
                  <ListItem><ListItemIcon><Box sx={{ width: 10, height: 10, bgcolor: '#ef4444', borderRadius: '50%' }} /></ListItemIcon><ListItemText primary="Security" secondary="35%" /></ListItem>
                  <ListItem><ListItemIcon><Box sx={{ width: 10, height: 10, bgcolor: '#f59e0b', borderRadius: '50%' }} /></ListItemIcon><ListItemText primary="Model Drift" secondary="25%" /></ListItem>
                  <ListItem><ListItemIcon><Box sx={{ width: 10, height: 10, bgcolor: '#3b82f6', borderRadius: '50%' }} /></ListItemIcon><ListItemText primary="Performance" secondary="20%" /></ListItem>
                  <ListItem><ListItemIcon><Box sx={{ width: 10, height: 10, bgcolor: '#8b5cf6', borderRadius: '50%' }} /></ListItemIcon><ListItemText primary="Bias" secondary="20%" /></ListItem>
                </List>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Mean Time to Resolution (MTTR)</Typography>
                <Box sx={{ textAlign: 'center', py: 3 }}>
                  <Typography variant="h3" color="primary">2.4h</Typography>
                  <Typography variant="body2" color="text.secondary">↓ 15% from last week</Typography>
                </Box>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Incident Escalation Rate</Typography>
                <Box sx={{ textAlign: 'center', py: 3 }}>
                  <Typography variant="h3" color="success">8.2%</Typography>
                  <Typography variant="body2" color="text.secondary">↓ 5% from last week</Typography>
                </Box>
              </Card>
            </Grid>
          </Grid>
        </>
      )}

      {activeTab === 3 && (
        <Box>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Standard incident response workflow with automated escalation
          </Typography>
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Stepper activeStep={1} alternativeLabel>
                <Step><StepLabel>Detection</StepLabel></Step>
                <Step><StepLabel>Triage</StepLabel></Step>
                <Step><StepLabel>Investigation</StepLabel></Step>
                <Step><StepLabel>Resolution</StepLabel></Step>
              </Stepper>
            </CardContent>
          </Card>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Button fullWidth variant="contained" startIcon={<PlayArrow />} sx={{ mb: 1 }}>Start Investigation</Button>
              <Button fullWidth variant="outlined" startIcon={<Escalator />} sx={{ mb: 1 }}>Escalate</Button>
              <Button fullWidth variant="outlined" startIcon={<Comment />}>Add Note</Button>
            </Grid>
            <Grid item xs={12} md={8}>
              <Card sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>Incident Timeline</Typography>
                <List dense>
                  <ListItem>
                    <ListItemIcon><Timeline /></ListItemIcon>
                    <ListItemText primary="Incident created" secondary="2 hours ago" />
                  </ListItem>
                  <Divider />
                  <ListItem>
                    <ListItemIcon><Security /></ListItemIcon>
                    <ListItemText primary="Automated containment applied" secondary="1 hour 45m ago" />
                  </ListItem>
                  <Divider />
                  <ListItem>
                    <ListItemIcon><AccountTree /></ListItemIcon>
                    <ListItemText primary="Assigned to: Security Team" secondary="1 hour 30m ago" />
                  </ListItem>
                </List>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Incident Detail Dialog */}
      <Dialog open={incidentWorkflowOpen} onClose={() => setIncidentWorkflowOpen(false)} maxWidth="md" fullWidth>
        {selectedIncident && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">{selectedIncident.title}</Typography>
                <Box>
                  <Chip label={selectedIncident.priority} color={selectedIncident.priority === 'P1' ? 'error' : 'warning'} sx={{ mr: 1 }} />
                  <Badge badgeContent={selectedIncident.relatedAlerts} color="error">
                    <BugReport />
                  </Badge>
                </Box>
              </Box>
            </DialogTitle>
            <DialogContent>
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">ID</Typography>
                  <Typography variant="body1" fontFamily="monospace">{selectedIncident.id}</Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Severity</Typography>
                  <Badge
                    badgeContent=""
                    color={selectedIncident.severity === 'critical' ? 'error' : 'warning'}
                    sx={{
                      '& .MuiBadge-badge': {
                        bgcolor: severityConfig[selectedIncident.severity]?.color,
                        width: 8,
                        height: 8,
                        minWidth: 8
                      }
                    }}
                  >
                    <Typography variant="body1" sx={{ textTransform: 'capitalize' }}>
                      {selectedIncident.severity}
                    </Typography>
                  </Badge>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Status</Typography>
                  <Chip
                    label={selectedIncident.status}
                    sx={{
                      bgcolor: statusColors[selectedIncident.status] + '20',
                      color: statusColors[selectedIncident.status],
                      border: `1px solid ${statusColors[selectedIncident.status]}`
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Assigned To</Typography>
                  <Typography variant="body1">{selectedIncident.assignedTo || 'Unassigned'}</Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Created</Typography>
                  <Typography variant="body1">{new Date(selectedIncident.createdAt).toLocaleString()}</Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Last Updated</Typography>
                  <Typography variant="body1">{new Date(selectedIncident.updatedAt).toLocaleString()}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">Description</Typography>
                  <Typography variant="body1">{selectedIncident.description}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">Root Cause</Typography>
                  <Typography variant="body1">{selectedIncident.rootCause}</Typography>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">Impact</Typography>
                  <Typography variant="body1">{selectedIncident.impact}</Typography>
                </Grid>
              </Grid>

              {selectedIncident.resolutionSteps.length > 0 && (
                <>
                  <Typography variant="subtitle2" gutterBottom>Resolution Steps</Typography>
                  <List dense>
                    {selectedIncident.resolutionSteps.map((step, i) => (
                      <ListItem key={i}>
                        <ListItemIcon><CheckCircle color="success" fontSize="small" /></ListItemIcon>
                        <ListItemText primary={step} />
                      </ListItem>
                    ))}
                  </List>
                </>
              )}
            </DialogContent>
            <DialogActions>
              {selectedIncident.status !== 'resolved' && (
                <Button onClick={() => handleUpdateStatus(selectedIncident.id, 'resolved')} color="success">
                  Mark Resolved
                </Button>
              )}
              {selectedIncident.status !== 'closed' && (
                <Button onClick={() => handleUpdateStatus(selectedIncident.id, 'closed')}>
                  Close Incident
                </Button>
              )}
              <Button onClick={() => setIncidentWorkflowOpen(false)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Paper>
  );
};

export default IncidentAlertDashboard;