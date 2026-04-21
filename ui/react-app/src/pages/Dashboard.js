import React, { useState } from 'react';
import { Box, Toolbar, Typography, Container, Grid, Paper, Card, CardContent } from '@mui/material';
import { People, CameraAlt, History, Assessment } from '@mui/icons-material';
import Sidebar from '../components/Sidebar';
import SystemStatus from '../components/SystemStatus';
import RecognizePage from './Recognize';
import EnrollPage from './Enroll';
import AdminPanel from './AdminPanel';
import CameraManagement from './CameraManagement';
import PersonProfile from './PersonProfile';
import AnalyticsDashboard from './AnalyticsDashboard';
import Compliance from './Compliance';
import DeveloperPlatform from './DeveloperPlatform';

const DashboardHome = () => (
  <Box>
    <Typography variant="h4" gutterBottom>System Overview</Typography>
    <Grid container spacing={3}>
      <Grid item xs={12} sm={6} md={3}>
        <Card sx={{ bgcolor: 'primary.main', color: 'primary.contrastText' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <People sx={{ mr: 1 }} />
              <Typography variant="h6">Total Enrolled</Typography>
            </Box>
            <Typography variant="h3">1,284</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card sx={{ bgcolor: 'success.main', color: 'success.contrastText' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <CameraAlt sx={{ mr: 1 }} />
              <Typography variant="h6">Recognitions Today</Typography>
            </Box>
            <Typography variant="h3">452</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card sx={{ bgcolor: 'info.main', color: 'info.contrastText' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <History sx={{ mr: 1 }} />
              <Typography variant="h6">Avg Latency</Typography>
            </Box>
            <Typography variant="h3">120ms</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card sx={{ bgcolor: 'secondary.main', color: 'secondary.contrastText' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Assessment sx={{ mr: 1 }} />
              <Typography variant="h6">Accuracy</Typography>
            </Box>
            <Typography variant="h3">99.8%</Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>

    <Grid container spacing={3} sx={{ mt: 3 }}>
      <Grid item xs={12} md={4}>
        <SystemStatus />
      </Grid>
      <Grid item xs={12} md={8}>
        <Paper sx={{ p: 2, height: '100%' }}>
          <Typography variant="h6" gutterBottom>Recent Activity</Typography>
          <Typography variant="body2" color="text.secondary">
            No recent recognitions recorded.
          </Typography>
        </Paper>
      </Grid>
    </Grid>
  </Box>
);

const Dashboard = ({ onLogout, user }) => {
  const [activePage, setActivePage] = useState('dashboard');

  const renderContent = () => {
    switch (activePage) {
      case 'dashboard':
        return <DashboardHome />;
      case 'enroll':
        return <EnrollPage />;
      case 'recognize':
        return <RecognizePage />;
      case 'admin':
        return <AdminPanel />;
      case 'cameras':
        return <CameraManagement />;
      case 'person-profile':
        return <PersonProfile personId={null} />; // Dynamic ID later
      case 'analytics':
        return <AnalyticsDashboard />;
      case 'compliance':
        return <Compliance />;
      case 'developer':
        return <DeveloperPlatform />;
      default:
        return <DashboardHome />;
    }
  };

  return (
    <Box sx={{ display: 'flex' }}>
      <Sidebar 
        activePage={activePage} 
        setActivePage={setActivePage} 
        onLogout={onLogout} 
        user={user}
      />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - 240px)` },
          minHeight: '100vh',
          bgcolor: 'background.default'
        }}
      >
        <Toolbar />
        <Container maxWidth="lg">
          {renderContent()}
        </Container>
      </Box>
    </Box>
  );
};

export default Dashboard;
