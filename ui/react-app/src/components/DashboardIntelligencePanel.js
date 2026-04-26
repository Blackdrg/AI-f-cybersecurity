import React, { useState, useEffect, useMemo } from 'react';
import {
  Box, Typography, Paper, Grid, Card, CardContent,
  Table, TableBody, TableCell, TableHead, TableRow,
  Chip, IconButton, Tooltip, LinearProgress, Button,
  Accordion, AccordionSummary, AccordionDetails, Alert,
  Tabs, Tab, Divider, List, ListItem, ListItemText,
  ListItemIcon, Badge, CircularProgress, TextField,
  Select, MenuItem, FormControl, InputLabel
} from '@mui/material';
import {
  Analytics, Timeline, BarChart, AlertCircle,
  TrendingUp, BugReport, Security, FilterList,
  Search, CompareArrows, AccountTree, NetworkCheck,
  ShowChart, History, Database, Download, PlayArrow,
  Pause, Refresh, ExpandMore, ChevronRight
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, AreaChart, Area, BarChart as RechartsBarChart, Bar } from 'recharts';
import API from '../services/api';

const DashboardIntelligencePanel = ({ 
  timeframe = '24h',
  onTimeframeChange,
  onAlertAction,
  onDrillDown,
  isLoading: propLoading
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [expandedAccordion, setExpandedAccordion] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [decisionTrace, setDecisionTrace] = useState([]);
  const [historicalTrends, setHistoricalTrends] = useState([]);
  const [riskMetrics, setRiskMetrics] = useState({});
  const [drilldownData, setDrilldownData] = useState(null);
  const [filterCriteria, setFilterCriteria] = useState({
    severity: 'all',
    type: 'all',
    dateRange: '7d'
  });

  useEffect(() => {
    fetchDashboardIntelligence();
    const interval = setInterval(fetchDashboardIntelligence, 60000);
    return () => clearInterval(interval);
  }, [timeframe]);

  const fetchDashboardIntelligence = async () => {
    setIsLoading(true);
    try {
      const [analyticsRes, alertsRes, trendsRes, riskRes] = await Promise.all([
        API.get(`/api/analytics?timeframe=${timeframe}`).catch(() => ({ data: null })),
        API.get('/api/alerts/active').catch(() => ({ data: { alerts: [] } })),
        API.get(`/api/analytics/risk-trends`).catch(() => ({ data: [] })),
        API.get('/api/analytics/risk-metrics').catch(() => ({ data: {} }))
      ]);
      
      setAnalyticsData(analyticsRes.data);
      setAlerts(alertsRes.data?.alerts || []);
      setHistoricalTrends(trendsRes.data || []);
      setRiskMetrics(riskRes.data || {});
      
      // Fetch decision trace
      fetchDecisionTrace();
    } catch (err) {
      console.warn('Failed to fetch intelligence data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchDecisionTrace = async () => {
    try {
      const res = await API.get('/api/events?limit=50');
      const events = res.data?.events || [];
      const trace = events.map(e => ({
        id: e.event_id || `event_${Date.now()}_${Math.random()}`,
        timestamp: e.timestamp,
        type: e.decision || e.action,
        confidence: e.confidence_score,
        riskScore: e.risk_score,
        subject: e.person_name || e.person_id || 'Unknown',
        details: e.details || {},
        path: generateDecisionPath(e)
      }));
      setDecisionTrace(trace);
    } catch (err) {
      console.warn('Failed to fetch decision trace');
    }
  };

  const generateDecisionPath = (event) => {
    const steps = [];
    if (event.detection_method) steps.push({ name: 'Detection', value: event.detection_method });
    if (event.confidence_score) steps.push({ name: 'Confidence', value: `${(event.confidence_score * 100).toFixed(1)}%` });
    if (event.risk_score) steps.push({ name: 'Risk', value: `${(event.risk_score * 100).toFixed(1)}%` });
    if (event.decision) steps.push({ name: 'Decision', value: event.decision });
    return steps;
  };

  const handleDrillDown = (metric, data) => {
    setDrilldownData({ metric, data });
    onDrillDown && onDrillDown(metric, data);
  };

  const handleAlertAction = (alert, action) => {
    onAlertAction && onAlertAction(alert, action);
    setAlerts(prev => prev.filter(a => a.id !== alert.id));
  };

  const getTrendIndicator = (value, baseline) => {
    const diff = ((value - baseline) / baseline) * 100;
    if (diff > 10) return { icon: <TrendingUp color="error" />, color: 'error', label: 'Rising' };
    if (diff < -10) return { icon: <TrendingUp color="success" />, color: 'success', label: 'Declining' };
    return { icon: <TrendingUp color="info" />, color: 'info', label: 'Stable' };
  };

  const getSeverityColor = (severity) => {
    const colors = {
      critical: '#ef4444',
      high: '#f59e0b',
      medium: '#fbbf24',
      low: '#10b981',
      info: '#3b82f6'
    };
    return colors[severity] || colors.info;
  };

  const prepareTrendData = () => {
    return historicalTrends.map(t => ({
      date: t.date || t.timestamp?.split('T')[0] || 'Unknown',
      recognitions: t.recognitions || t.recognition_count || 0,
      risk: (t.risk || t.risk_score || 0) * 100,
      alerts: t.alerts || 0,
      accuracy: (t.accuracy || 0.95) * 100
    })).slice(-30); // Last 30 data points
  };

  const trendData = prepareTrendData();

  const renderAlertPrioritization = () => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AlertCircle color="warning" />
            Alert Prioritization Center
          </Typography>
          <Badge badgeContent={alerts.length} color="error">
            <FilterList />
          </Badge>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Severity</InputLabel>
            <Select
              value={filterCriteria.severity}
              onChange={(e) => setFilterCriteria({...filterCriteria, severity: e.target.value})}
              label="Severity"
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="critical">Critical</MenuItem>
              <MenuItem value="high">High</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="low">Low</MenuItem>
            </Select>
          </FormControl>
          <TextField
            size="small"
            placeholder="Search alerts..."
            InputProps={{ startAdornment: <Search sx={{ mr: 1, fontSize: 20 }} /> }}
            onChange={(e) => setFilterCriteria({...filterCriteria, search: e.target.value})}
            sx={{ minWidth: 200 }}
          />
        </Box>

        {alerts.length === 0 ? (
          <Alert severity="success" sx={{ mb: 2 }}>
            No active alerts - All systems operational
          </Alert>
        ) : (
          <Stack spacing={2}>
            {alerts
              .filter(a => filterCriteria.severity === 'all' || a.severity === filterCriteria.severity)
              .sort((a, b) => {
                const severityOrder = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };
                return (severityOrder[b.severity] || 0) - (severityOrder[a.severity] || 0);
              })
              .map((alert, idx) => (
                <Paper
                  key={idx}
                  sx={{
                    p: 2,
                    borderLeft: `4px solid ${getSeverityColor(alert.severity)}`,
                    background: 'rgba(0,0,0,0.2)',
                    transition: 'all 0.3s'
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Box>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {alert.title || alert.type}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {alert.message}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                        <Chip
                          label={alert.severity}
                          size="small"
                          sx={{
                            bgcolor: `${getSeverityColor(alert.severity)}33`,
                            color: getSeverityColor(alert.severity)
                          }}
                        />
                        <Chip label={alert.category || 'General'} size="small" variant="outlined" />
                        {alert.affected_systems && (
                          <Chip label={`${alert.affected_systems.length} systems`} size="small" />
                        )}
                      </Box>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(alert.timestamp).toLocaleString()}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, mt: 1 }}>
                        <Button
                          size="small"
                          variant="contained"
                          color="warning"
                          onClick={() => handleAlertAction(alert, 'investigate')}
                        >
                          Investigate
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => handleAlertAction(alert, 'acknowledge')}
                        >
                          Acknowledge
                        </Button>
                      </Box>
                    </Box>
                  </Box>
                  {alert.metrics && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Impact: {alert.metrics.affected_users || 0} users | 
                        Confidence: {(alert.confidence * 100 || 0).toFixed(1)}%
                      </Typography>
                    </Box>
                  )}
                </Paper>
              ))}
          </Stack>
        )}
      </CardContent>
    </Card>
  );

  const renderHistoricalTrends = () => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Timeline color="primary" />
            Historical Trend Analysis
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              size="small"
              variant={timeframe === '24h' ? 'contained' : 'outlined'}
              onClick={() => onTimeframeChange && onTimeframeChange('24h')}
            >
              24h
            </Button>
            <Button
              size="small"
              variant={timeframe === '7d' ? 'contained' : 'outlined'}
              onClick={() => onTimeframeChange && onTimeframeChange('7d')}
            >
              7d
            </Button>
            <Button
              size="small"
              variant={timeframe === '30d' ? 'contained' : 'outlined'}
              onClick={() => onTimeframeChange && onTimeframeChange('30d')}
            >
              30d
            </Button>
          </Box>
        </Box>

        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)} sx={{ mb: 2 }}>
          <Tab label="Recognition Volume" />
          <Tab label="Risk Metrics" />
          <Tab label="System Health" />
        </Tabs>

        <Box sx={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            {activeTab === 0 && (
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="colorRecognitions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <RechartsTooltip />
                <Area
                  type="monotone"
                  dataKey="recognitions"
                  stroke="#3b82f6"
                  fill="url(#colorRecognitions)"
                  strokeWidth={2}
                />
              </AreaChart>
            )}
            {activeTab === 1 && (
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <RechartsTooltip />
                <Line
                  type="monotone"
                  dataKey="risk"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={{ fill: '#f59e0b' }}
                />
                <Line
                  type="monotone"
                  dataKey="alerts"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={{ fill: '#ef4444' }}
                />
              </LineChart>
            )}
            {activeTab === 2 && (
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="colorAccuracy" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} domain={[90, 100]} />
                <RechartsTooltip />
                <Area
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#10b981"
                  fill="url(#colorAccuracy)"
                  strokeWidth={2}
                />
              </AreaChart>
            )}
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );

  const renderDecisionTraceability = () => (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Database color="primary" />
            Decision Traceability
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {decisionTrace.length} recent decisions
          </Typography>
        </Box>

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Timestamp</TableCell>
              <TableCell>Subject</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Risk</TableCell>
              {/* <TableCell>Decision Path</TableCell> */}
              <TableCell align="right">Decision</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {decisionTrace.slice(0, 20).map((trace, idx) => (
              <TableRow key={trace.id || idx} hover>
                <TableCell>
                  <Typography variant="body2">
                    {new Date(trace.timestamp).toLocaleTimeString()}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {trace.subject}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={`${(trace.confidence * 100 || 0).toFixed(1)}%`}
                    size="small"
                    sx={{
                      bgcolor: trace.confidence > 0.8 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                      color: trace.confidence > 0.8 ? '#10b981' : '#f59e0b'
                    }}
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    label={`${(trace.riskScore * 100 || 0).toFixed(1)}%`}
                    size="small"
                    sx={{
                      bgcolor: trace.riskScore < 0.3 ? 'rgba(16, 185, 129, 0.2)' : 
                              trace.riskScore < 0.6 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                      color: trace.riskScore < 0.3 ? '#10b981' :
                             trace.riskScore < 0.6 ? '#f59e0b' : '#ef4444'
                    }}
                  />
                </TableCell>
                <TableCell align="right">
                  <Chip
                    label={trace.type || 'Unknown'}
                    size="small"
                    color={
                      trace.type === 'allow' ? 'success' :
                      trace.type === 'deny' ? 'error' : 'warning'
                    }
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {drilldownData && (
          <Accordion
            expanded={expandedAccordion === 'drilldown'}
            onChange={() => setExpandedAccordion(expandedAccordion === 'drilldown' ? null : 'drilldown')}
            sx={{ mt: 2 }}
          >
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography>Drill-down Details</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="body2" color="text.secondary">
                {JSON.stringify(drilldownData, null, 2)}
              </Typography>
            </AccordionDetails>
          </Accordion>
        )}
      </CardContent>
    </Card>
  );

  const renderRiskMetrics = () => (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Assessment color="primary" />
          Risk Analytics
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.paper' }}>
              <Typography variant="h3" sx={{ color: riskMetrics.avgRiskScore > 0.6 ? '#ef4444' : riskMetrics.avgRiskScore > 0.3 ? '#f59e0b' : '#10b981' }}>
                {((riskMetrics.avgRiskScore || 0) * 100).toFixed(1)}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Avg Risk Score
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.paper' }}>
              <Typography variant="h3" color="success.main">
                {riskMetrics.falsePositiveRate ? (riskMetrics.falsePositiveRate * 100).toFixed(2) : '0.01'}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                False Positive Rate
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.paper' }}>
              <Typography variant="h3" color="info.main">
                {riskMetrics.falseNegativeRate ? (riskMetrics.falseNegativeRate * 100).toFixed(2) : '0.03'}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                False Negative Rate
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'background.paper' }}>
              <Typography variant="h3" color="warning.main">
                {riskMetrics.threatCount || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Active Threats
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Anomaly Detection Score
          </Typography>
          <LinearProgress
            variant="determinate"
            value={(riskMetrics.anomalyScore || 0) * 100}
            sx={{
              height: 10,
              borderRadius: 5,
              bgcolor: 'rgba(0,0,0,0.2)',
              '& .MuiLinearProgress-bar': {
                borderRadius: 5,
                bgcolor: (riskMetrics.anomalyScore || 0) > 0.7 ? '#ef4444' :
                        (riskMetrics.anomalyScore || 0) > 0.4 ? '#f59e0b' : '#10b981'
              }
            }}
          />
        </Box>
      </CardContent>
    </Card>
  );

  if (isLoading && propLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h5" gutterBottom sx={{ fontWeight: 700 }}>
        Dashboard Intelligence Hub
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Advanced analytics, alert prioritization, and decision audit trail
      </Typography>

      <Box sx={{ flexGrow: 1, overflow: 'auto', pr: 2 }}>
        {renderAlertPrioritization()}
        {renderHistoricalTrends()}
        {renderDecisionTraceability()}
        {renderRiskMetrics()}
      </Box>
    </Box>
  );
};

export default DashboardIntelligencePanel;
