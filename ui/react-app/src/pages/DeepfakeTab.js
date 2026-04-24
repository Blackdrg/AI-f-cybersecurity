import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Grid, Card, CardContent, Paper,
  Table, TableBody, TableCell, TableHead, TableRow,
  LinearProgress, Chip, Alert, Button, IconButton,
  Tooltip, Avatar, Badge, List, ListItem, ListItemText,
  ListItemAvatar, Divider
} from '@mui/material';
import {
  BugReport, Security, Radar, AlertCircle,
  CheckCircle, Error as ErrorIcon, Timeline,
  PlayCircle, Pause, Database, Block
} from '@mui/icons-material';
import API from '../services/api';

function DeepfakeTab() {
  const [threats, setThreats] = useState([]);
  const [stats, setStats] = useState({});
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    loadThreatData();
    if (isLive) {
      const interval = setInterval(loadThreatData, 5000);
      return () => clearInterval(interval);
    }
  }, [isLive]);

  const loadThreatData = async () => {
    try {
      const res = await API.get('/api/deepfake/threats');
      setThreats(res.data || []);
      setStats(res.data?.stats || {});
    } catch (err) {
      // Sample data
      setThreats([
        {
          id: 't_001',
          type: 'Deepfake Video',
          severity: 'critical',
          confidence: 0.95,
          target: 'Executive Account',
          source_ip: '192.168.1.100',
          timestamp: new Date(Date.now() - 2 * 60000).toISOString(),
          method: 'GAN Generation',
          artifacts: ['Temporal inconsistency', 'GAN artifacts'],
          action: 'blocked'
        },
        {
          id: 't_002',
          type: 'Lip-sync Attack',
          severity: 'high',
          confidence: 0.87,
          target: 'Voice Auth System',
          source_ip: '10.0.0.45',
          timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
          method: 'Audio-Video Mismatch',
          artifacts: ['Audio-visual desync', 'Phoneme mismatch'],
          action: 'challenged'
        },
        {
          id: 't_003',
          type: '3D Mask Attack',
          severity: 'high',
          confidence: 0.92,
          target: 'Physical Access Control',
          source_ip: '172.16.0.23',
          timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
          method: 'Silicone Mask',
          artifacts: ['Depth inconsistency', 'Reflection anomaly'],
          action: 'denied'
        },
        {
          id: 't_004',
          type: 'Spoofing Attempt',
          severity: 'medium',
          confidence: 0.78,
          target: 'Mobile App Login',
          source_ip: '203.0.113.50',
          timestamp: new Date(Date.now() - 30 * 60000).toISOString(),
          method: 'Photo Replay',
          artifacts: ['No liveness response', 'Static texture'],
          action: 'blocked'
        },
        {
          id: 't_005',
          type: 'AI-generated Content',
          severity: 'low',
          confidence: 0.65,
          target: 'Document Verification',
          source_ip: '198.51.100.75',
          timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
          method: 'Synthetic ID',
          artifacts: ['Watermark detected', 'GAN fingerprint'],
          action: 'flagged'
        }
      ]);
      setStats({
        total_threats: 5,
        blocked: 2,
        challenged: 1,
        denied: 1,
        flagged: 1,
        detection_rate: 98.5,
        false_positive_rate: 0.3
      });
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return '#ef4444';
      case 'high': return '#f59e0b';
      case 'medium': return '#3b82f6';
      case 'low': return '#10b981';
      default: return '#64748b';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold">
            Deepfake Detection Center
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Multi-modal deepfake and synthetic identity defense
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button
            variant={isLive ? 'contained' : 'outlined'}
            startIcon={isLive ? <Pause /> : <PlayArrow />}
            onClick={() => setIsLive(!isLive)}
            color={isLive ? 'error' : 'primary'}
          >
            {isLive ? 'Stop Live' : 'Start Live'}
          </Button>
          <Button variant="contained" startIcon={<Database />}>
            Threat Intelligence
          </Button>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: 'error.main', color: 'white' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <BugReport />
                <Typography variant="body2" sx={{ opacity: 0.8 }}>Active Threats</Typography>
              </Box>
              <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                {stats.total_threats || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: 'success.main', color: 'white' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CheckCircle />
                <Typography variant="body2" sx={{ opacity: 0.8 }}>Detection Rate</Typography>
              </Box>
              <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                {stats.detection_rate || 98.5}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: 'warning.main', color: 'white' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AlertCircle />
                <Typography variant="body2" sx={{ opacity: 0.8 }}>False Positive</Typography>
              </Box>
              <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                {stats.false_positive_rate || 0.3}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ bgcolor: 'info.main', color: 'white' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Block />
                <Typography variant="body2" sx={{ opacity: 0.8 }}>Blocked</Typography>
              </Box>
              <Typography variant="h4" fontWeight="bold" sx={{ mt: 1 }}>
                {stats.blocked || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Live Threat Feed */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Radar color="error" /> Live Threat Feed
                </Typography>
                <Chip label={`${threats.length} total`} size="small" />
              </Box>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Type</TableCell>
                    <TableCell>Target</TableCell>
                    <TableCell>Severity</TableCell>
                    <TableCell align="right">Confidence</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell>Time</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {threats.map((threat) => (
                    <TableRow key={threat.id}>
                      <TableCell>
                        <Typography variant="body2" fontWeight={500}>
                          {threat.type}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {threat.method}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{threat.target}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={threat.severity}
                          size="small"
                          sx={{
                            bgcolor: `${getSeverityColor(threat.severity)}22`,
                            color: getSeverityColor(threat.severity),
                            fontWeight: 600,
                          }}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography fontWeight={600}>
                          {Math.round(threat.confidence * 100)}%
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={threat.action}
                          size="small"
                          color={
                            threat.action === 'blocked' ? 'error' :
                            threat.action === 'denied' ? 'warning' :
                            'info'
                          }
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(threat.timestamp).toLocaleTimeString()}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>

        {/* Detection Methods */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Detection Methods</Typography>
              <List dense>
                {[
                  { name: 'GAN Artifact Detection', value: 98, color: '#ef4444' },
                  { name: 'Temporal Consistency', value: 96, color: '#f59e0b' },
                  { name: '3D Geometry Check', value: 94, color: '#3b82f6' },
                  { name: 'Lip-sync Analysis', value: 92, color: '#8b5cf6' },
                  { name: 'Watermark Detection', value: 89, color: '#10b981' },
                ].map((method, idx) => (
                  <ListItem key={idx} sx={{ px: 0 }}>
                    <ListItemText primary={method.name} />
                    <Box sx={{ width: 60, textAlign: 'right' }}>
                      <Typography variant="body2" fontWeight={600} color={method.color}>
                        {method.value}%
                      </Typography>
                    </Box>
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>

          {/* Recent Blocked */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Recently Blocked</Typography>
              <List dense>
                {threats.slice(0, 3).map((t, idx) => (
                  <ListItem key={t.id} sx={{ px: 0, py: 1 }}>
                    <ListItemAvatar>
                      <Avatar sx={{ width: 32, height: 32, bgcolor: `${getSeverityColor(t.severity)}22` }}>
                        <BugReport sx={{ fontSize: 16, color: getSeverityColor(t.severity) }} />
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={t.type}
                      secondary={t.target}
                      primaryTypographyProps={{ variant: 'body2' }}
                      secondaryTypographyProps={{ variant: 'caption' }}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Threat Details */}
      {threats.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Threat Intensity Over Time</Typography>
            <Box sx={{ height: 150, p: 2, bgcolor: 'action.hover', borderRadius: 1, position: 'relative' }}>
              <svg width="100%" height="100%" viewBox="0 0 400 120">
                <line x1="20" y1="100" x2="380" y2="100" stroke="rgba(255,255,255,0.3)" />
                {threats.map((t, idx) => {
                  const x = 40 + idx * 70;
                  const y = 100 - (t.confidence * 80);
                  return (
                    <g key={t.id}>
                      <circle cx={x} cy={y} r={6} fill={getSeverityColor(t.severity)} />
                      <line x1={x} y1={100} x2={x} y2={y} stroke={getSeverityColor(t.severity)} strokeWidth="1" strokeDasharray="4,4" />
                    </g>
                  );
                })}
              </svg>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}

export default DeepfakeTab;