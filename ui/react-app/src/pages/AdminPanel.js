/* Enhanced Admin Panel with Enterprise Features */
import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Grid, Paper, List, ListItem, ListItemText, 
  Divider, Button, TextField, Dialog, DialogTitle, DialogContent, DialogActions,
  Chip, Table, TableBody, TableCell, TableHead, TableRow, Card, CardContent,
  Tabs, Tab, Alert, LinearProgress, IconButton, Tooltip, Switch,
  FormControlLabel, Select, MenuItem, InputAdornment, CircularProgress
} from '@mui/material';
import { 
  VpnKey, Business, People, Receipt, Shield, Gavel, 
  Security, TrendingUp, BugReport, Public, Key, 
  Settings, Analytics, Timeline, Radar, Database,
  Eye, Brain, AlertCircle, CheckCircle, Error as ErrorIcon,
  PlayArrow, Pause, History, BarChart, Article, CompareArrows
} from '@mui/icons-material';
import API from '../services/api';

// Lazy-loaded components
const OperatorWorkflowPanel = React.lazy(() => 
  import('../components/OperatorWorkflowPanel').catch(() => ({ default: () => <Box>Component unavailable</Box> }))
);
const ExplainableAIPanel = React.lazy(() => 
  import('../components/ExplainableAIPanel').catch(() => ({ default: () => <Box>Component unavailable</Box> }))
);
const DashboardIntelligencePanel = React.lazy(() => 
  import('../components/DashboardIntelligencePanel').catch(() => ({ default: () => <Box>Component unavailable</Box> }))
);
const EnrichmentPortalPanel = React.lazy(() => 
  import('../components/EnrichmentPortalPanel').catch(() => ({ default: () => <Box>Component unavailable</Box> }))
);
const RecognitionErrorRecovery = React.lazy(() => 
  import('../components/RecognitionErrorRecovery').catch(() => ({ default: () => <Box>Component unavailable</Box> }))
);

