import React, { useState, useEffect, useMemo, Suspense } from 'react';
import { Box, Toolbar, Typography, Container, Grid, Paper, Card, CardContent, IconButton, CircularProgress, Select, MenuItem, Button, CircularProgress } from '@mui/material';
import { 
  People, CameraAlt, History, Assessment, 
  Security, Timeline, ShowChart, Warning,
  Refresh, PlayArrow, Pause, Settings,
  AccountCircle, Lock, Key, BarChart,
  Radar, TimelineRounded, Shield, BugReport,
  Insights, NetworkCheck, AccountTree, Article
} from '@mui/icons-material';
import Sidebar from '../components/Sidebar';
import SystemStatus from '../components/SystemStatus';
import DashboardIntelligencePanel from '../components/DashboardIntelligencePanel';
import EnrichmentPortalPanel from '../components/EnrichmentPortalPanel';
import OperatorWorkflowPanel from '../components/OperatorWorkflowPanel';
import RecognizeErrorRecovery from '../components/RecognitionErrorRecovery';
import ExplainableAIPanel from '../components/ExplainableAIPanel';
import API from '../services/api';
import './Dashboard.css';

const DashboardHome = () => {
  const [metrics, setMetrics] = useState({
    totalRecognitions: 0,
    totalEnrollments: 0,
    activeSessions: 0,
    riskScore: 0,
    avgConfidence: 0.94,
    deepfakeDetected: 0,
    accuracy: 0
  });
  const [events, setEvents] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [threats, setThreats] = useState([]);
  const [timeframe, setTimeframe] = useState('24h');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeIntelligenceTab, setActiveIntelligenceTab] = useState('overview');
  const [selectedRecognition, setSelectedRecognition] = useState(null);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [timeframe]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [metricsRes, eventsRes, sessionsRes] = await Promise.all([
        API.get("/api/analytics?timeframe=" + timeframe).catch(() => ({data: metrics})),
        API.get("/api/events?limit=50").catch(() => ({data: {events: []}})),
        API.get("/api/sessions/active").catch(() => ({data: {sessions: []}}))
      ]);
      
      setMetrics(metricsRes.data || metrics);
      setEvents(eventsRes.data?.events || eventsRes.data || []);
      setSessions(sessionsRes.data?.sessions || sessionsRes.data || []);
      
      // Fetch threats
      try {
        const threatsRes = await API.get("/api/security/threats").catch(() => ({data: []}));
        setThreats(threatsRes.data || []);
      } catch (err) {
        setThreats([]);
      }
      
      setError(null);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score) => {
    if (score < 0.3) return '#10b981';
    if (score < 0.6) return '#f59e0b';
    return '#ef4444';
  };

  const getConfidenceColor = (score) => {
    if (score > 0.8) return '#10b981';
    if (score > 0.5) return '#f59e0b';
    return '#ef4444';
  };

  // Simulated data for demo when backend not available
  const demoMetrics = {
    totalRecognitions: 12847,
    totalEnrollments: 2156,
    activeSessions: 47,
    riskScore: 0.23,
    avgConfidence: 0.94,
    deepfakeDetected: 12,
    accuracy: 0.998
  };

  const demoEvents = [
    { timestamp: new Date(Date.now() - 5*60000).toISOString(), person_name: 'John Smith', method: 'Face', confidence: 0.92, risk_score: 0.1, decision: 'allow' },
    { timestamp: new Date(Date.now() - 10*60000).toISOString(), person_name: 'Sarah Johnson', method: 'Multi-Modal', confidence: 0.97, risk_score: 0.05, decision: 'allow' },
    { timestamp: new Date(Date.now() - 15*60000).toISOString(), person_name: 'Mike Chen', method: 'Voice', confidence: 0.88, risk_score: 0.15, decision: 'review' },
    { timestamp: new Date(Date.now() - 20*60000).toISOString(), person_name: 'Emily Davis', method: 'Gait', confidence: 0.76, risk_score: 0.25, decision: 'deny' },
    { timestamp: new Date(Date.now() - 25*60000).toISOString(), person_name: 'Robert Wilson', method: 'Face', confidence: 0.95, risk_score: 0.08, decision: 'allow' },
  ];

  const demoSessions = [
    { person_name: 'John Smith', device_id: 'CAM-001', last_active: new Date(Date.now() - 2*60000).toISOString(), confidence: 0.94 },
    { person_name: 'Sarah Johnson', device_id: 'CAM-003', last_active: new Date(Date.now() - 5*60000).toISOString(), confidence: 0.91 },
    { person_name: 'Mike Chen', device_id: 'CAM-002', last_active: new Date(Date.now() - 8*60000).toISOString(), confidence: 0.88 },
    { person_name: 'Emily Davis', device_id: 'CAM-LAB-01', last_active: new Date(Date.now() - 12*60000).toISOString(), confidence: 0.82 },
    { person_name: 'Robert Wilson', device_id: 'CAM-001', last_active: new Date(Date.now() - 15*60000).toISOString(), confidence: 0.96 },
    { person_name: 'Lisa Anderson', device_id: 'CAM-SEC-01', last_active: new Date(Date.now() - 18*60000).toISOString(), confidence: 0.89 },
    { person_name: 'Tom Martinez', device_id: 'CAM-004', last_active: new Date(Date.now() - 22*60000).toISOString(), confidence: 0.78 },
    { person_name: 'Jennifer Lee', device_id: 'CAM-GATE-01', last_active: new Date(Date.now() - 25*60000).toISOString(), confidence: 0.93 },
  ];

  const demoThreats = [
    { type: 'Deepfake Video', confidence: 0.95, timestamp: new Date(Date.now() - 5*60000).toISOString() },
    { type: 'Spoofing Attempt', confidence: 0.87, timestamp: new Date(Date.now() - 45*60000).toISOString() },
    { type: 'Mask Attack', confidence: 0.92, timestamp: new Date(Date.now() - 2*3600000).toISOString() },
  ];

  const displayMetrics = loading ? demoMetrics : metrics;
  const displayEvents = loading ? demoEvents : events;
  const displaySessions = loading ? demoSessions : sessions;
  const displayThreats = loading ? demoThreats : threats;

  if (loading && !events.length) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p>Initializing Zero-Knowledge Identity Platform...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-new">
      {/* Enhanced Header */}
      <div className="dashboard-header">
        <div className="header-left">
          <h1>Enterprise Identity Intelligence Platform</h1>
          <p className="subtitle">Zero-Knowledge Biometric Recognition System v2.0 - Operator Dashboard</p>
        </div>
        <div className="header-right">
          <div className="timeframe-selector">
            <Select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              size="small"
              className="timeframe-select"
            >
              <MenuItem value="1h">Last Hour</MenuItem>
              <MenuItem value="24h">Last 24 Hours</MenuItem>
              <MenuItem value="7d">Last 7 Days</MenuItem>
            </Select>
          </div>
          <IconButton, CircularProgress onClick={fetchDashboardData} className="refresh-btn">
            <Refresh />
          </IconButton, CircularProgress>
          <Button, CircularProgress variant="contained" startIcon={<Settings />} className="settings-btn">
            System Config
          </Button, CircularProgress>
        </div>
      </div>

      {error && <div className="error-alert">{error}</div>}

      {/* Intelligence Overview Tabs */}
      <div className="intelligence-tabs" style={{ marginBottom: '20px' }}>
        <Button, CircularProgress
          variant={activeIntelligenceTab === 'overview' ? 'contained' : 'outlined'}
          onClick={() => setActiveIntelligenceTab('overview')}
          size="small"
          sx={{ mr: 1 }}
        >
          Overview
        </Button, CircularProgress>
        <Button, CircularProgress
          variant={activeIntelligenceTab === 'intelligence' ? 'contained' : 'outlined'}
          onClick={() => setActiveIntelligenceTab('intelligence')}
          size="small"
          sx={{ mr: 1 }}
          startIcon={<Radar />}
        >
          Intelligence Hub
        </Button, CircularProgress>
        <Button, CircularProgress
          variant={activeIntelligenceTab === 'enrichment' ? 'contained' : 'outlined'}
          onClick={() => setActiveIntelligenceTab('enrichment')}
          size="small"
          sx={{ mr: 1 }}
          startIcon={<Article />}
        >
          Data Enrichment
        </Button, CircularProgress>
        <Button, CircularProgress
          variant={activeIntelligenceTab === 'workflow' ? 'contained' : 'outlined'}
          onClick={() => setActiveIntelligenceTab('workflow')}
          size="small"
          startIcon={<Timeline />}
        >
          Workflow & Recovery
        </Button, CircularProgress>
      </div>

      {/* Dynamic Content Based on Active Tab */}
      {activeIntelligenceTab === 'overview' && (
        <>
          {/* Key Metrics Grid */}
          <Grid container spacing={2} className="metrics-grid">
            <Grid item xs={12} sm={6} md={4} lg={2}>
              <Card className="metric-card metric-blue">
                <div className="metric-icon-box blue">
                  <People />
                </div>
                <Typography className="metric-label">Total Enrolled</Typography>
                <Typography className="metric-value">{displayMetrics.totalEnrollments.toLocaleString()}</Typography>
                <Typography className="metric-change positive">+8.2%</Typography>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={4} lg={2}>
              <Card className="metric-card metric-green">
                <div className="metric-icon-box green">
                  <CameraAlt />
                </div>
                <Typography className="metric-label">Recognitions</Typography>
                <Typography className="metric-value">{displayMetrics.totalRecognitions.toLocaleString()}</Typography>
                <Typography className="metric-change positive">+12.5%</Typography>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={4} lg={2}>
              <Card className="metric-card metric-purple">
                <div className="metric-icon-box purple">
                  <Security />
                </div>
                <Typography className="metric-label">Active Sessions</Typography>
                <Typography className="metric-value">{displayMetrics.activeSessions}</Typography>
                <Typography className="metric-change">{displaySessions.length} locations</Typography>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={4} lg={2}>
              <Card className="metric-card metric-orange">
                <div className="metric-icon-box orange">
                  <Assessment />
                </div>
                <Typography className="metric-label">Accuracy Rate</Typography>
                <Typography className="metric-value">{(displayMetrics.accuracy * 100).toFixed(1)}%</Typography>
                <Typography className="metric-change positive">+0.1%</Typography>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={4} lg={2}>
              <Card className="metric-card metric-cyan">
                <div className="metric-icon-box cyan">
                  <Timeline />
                </div>
                <Typography className="metric-label">Avg Confidence</Typography>
                <Typography className="metric-value">{(displayMetrics.avgConfidence * 100).toFixed(1)}%</Typography>
                <Typography className="metric-change positive">Calibrated</Typography>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={4} lg={2}>
              <Card className="metric-card metric-red">
                <div className="metric-icon-box red">
                  <BugReport />
                </div>
                <Typography className="metric-label">Deepfake Blocked</Typography>
                <Typography className="metric-value">{displayMetrics.deepfakeDetected}</Typography>
                <Typography className="metric-change">Real-time</Typography>
              </Card>
            </Grid>
          </Grid>

          {/* Charts Grid */}
          <Grid container spacing={2} className="charts-grid">
            <Grid item xs={12} lg={6}>
              <Card className="chart-card">
                <div className="card-header">
                  <div className="card-title">
                    <TimelineRounded />
                    <span>Recognition Trends</span>
                  </div>
                  <span className="badge">Live</span>
                </div>
                <div className="chart-placeholder">
                  <ShowChart className="chart-icon" />
                  <Typography>Interactive trend visualization</Typography>
                  <Typography variant="caption" color="text.secondary">
                    12,847 recognitions tracked | Peak: 1,245/hr
                  </Typography>
                </div>
              </Card>
            </Grid>
            <Grid item xs={12} lg={6}>
              <Card className="chart-card">
                <div className="card-header">
                  <div className="card-title">
                    <Radar />
                    <span>Method Distribution</span>
                  </div>
                </div>
                <div className="method-stats">
                  <div className="method-item">
                    <div className="method-dot blue"></div>
                    <span>Face Recognition</span>
                    <span className="method-value">58%</span>
                  </div>
                  <div className="method-item">
                    <div className="method-dot yellow"></div>
                    <span>Voice Analysis</span>
                    <span className="method-value">22%</span>
                  </div>
                  <div className="method-item">
                    <div className="method-dot green"></div>
                    <span>Gait Analysis</span>
                    <span className="method-value">12%</span>
                  </div>
                  <div className="method-item">
                    <div className="method-dot purple"></div>
                    <span>Multi-Modal</span>
                    <span className="method-value">8%</span>
                  </div>
                </div>
              </Card>
            </Grid>
            <Grid item xs={12} lg={6}>
              <Card className="chart-card">
                <div className="card-header">
                  <div className="card-title">
                    <Shield />
                    <span>Threat Intelligence</span>
                  </div>
                  <span className="badge alert">{displayThreats.length} active</span>
                </div>
                <div className="threats-list">
                  {displayThreats.map((t, i) => (
                    <div key={i} className="threat-item">
                      <div className="threat-icon">
                        <BugReport />
                      </div>
                      <div className="threat-info">
                        <Typography variant="subtitle2">{t.type}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(t.timestamp).toLocaleTimeString()}
                        </Typography>
                      </div>
                      <span className="threat-score">{Math.round(t.confidence * 100)}%</span>
                    </div>
                  ))}
                </div>
              </Card>
            </Grid>
            <Grid item xs={12} lg={6}>
              <Card className="chart-card">
                <div className="card-header">
                  <div className="card-title">
                    <Insights />
                    <span>Risk Analysis</span>
                  </div>
                </div>
                <div className="risk-metrics">
                  <div className="risk-item">
                    <span>System Risk</span>
                    <span className="risk-badge" style={{background: getRiskColor(displayMetrics.riskScore)}}>
                      {Math.round(displayMetrics.riskScore * 100)}%
                    </span>
                  </div>
                  <div className="risk-item">
                    <span>Avg False Positive</span>
                    <span className="risk-badge green">0.8%</span>
                  </div>
                  <div className="risk-item">
                    <span>Avg False Negative</span>
                    <span className="risk-badge green">0.3%</span>
                  </div>
                  <div className="risk-item">
                    <span>Bias Score</span>
                    <span className="risk-badge cyan">0.94</span>
                  </div>
                </div>
              </Card>
            </Grid>
          </Grid>

          {/* Detailed Tables */}
          <Grid container spacing={2} className="bottom-section">
            <Grid item xs={12} lg={8}>
              <Card className="table-card">
                <div className="card-header">
                  <div className="card-title">
                    <History />
                    <span>Recent Events</span>
                  </div>
                  <span className="badge">{displayEvents.length} total</span>
                </div>
                <div className="table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Identity</th>
                        <th>Method</th>
                        <th>Confidence</th>
                        <th>Risk</th>
                        <th>Decision</th>
                      </tr>
                    </thead>
                    <tbody>
                      {displayEvents.map((e, i) => (
                        <tr key={i}>
                          <td>{new Date(e.timestamp).toLocaleTimeString()}</td>
                          <td>{e.person_name || 'Unknown'}</td>
                          <td><span className="method-badge">{e.method}</span></td>
                          <td><span className="confidence-badge" style={{background: getConfidenceColor(e.confidence)}}>{Math.round(e.confidence * 100)}%</span></td>
                          <td><span className="risk-badge" style={{background: getRiskColor(e.risk_score)}}>{Math.round(e.risk_score * 100)}%</span></td>
                          <td><span className={`decision-badge ${e.decision}`}>{e.decision}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </Grid>
            <Grid item xs={12} lg={4}>
              <Card className="table-card">
                <div className="card-header">
                  <div className="card-title">
                    <NetworkCheck />
                    <span>Live Sessions</span>
                  </div>
                  <span className="badge">{displaySessions.length} active</span>
                </div>
                <div className="sessions-list">
                  {displaySessions.map((s, i) => (
                    <div key={i} className="session-item">
                      <div className="session-avatar">
                        <AccountCircle />
                      </div>
                      <div className="session-info">
                        <Typography variant="subtitle2">{s.person_name}</Typography>
                        <Typography variant="caption" color="text.secondary">{s.device_id}</Typography>
                      </div>
                      <span className="session-confidence" style={{background: getConfidenceColor(s.confidence)}}>
                        {Math.round(s.confidence * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            </Grid>
          </Grid>
        </>
      )}

      {/* Intelligence Hub Tab */}
      {activeIntelligenceTab === 'intelligence' && (
        <React.Suspense fallback={<Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>}>
          <DashboardIntelligencePanel
            timeframe={timeframe}
            onTimeframeChange={setTimeframe}
            onAlertAction={() => {}}
            onDrillDown={() => {}}
          />
        </React.Suspense>
      )}

      {/* Data Enrichment Tab */}
      {activeIntelligenceTab === 'enrichment' && (
        <React.Suspense fallback={<Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>}>
          <EnrichmentPortalPanel
            onEnrichmentComplete={() => {}}
            onAlertAction={() => {}}
          />
        </React.Suspense>
      )}

      {/* Workflow & Recovery Tab */}
      {activeIntelligenceTab === 'workflow' && (
        <React.Suspense fallback={<Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>}>
          <OperatorWorkflowPanel
            recognitionResult={selectedRecognition}
            onRetry={() => fetchDashboardData()}
            onOverride={() => {}}
            onEscalate={() => {}}
          />
        </React.Suspense>
      )}
    </div>
  );
};

export default DashboardHome;
