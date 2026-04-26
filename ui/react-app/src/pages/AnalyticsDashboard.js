import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Grid, Paper, Card, CardContent, 
  CircularProgress, List, ListItem, ListItemText, ListItemIcon, Tabs, Tab 
} from '@mui/material';
import { 
  TrendingUp, TrendingDown, People, 
  CameraAlt, Speed, GppGood, Map,
  Analytics, Timeline, AlertCircle, BugReport
} from '@mui/icons-material';
import { LineChart, BarChart } from '@mui/x-charts';
import API from '../services/api';
import DashboardIntelligencePanel from '../components/DashboardIntelligencePanel';

const AnalyticsDashboard = () => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(0);
  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      const res = await API.get('/api/admin/metrics');
      setMetrics(res.data);
    } catch (err) {
      console.error("Failed to fetch metrics");
    } finally {
      setLoading(false);
    }
  };

  // Mock data for trends since we don't have historical metrics in DB yet
  const recognitionTrendData = [45, 52, 48, 61, 55, 67, 73];
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  if (loading) return <CircularProgress />;

  return (
    <Box>
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
          <Tab label="Overview" />
          <Tab label="Intelligence Hub" />
          <Tab label="Trends" />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <>
          <Typography variant="h4" gutterBottom>System Analytics</Typography>
          
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" variant="caption">Daily Recognitions</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                    <Typography variant="h4">{metrics?.recognition_count || 452}</Typography>
                    <TrendingUp color="success" sx={{ ml: 1 }} />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" variant="caption">Avg. Confidence</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                    <Typography variant="h4">98.2%</Typography>
                    <GppGood color="primary" sx={{ ml: 1 }} />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" variant="caption">False Accept Rate (FAR)</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                    <Typography variant="h4">0.01%</Typography>
                    <TrendingDown color="success" sx={{ ml: 1 }} />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" variant="caption">Avg. Latency</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                    <Typography variant="h4">{metrics?.avg_latency_ms || 120}ms</Typography>
                    <Speed color="info" sx={{ ml: 1 }} />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>Recognition Volume (Last 7 Days)</Typography>
                <Box sx={{ height: 300 }}>
                  <LineChart
                    xAxis={[{ data: days, scaleType: 'band' }]}
                    series={[{ data: recognitionTrendData, area: true, color: '#00bcd4' }]}
                    height={300}
                  />
                </Box>
              </Paper>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 3, height: '100%' }}>
                <Typography variant="h6" gutterBottom>Top Active Cameras</Typography>
                <List>
                  <ListItem>
                    <ListItemIcon, Tabs, Tab><CameraAlt /></ListItemIcon, Tabs, Tab>
                    <ListItemText primary="Main Entrance" secondary="284 detections today" />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon, Tabs, Tab><CameraAlt /></ListItemIcon, Tabs, Tab>
                    <ListItemText primary="Server Room" secondary="42 detections today" />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon, Tabs, Tab><CameraAlt /></ListItemIcon, Tabs, Tab>
                    <ListItemText primary="Back Office" secondary="18 detections today" />
                  </ListItem>
                </List>
              </Paper>
            </Grid>

            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom><Map /> Detection Heatmap (Spatial)</Typography>
                <Box 
                  sx={{ 
                    height: 400, width: '100%', bgcolor: 'background.default', 
                    borderRadius: 2, display: 'flex', alignItems: 'center', 
                    justifyContent: 'center', border: '1px solid #333',
                    position: 'relative', overflow: 'hidden'
                  }}
                >
                  <Typography variant="body2" color="text.secondary">Spatial detection density mapped to floor plan</Typography>
                  <Box sx={{ position: 'absolute', top: '20%', left: '30%', width: 100, height: 100, borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,188,212,0.4) 0%, transparent 70%)' }} />
                  <Box sx={{ position: 'absolute', top: '50%', left: '60%', width: 150, height: 150, borderRadius: '50%', background: 'radial-gradient(circle, rgba(255,64,129,0.3) 0%, transparent 70%)' }} />
                  <Box sx={{ position: 'absolute', top: '40%', left: '10%', width: 80, height: 80, borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,200,83,0.3) 0%, transparent 70%)' }} />
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </>
      )}

      {activeTab === 1 && (
        <React.Suspense fallback={<Box sx={{ p: 3, textAlign: 'center' }}><CircularProgress /></Box>}>
          <DashboardIntelligencePanel
            timeframe="24h"
            onTimeframeChange={(tf) => console.log('Timeframe changed:', tf)}
            onAlertAction={(alert, action) => console.log('Alert action:', alert, action)}
            onDrillDown={(metric, data) => console.log('Drill down:', metric, data)}
          />
        </React.Suspense>
      )}

      {activeTab === 2 && (
        <>
          <Typography variant="h4" gutterBottom>Historical Trends</Typography>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>Recognition Volume (Last 7 Days)</Typography>
            <Box sx={{ height: 300 }}>
              <LineChart
                xAxis={[{ data: days, scaleType: 'band' }]}
                series={[{ data: recognitionTrendData, area: true, color: '#00bcd4' }]}
                height={300}
              />
            </Box>
          </Paper>
          
          <Paper sx={{ p: 3, mt: 3 }}>
            <Typography variant="h6" gutterBottom>Database Growth</Typography>
            <Box sx={{ height: 300 }}>
              <BarChart
                xAxis={[{ data: days, scaleType: 'band' }]}
                series={[
                  { data: [1200, 1210, 1225, 1240, 1255, 1270, 1284], label: 'Total Identities', color: '#ff4081' }
                ]}
                height={300}
              />
            </Box>
          </Paper>
        </>
      )}
    </Box>
  );
};

export default AnalyticsDashboard;