const AdminPanel = () => {
  const [orgs, setOrgs] = useState([]);
  const [activeOrg, setActiveOrg] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);
  const [isKeyDialogOpen, setIsKeyDialogOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const [policies, setPolicies] = useState([]);
  const [systems, setSystems] = useState([]);
  const [complianceData, setComplianceData] = useState({});
  const [threats, setThreats] = useState([]);
  const [riskMetrics, setRiskMetrics] = useState({});
  const [darkMode, setDarkMode] = useState(true);
  const [intelligenceTimeframe, setIntelligenceTimeframe] = useState('24h');
  const [selectedRecognition, setSelectedRecognition] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [orgsRes, policiesRes, systemsRes, complianceRes, threatsRes, riskRes] = await Promise.all([
        API.get('/api/organizations').catch(() => ({data: []})),
        API.get('/api/policies').catch(() => ({data: []})),
        API.get('/api/systems/status').catch(() => ({data: []})),
        API.get('/api/compliance/status').catch(() => ({data: {}})),
        API.get('/api/security/threats').catch(() => ({data: []})),
        API.get('/api/analytics/risk-metrics').catch(() => ({data: {}}))
      ]);
      
      setOrgs(orgsRes.data);
      if (orgsRes.data.length > 0) setActiveOrg(orgsRes.data[0]);
      setPolicies(policiesRes.data);
      setSystems(systemsRes.data);
      setComplianceData(complianceRes.data);
      setThreats(threatsRes.data);
      setRiskMetrics(riskRes.data);
    } catch (err) {
      console.error("Failed to fetch admin data");
    }
  };

  const generateKey = async () => {
    if (!activeOrg) return;
    try {
      await API.post(`/api/organizations/${activeOrg.org_id}/api-keys?name=${newKeyName}`);
      setIsKeyDialogOpen(false);
      setNewKeyName('');
      fetchDashboardData();
    } catch (err) {
      console.error("Failed to generate API key");
    }
  };

  const updatePolicy = async (policyId, enabled) => {
    try {
      await API.put(`/api/policies/${policyId}`, { enabled });
      fetchDashboardData();
    } catch (err) {
      console.error("Failed to update policy");
    }
  };

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const renderSystemHealth = () => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Security color="primary" /> System Health
        </Typography>
        <Grid container spacing={2}>
          {systems.map((sys) => (
            <Grid item xs={12} sm={6} md={3} key={sys.id}>
              <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="subtitle2" color="text.secondary">{sys.name}</Typography>
                  <Chip 
                    label={sys.status} 
                    size="small" 
                    color={sys.status === 'healthy' ? 'success' : sys.status === 'degraded' ? 'warning' : 'error'}
                  />
                </Box>
                <Typography variant="h4" sx={{ mb: 1, color: 'primary.main' }}>
                  {sys.uptime}%
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={sys.uptime} 
                  sx={{ 
                    height: 6, 
                    borderRadius: 3,
                    '& .MuiLinearProgress-bar': {
                      borderRadius: 3,
                    }
                  }} 
                />
              </Paper>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );

  const renderPolicyManager = () => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Gavel color="primary" /> Policy Management
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Policy</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {policies.map((policy) => (
              <TableRow key={policy.id}>
                <TableCell>
                  <Typography variant="subtitle2">{policy.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {policy.description}
                  </Typography>
                </TableCell>
                <TableCell>{policy.type}</TableCell>
                <TableCell>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={policy.enabled}
                        onChange={(e) => updatePolicy(policy.id, e.target.checked)}
                        size="small"
                      />
                    }
                    label={policy.enabled ? 'Enabled' : 'Disabled'}
                  />
                </TableCell>
                <TableCell>
                  <Tooltip title="Edit">
                    <IconButton size="small">
                      <Settings fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );

  const renderComplianceDashboard = () => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Shield color="primary" /> Compliance Status
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>Overall Compliance Score</Typography>
              <Typography variant="h3" sx={{ color: '#10b981', mb: 1 }}>
                {complianceData.overallScore || 0}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={complianceData.overallScore || 0} 
                sx={{ 
                  height: 10,
                  borderRadius: 5,
                  bgcolor: 'rgba(16, 185, 129, 0.2)',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: '#10b981',
                  }
                }} 
              />
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, height: '100%' }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>Recent Violations</Typography>
              {threats.slice(0, 5).map((t, i) => (
                <Alert 
                  key={i}
                  severity={t.severity === 'critical' ? 'error' : t.severity === 'high' ? 'warning' : 'info'}
                  sx={{ mb: 1, fontSize: '0.8rem' }}
                  icon={t.severity === 'critical' ? <ErrorIcon /> : <AlertCircle />}
                >
                  {t.type} - {new Date(t.timestamp).toLocaleDateString()}
                </Alert>
              ))}
            </Paper>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  const renderRiskAnalytics = () => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TrendingUp color="primary" /> Risk Analytics
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ bgcolor: 'error.light', color: 'white' }}>
              <CardContent>
                <Typography variant="caption">Critical Risks</Typography>
                <Typography variant="h4">{riskMetrics.critical || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ bgcolor: 'warning.light', color: 'white' }}>
              <CardContent>
                <Typography variant="caption">High Risks</Typography>
                <Typography variant="h4">{riskMetrics.high || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ bgcolor: 'info.light', color: 'white' }}>
              <CardContent>
                <Typography variant="caption">Medium Risks</Typography>
                <Typography variant="h4">{riskMetrics.medium || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ bgcolor: 'success.light', color: 'white' }}>
              <CardContent>
                <Typography variant="caption">Resolved</Typography>
                <Typography variant="h4">{riskMetrics.resolved || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  const renderOriginalAdmin = () => (
    <Box>
      <Typography variant="h4" gutterBottom>Admin Dashboard</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom><Business /> Organizations</Typography>
            <List>
              {orgs.map(org => (
                <ListItem 
                  button 
                  key={org.org_id} 
                  selected={activeOrg?.org_id === org.org_id}
                  onClick={() => setActiveOrg(org)}
                >
                  <ListItemText primary={org.name} secondary={org.subscription_tier} />
                </ListItem>
              ))}
              <ListItem button>
                <ListItemText primary="+ Create New Org" sx={{ color: 'primary.main' }} />
              </ListItem>
            </List>
          </Paper>
        </Grid>

        <Grid item xs={12} md={9}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom><People /> Organization Members</Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>User</TableCell>
                      <TableCell>Role</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell>Admin User</TableCell>
                      <TableCell><Chip label="Admin" size="small" color="primary" /></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="h6"><VpnKey /> API Keys</Typography>
                  <Button size="small" onClick={() => setIsKeyDialogOpen(true)}>Generate Key</Button>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Manage API keys for server-side integrations.
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText primary="Production Key" secondary="fr_live_...4a2b" />
                    <Chip label="Active" size="small" color="success" />
                  </ListItem>
                </List>
              </Paper>
            </Grid>

            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom><Receipt /> Billing & Invoices</Typography>
                <Box sx={{ display: 'flex', gap: 4, mb: 2 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Current Plan</Typography>
                    <Typography variant="h5">{activeOrg?.subscription_tier?.toUpperCase()}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Next Invoice</Typography>
                    <Typography variant="h5">$0.00</Typography>
                  </Box>
                </Box>
                <Button variant="outlined">Manage Subscription</Button>
              </Paper>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      <Dialog open={isKeyDialogOpen} onClose={() => setIsKeyDialogOpen(false)}>
        <DialogTitle>Generate New API Key</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Key Name"
            fullWidth
            variant="standard"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsKeyDialogOpen(false)}>Cancel</Button>
          <Button onClick={generateKey} variant="contained">Generate</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );

  return (
    <Box sx={{ p: 3 }}>
      {/* Enhanced Header with Tabs */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Enterprise Admin Console
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Zero-Knowledge Identity Platform - System Administration
        </Typography>
      </Box>

       <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
         <Tabs value={activeTab} onChange={handleTabChange} variant="scrollable" scrollButtons="auto">
           <Tab label={<span><Business /> Organizations</span>} />
           <Tab label={<span><Shield /> Policy Engine</span>} />
           <Tab label={<span><Security /> Compliance</span>} />
           <Tab label={<span><Brain /> Explainable AI</span>} />
           <Tab label={<span><Timeline /> Operator Workflow</span>} />
           <Tab label={<span><Analytics /> Intelligence</span>} />
           <Tab label={<span><Article /> Enrichment</span>} />
           <Tab label={<span><BugReport /> Anti-Spoof</span>} />
           <Tab label={<span><Key /> Identity Tokens</span>} />
           <Tab label={<span>Settings</span>} />
         </Tabs>
       </Box>

      {/* Tab Content */}
      {activeTab === 0 && renderOriginalAdmin()}
        {activeTab === 1 && (
          <Box>
            {renderSystemHealth()}
            {renderPolicyManager()}
          </Box>
        )}
        {activeTab === 2 && (
          <Box>
            {renderComplianceDashboard()}
            {renderRiskAnalytics()}
          </Box>
        )}
        {activeTab === 3 && (
          <Box>
            <React.Suspense fallback={<Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>}>
              <ExplainableAIPanel
                explanation={{
                  summary: 'Recognition based on multiple biometric modalities with 4 contributing factors',
                  factors: [
                    { name: 'Face Recognition', contribution: 52, confidence: 94 },
                    { name: 'Spoof Detection', contribution: -8, confidence: 87 },
                    { name: 'Emotion Analysis', contribution: 10, confidence: 87 },
                    { name: 'Demographic Analysis', contribution: 8, confidence: 82 }
                  ],
                  metrics: {
                    overallAccuracy: 94.2,
                    biasScore: 0.96,
                    confidenceVariance: 0.03
                  }
                }}
              />
            </React.Suspense>
          </Box>
        )}
        {activeTab === 4 && (
          <Box>
            <React.Suspense fallback={<Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>}>
              <OperatorWorkflowPanel 
                recognitionResult={selectedRecognition}
                onRetry={(adjustments) => {
                  console.log('Retry requested with:', adjustments);
                }}
                onOverride={(data) => {
                  console.log('Override requested:', data);
                }}
                onEscalate={(data) => {
                  console.log('Escalation requested:', data);
                }}
              />
            </React.Suspense>
          </Box>
        )}
        {activeTab === 5 && (
          <Box>
            <React.Suspense fallback={<Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>}>
              <DashboardIntelligencePanel
                timeframe={intelligenceTimeframe}
                onTimeframeChange={setIntelligenceTimeframe}
                onAlertAction={(alert, action) => console.log('Alert action:', alert, action)}
                onDrillDown={(metric, data) => console.log('Drill down:', metric, data)}
              />
            </React.Suspense>
          </Box>
        )}
        {activeTab === 6 && (
          <Box>
            <React.Suspense fallback={<Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>}>
              <EnrichmentPortalPanel
                personId={activeOrg?.org_id || null}
                onEnrichmentComplete={(results) => console.log('Enrichment complete:', results)}
                onAlertAction={(alert, action) => console.log('Alert action:', alert, action)}
              />
            </React.Suspense>
          </Box>
        )}
        {activeTab === 7 && (
          <Box>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <BugReport /> Deepfake Detection Settings
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 2, bgcolor: 'error.light' }}>
                      <Typography variant="h6" sx={{ color: 'white' }}>
                        {threats.length} Active Threats
                      </Typography>
                      <Typography variant="body2" sx={{ color: 'white', opacity: 0.8 }}>
                        Blocked in last 24h
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>Detection Sensitivity</Typography>
                      <Select fullWidth size="small" defaultValue="high">
                        <MenuItem value="low">Low (Fewer false positives)</MenuItem>
                        <MenuItem value="medium">Medium (Balanced)</MenuItem>
                        <MenuItem value="high">High (Catch all threats)</MenuItem>
                      </Select>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>Auto-Block</Typography>
                      <FormControlLabel
                        control={<Switch defaultChecked />}
                        label="Block high-risk attempts"
                      />
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Box>
        )}
      {activeTab === 2 && (
        <Box>
          {renderComplianceDashboard()}
          {renderRiskAnalytics()}
        </Box>
      )}
      {activeTab === 3 && (
        <Box>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Brain /> Explainable AI Configuration
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>Decision Breakdown</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Show feature contributions for each decision
                    </Typography>
                    <FormControlLabel
                      control={<Switch defaultChecked />}
                      label="Enable explanation panel"
                    />
                  </Paper>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>Bias Detection</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Monitor fairness across demographic groups
                    </Typography>
                    <FormControlLabel
                      control={<Switch defaultChecked />}
                      label="Enable bias monitoring"
                    />
                  </Paper>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Box>
      )}
      {activeTab === 4 && (
        <Box>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <BugReport /> Deepfake Detection Settings
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <Paper sx={{ p: 2, bgcolor: 'error.light' }}>
                    <Typography variant="h6" sx={{ color: 'white' }}>
                      {threats.length} Active Threats
                    </Typography>
                    <Typography variant="body2" sx={{ color: 'white', opacity: 0.8 }}>
                      Blocked in last 24h
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>Detection Sensitivity</Typography>
                    <Select fullWidth size="small" defaultValue="high">
                      <MenuItem value="low">Low (Fewer false positives)</MenuItem>
                      <MenuItem value="medium">Medium (Balanced)</MenuItem>
                      <MenuItem value="high">High (Catch all threats)</MenuItem>
                    </Select>
                  </Paper>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>Auto-Block</Typography>
                    <FormControlLabel
                      control={<Switch defaultChecked />}
                      label="Block high-risk attempts"
                    />
                  </Paper>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Box>
      )}
      {activeTab === 5 && (
        <Box>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Key /> Revocable Tokens & Identity
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Manage revocable biometric tokens and decentralized identifiers
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="primary">1,247</Typography>
                    <Typography variant="body2" color="text.secondary">Active Tokens</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'success.light' }}>
                    <Typography variant="h4" color="white">2,156</Typography>
                    <Typography variant="body2" color="white">DIDs Created</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'info.light' }}>
                    <Typography variant="h4" color="white">48</Typography>
                    <Typography variant="body2" color="white">Revoked Today</Typography>
                  </Paper>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Box>
      )}
      {activeTab === 6 && (
        <Box>
          {renderOriginalAdmin()}
        </Box>
      )}
    </Box>
  );
};

export default AdminPanel;
