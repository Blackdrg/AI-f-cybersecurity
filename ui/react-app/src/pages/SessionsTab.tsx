import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Grid, Paper, Card, CardContent,
  Table, TableBody, TableCell, TableHead, TableRow,
  Chip, LinearProgress, Tooltip, IconButton, Avatar,
  Button, TextField, InputAdornment
} from '@mui/material';
import {
  Monitor, Radar, NetworkCheck, TrendingUp,
  PlayArrow, Pause, Timeline, AccountCircle
} from '@mui/icons-material';
import API from '../services/api';

function SessionsTab() {
  const [sessions, setSessions] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadSessions();
    const interval = setInterval(loadSessions, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadSessions = async () => {
    try {
      const res = await API.get('/api/sessions/active');
      setSessions(res.data?.sessions || []);
      setMetrics(res.data?.metrics || {});
    } catch (err) {
      // Use sample data
      setSessions([
        {
          id: 'sess_001',
          person_name: 'John Smith',
          person_id: 'person_123',
          device_id: 'CAM-SEC-01',
          start_time: new Date(Date.now() - 25 * 60000).toISOString(),
          last_active: new Date(Date.now() - 2 * 60000).toISOString(),
          confidence: 0.94,
          risk_score: 0.12,
          location: 'Main Entrance',
          behaviors: { walking_speed: 1.2, posture: 0.9 }
        },
        {
          id: 'sess_002',
          person_name: 'Sarah Johnson',
          person_id: 'person_456',
          device_id: 'CAM-003',
          start_time: new Date(Date.now() - 18 * 60000).toISOString(),
          last_active: new Date(Date.now() - 5 * 60000).toISOString(),
          confidence: 0.91,
          risk_score: 0.18,
          location: 'Lobby Area',
          behaviors: { walking_speed: 1.1, posture: 0.85 }
        },
        {
          id: 'sess_003',
          person_name: 'Mike Chen',
          person_id: 'person_789',
          device_id: 'CAM-LAB-01',
          start_time: new Date(Date.now() - 45 * 60000).toISOString(),
          last_active: new Date(Date.now() - 8 * 60000).toISOString(),
          confidence: 0.88,
          risk_score: 0.25,
          location: 'Research Lab',
          behaviors: { walking_speed: 0.9, posture: 0.8 }
        },
        {
          id: 'sess_004',
          person_name: 'Emily Davis',
          person_id: 'person_101',
          device_id: 'CAM-002',
          start_time: new Date(Date.now() - 12 * 60000).toISOString(),
          last_active: new Date(Date.now() - 1 * 60000).toISOString(),
          confidence: 0.96,
          risk_score: 0.08,
          location: 'Server Room',
          behaviors: { walking_speed: 1.3, posture: 0.95 }
        },
        {
          id: 'sess_005',
          person_name: 'Robert Wilson',
          person_id: 'person_202',
          device_id: 'CAM-GATE-01',
          start_time: new Date(Date.now() - 30 * 60000).toISOString(),
          last_active: new Date(Date.now() - 3 * 60000).toISOString(),
          confidence: 0.85,
          risk_score: 0.32,
          location: 'Loading Dock',
          behaviors: { walking_speed: 1.0, posture: 0.75 }
        }
      ]);
      setMetrics({
        total_active: 5,
        avg_confidence: 0.908,
        avg_risk: 0.19,
        drift_alerts: 1
      });
    }
  };

  const getRiskColor = (score) => {
    if (score < 0.2) return '#10b981';
    if (score < 0.5) return '#f59e0b';
    return '#ef4444';
  };

  const getConfidenceColor = (score) => {
    if (score > 0.9) return '#10b981';
    if (score > 0.7) return '#f59e0b';
    return '#ef4444';
  };

  const filteredSessions = sessions.filter(s =>
    s.person_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.device_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold">
            Session Monitoring
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Track active identity sessions and behavioral patterns
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            size="small"
            placeholder="Search sessions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Timeline fontSize="small" />
                </InputAdornment>
              ),
            }}
            sx={{ width: 250 }}
          />
          <Button variant="contained" startIcon={<PlayArrow />}>
            Live Mode
          </Button>
        </Box>
      </Box>

      {/* Metrics Summary */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: 'primary.main', color: 'white' }}>
            <CardContent>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>Active Sessions</Typography>
              <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                {metrics.total_active || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: 'success.main', color: 'white' }}>
            <CardContent>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>Avg Confidence</Typography>
              <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                {Math.round((metrics.avg_confidence || 0) * 100)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: 'warning.main', color: 'white' }}>
            <CardContent>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>Avg Risk Score</Typography>
              <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                {Math.round((metrics.avg_risk || 0) * 100)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: 'error.main', color: 'white' }}>
            <CardContent>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>Drift Alerts</Typography>
              <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                {metrics.drift_alerts || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Sessions Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Monitor color="primary" /> Active Identity Sessions
          </Typography>
          <Paper sx={{ width: '100%', overflow: 'hidden' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Person</TableCell>
                  <TableCell>Device</TableCell>
                  <TableCell>Location</TableCell>
                  <TableCell align="right">Duration</TableCell>
                  <TableCell align="right">Confidence</TableCell>
                  <TableCell align="right">Risk</TableCell>
                  <TableCell align="right">Behavior</TableCell>
                  <TableCell align="right">Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredSessions.map((session) => {
                  const duration = Math.floor((Date.now() - new Date(session.start_time).getTime()) / 60000);
                  return (
                    <TableRow key={session.id}>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Avatar sx={{ width: 32, height: 32, fontSize: '0.8rem' }}>
                            {session.person_name[0]}
                          </Avatar>
                          <Box>
                            <Typography variant="subtitle2">{session.person_name}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {session.person_id}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{session.device_id}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={session.location} size="small" />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{duration} min</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography fontWeight={600} color={getConfidenceColor(session.confidence)}>
                          {Math.round(session.confidence * 100)}%
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography fontWeight={600} color={getRiskColor(session.risk_score)}>
                          {Math.round(session.risk_score * 100)}%
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title={`Walking: ${session.behaviors?.walking_speed}m/s`}>
                          <Chip label={`Posture: ${Math.round(session.behaviors?.posture * 100)}%`} size="small" />
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right">
                        <Chip
                          label={session.risk_score > 0.3 ? 'Review' : 'Normal'}
                          size="small"
                          color={session.risk_score > 0.3 ? 'warning' : 'success'}
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Paper>
        </CardContent>
      </Card>

      {/* Behavioral Drift Chart */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Behavioral Drift Monitoring</Typography>
          <Box sx={{ height: 200, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
            <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 7 }}>
              Behavioral drift visualization - tracking walking patterns, posture changes, and interaction styles
            </Typography>
            <Typography variant="body2" color="text.secondary" align="center">
              (Real-time updates every 30 seconds)
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}

export default SessionsTab;