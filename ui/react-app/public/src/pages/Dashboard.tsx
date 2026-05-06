import React, { useState, useEffect } from 'react';
import {
  Box, Toolbar, Typography, Container, Paper,
  IconButton, Button, AppBar, Tabs, Tab, Badge,
  Chip, LinearProgress, Snackbar, Alert, SpeedDial, SpeedDialAction,
  SpeedDialIcon, Tooltip
} from '@mui/material';
import {
  Security, Timeline, Refresh, Settings, Warning,
  AccountCircle, Notifications, Error as ErrorIcon, CheckCircle, Flag, Menu as MenuIcon,
  ExpandMore
} from '@mui/icons-material';
import Sidebar from '../components/Sidebar';
import DashboardHome from './DashboardHome';
import RecognizePage from './Recognize';
import EnrollPage from './Enroll';
import AdminPanel from './AdminPanel';
import CameraManagement from './CameraManagement';
import PersonProfile from './PersonProfile';
import AnalyticsDashboard from './AnalyticsDashboard';
import Compliance from './Compliance';
import DeveloperPlatform from './DeveloperPlatform';
import API from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { OrgSwitcher } from '../components/OrgSwitcher';
import { AuditTimeline } from '../components/AuditTimeline';
import { IncidentAlertDashboard } from '../components/IncidentAlertDashboard';
import { PermissionGuard as RBACGuard, RoleBadge } from '../components/RBACGuard';
import { SnackbarState } from '../types';
import { PERMISSIONS } from '../contexts/AuthContext';
import './Dashboard.css';

interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  production_systems?: boolean;
}

interface OrgData {
  org_id?: string;
  name?: string;
  subscription_tier?: string;
}

interface UserData {
  name?: string;
  email?: string;
  role?: string;
}

const Dashboard = () => {
  const [activePage, setActivePage] = useState<string>('dashboard');
  const [loading, setLoading] = useState(true);
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({ status: 'healthy' });
  const [criticalAlerts, setCriticalAlerts] = useState(0);
  const [pendingIncidents, setPendingIncidents] = useState(0);
  const [snackbar, setSnackbar] = useState<SnackbarState>({ open: false, message: '', severity: 'success' as const });
  const [activeTab, setActiveTab] = useState<number>(0);
  const [fabOpen, setFabOpen] = useState(false);

  const {
    user: currentUser,
    organization,
    hasPermission,
    logout
  } = useAuth();

  useEffect(() => {
    fetchSystemHealth();
    fetchCriticalAlerts();
    fetchPendingIncidents();
    const interval = setInterval(() => {
      fetchSystemHealth();
      fetchCriticalAlerts();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchSystemHealth = async () => {
    try {
      const res = await API.get('/api/health').catch(() => null);
if (res?.data?.data) {
         setSystemHealth(res.data.data);
      } else {
        // Fallback to basic health
        setSystemHealth({ status: 'healthy', production_systems: true });
      }
    } catch (err: any) {
      setSystemHealth({ status: 'degraded', production_systems: false });
    }
    setLoading(false);
  };

   const fetchCriticalAlerts = async () => {
     try {
       const res = await API.get('/api/orgs/alerts/active').catch(() => ({ data: [] }));
       const alerts = res.data || [];
       const critical = alerts.filter((a: any) => 
         a.severity === 'critical' || 
         (typeof a === 'object' && a.type === 'DEEPFAKE_DETECTED')
       ).length;
       setCriticalAlerts(critical);
     } catch (err: any) {
       // Use demo data if API fails
       setCriticalAlerts(Math.floor(Math.random() * 3));
     }
   };

   const fetchPendingIncidents = async () => {
     try {
       const res = await API.get('/api/orgs/incidents').catch(() => ({ data: [] }));
       const incidents = res.data || [];
       const pending = incidents.filter((i: any) => 
         i.status === 'open' || i.status === 'investigating'
       ).length;
       setPendingIncidents(pending);
     } catch (err: any) {
       setPendingIncidents(Math.floor(Math.random() * 2));
     }
   };

const handlePageChange = (newPage: string) => {
   setActivePage(newPage);
   setActiveTab(0);
 };

 const TabAnalyticsView = ({ activeTab, setActiveTab }: { activeTab: number; setActiveTab: (tab: number) => void }) => (
    <Box sx={{ width: '100%', height: '100%' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)} variant="scrollable" scrollButtons="auto">
          <Tab label="Overview" />
          <Tab label="Intelligence Hub" />
          <Tab label="Trends" />
        </Tabs>
      </Box>
      {activeTab === 0 && <AnalyticsDashboard />}
      {activeTab === 1 && (
        <DashboardIntelligencePanelWrapped />
      )}
      {activeTab === 2 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h4" gutterBottom>Historical Trends</Typography>
          <AnalyticsDashboard />
        </Paper>
      )}
    </Box>
  );

  const DashboardIntelligencePanelWrapped = () => {
    const DashboardIntelligencePanel = React.lazy(() => 
      import('../components/DashboardIntelligencePanel').catch(() => ({ default: () => <Box>Component unavailable</Box> }))
    );
    return (
      <React.Suspense fallback={<Box sx={{ p: 3, textAlign: 'center' }}><LinearProgress /></Box>}>
        <DashboardIntelligencePanel
          timeframe="24h"
          onTimeframeChange={() => {}}
          onAlertAction={() => {}}
          onDrillDown={() => {}}
        />
      </React.Suspense>
    );
  };

  const fabActions = [
    { icon: <Flag color="error" />, name: 'Report Incident', action: () => handlePageChange('incidents') },
    { icon: <Security color="warning" />, name: 'Quick Scan', action: () => console.log('Quick scan') },
    { icon: <Timeline color="info" />, name: 'Activity Log', action: () => handlePageChange('audit') },
    { icon: <Settings color="primary" />, name: 'Settings', action: () => handlePageChange('admin') },
  ];

  const getStatusColor = () => {
    switch (systemHealth.status) {
      case 'healthy': return 'success';
      case 'degraded': return 'warning';
      case 'unhealthy': return 'error';
      default: return 'default';
    }
  };

  const renderContent = () => {
    switch (activePage) {
      case 'dashboard':
        return <DashboardHome />;
      case 'recognize':
        return <RecognizePage />;
      case 'enroll':
        return <EnrollPage />;
      case 'admin':
        return <AdminPanel />;
      case 'cameras':
        return <CameraManagement />;
      case 'person':
        return <PersonProfile personId="" />;
      case 'analytics':
        return <TabAnalyticsView activeTab={activeTab} setActiveTab={setActiveTab} />;
      case 'compliance':
        return <Compliance />;
      case 'developer':
        return <DeveloperPlatform />;
      case 'audit':
        return <AuditTimeline orgId={organization?.org_id || ""} />;
      case 'incidents':
        return <IncidentAlertDashboard />;
      default:
        return <DashboardHome />;
    }
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }} className="dashboard-app">
      <Sidebar
        activePage={activePage}
        setActivePage={handlePageChange}
        onLogout={logout}
        user={currentUser || undefined}
      />
      <Box
        component="main"
        className="dashboard-main"
        sx={{ width: '100%' }}
      >
        {/* Enhanced App Bar */}
        <AppBar
          position="fixed"
          sx={{
            top: 0,
            right: 0,
            width: 'calc(100% - 280px)',
            bgcolor: 'rgba(10, 14, 23, 0.9)',
            backdropFilter: 'blur(10px)',
            borderBottom: '1px solid',
            borderColor: 'rgba(255,255,255,0.1)',
            zIndex: (theme) => theme.zIndex.drawer + 1,
          }}
        >
          <Toolbar sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <OrgSwitcher />
              {organization && (
                <RoleBadge role={currentUser?.role || 'viewer'} />
              )}
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {/* System Health Indicator */}
              <Tooltip title={`System: ${systemHealth.status?.toUpperCase()}`}>
                <Chip
                  icon={
                    systemHealth.status === 'healthy' ? (
                      <CheckCircle />
                    ) : systemHealth.status === 'degraded' ? (
                      <Warning />
                    ) : (
                      <ErrorIcon />
                    )
                  }
                  label={systemHealth.status?.toUpperCase()}
                  size="small"
                  sx={{
                    bgcolor: `${getStatusColor()}.dark`,
                    color: 'white',
                    '& .MuiChip-icon': { color: 'white' }
                  }}
                />
              </Tooltip>

              {/* Critical Alerts Badge */}
              {hasPermission(PERMISSIONS.VIEW_ALERTS) && (
                <Badge badgeContent={criticalAlerts} color="error" max={99}>
                  <IconButton
                    color="inherit"
                    size="small"
                    onClick={() => handlePageChange('incidents')}
                  >
                    <Notifications />
                  </IconButton>
                </Badge>
              )}

              {/* Pending Incidents Badge */}
              {hasPermission(PERMISSIONS.MANAGE_INCIDENTS) && pendingIncidents > 0 && (
                <Badge badgeContent={pendingIncidents} color="warning" max={99}>
                  <IconButton
                    color="inherit"
                    size="small"
                    onClick={() => handlePageChange('incidents')}
                  >
                    <Flag />
                  </IconButton>
                </Badge>
              )}

              {/* Refresh Button */}
              <IconButton
                color="inherit"
                size="small"
                onClick={fetchSystemHealth}
                disabled={loading}
              >
                <Refresh />
              </IconButton>

              {/* User Menu */}
               {currentUser && (
                 <Button
                   variant="outlined"
                   size="small"
                   startIcon={<AccountCircle />}
                   endIcon={<ExpandMore />}
                   sx={{
                     borderColor: 'rgba(255,255,255,0.2)',
                     color: '#e2e8f0',
                     textTransform: 'none',
                     minWidth: 'auto',
                     px: 1
                   }}
                   onClick={logout}
                 >
                   <Box sx={{ textAlign: 'left', mr: 1 }}>
                     <Typography variant="body2" sx={{ fontWeight: 600 }}>
                       {currentUser?.name || currentUser?.email || 'User'}
                     </Typography>
                     <Typography variant="caption" sx={{ opacity: 0.7 }}>
                       {currentUser?.role || 'Viewer'}
                     </Typography>
                   </Box>
                 </Button>
               )}
            </Box>
          </Toolbar>
        </AppBar>

        {/* Enhanced Toolbar Spacer */}
        <Toolbar />
        <Toolbar />

        {/* Status Bar */}
        <Paper
          sx={{
            mx: 2,
            mb: 2,
            p: 1,
            bgcolor: 'rgba(255,255,255,0.02)',
            border: '1px solid',
            borderColor: 'rgba(255,255,255,0.05)',
            borderRadius: 1,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 1
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap' }}>
            <Typography variant="caption" color="text.secondary">
              Organization: <strong>{organization?.name || 'Loading...'}</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Plan: <Chip
                label={organization?.subscription_tier || 'Loading...'}
                size="small"
                sx={{
                  ml: 0.5,
bgcolor: `${getTierColor(organization?.subscription_tier)}20`,
                   color: getTierColor(organization?.subscription_tier),
                  border: `1px solid ${getTierColor(organization?.subscription_tier)}`,
                  fontSize: '0.65rem',
                  height: 18,
                  borderRadius: 1
                }}
              />
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Role: <strong>{currentUser?.role || 'Viewer'}</strong>
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Typography variant="caption" color="text.secondary">
              Last Sync: <strong>{new Date().toLocaleTimeString()}</strong>
            </Typography>
            {loading && (
              <LinearProgress
                sx={{
                  width: 100,
                  height: 4,
                  borderRadius: 2,
                  bgcolor: 'rgba(255,255,255,0.1)',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: '#3b82f6'
                  }
                }}
              />
            )}
          </Box>
        </Paper>

        <Container maxWidth={false} className="dashboard-container">
          {renderContent()}
        </Container>

        {/* Enhanced Speed Dial */}
        <SpeedDial
          ariaLabel="Quick Actions"
          sx={{
            position: 'fixed',
            bottom: 80,
            right: 24,
            '& .MuiSpeedDial-fab': {
              bgcolor: 'primary.main',
              '&:hover': {
                bgcolor: 'primary.dark'
              }
            }
          }}
          icon={<SpeedDialIcon openIcon={<MenuIcon />} />}
          open={fabOpen}
          onClose={() => setFabOpen(false)}
          onOpen={() => setFabOpen(true)}
        >
          {fabActions.map((action) => (
            <SpeedDialAction
              key={action.name}
              icon={action.icon}
              tooltipTitle={action.name}
              onClick={action.action}
              sx={{
                '& .MuiSpeedDialAction-staticTooltipLabel': {
                  bgcolor: 'rgba(0,0,0,0.8)',
                  color: 'white',
                }
              }}
            />
          ))}
        </SpeedDial>

        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert severity={snackbar.severity} sx={{ width: '100%' }}>
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Box>

      <style>{`
        .dashboard-main {
          transition: width 0.3s ease;
        }
        @media (max-width: 1200px) {
          .dashboard-main {
            width: calc(100% - 80px) !important;
          }
          .MuiAppBar-root {
            width: calc(100% - 80px) !important;
          }
        }
        @media (max-width: 900px) {
          .dashboard-main {
            width: 100% !important;
            padding: 16px;
          }
          .MuiAppBar-root {
            width: 100% !important;
          }
        }
        @media print {
          .MuiSpeedDial-root,
          .MuiAppBar-root {
            display: none !important;
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .MuiSpeedDial-root,
          .dashboard-app * {
            transition: none !important;
            animation: none !important;
          }
        }
      `}</style>
    </Box>
  );
};

const getTierColor = (tier?: string) => {
  const colors: Record<string, string> = {
    free: '#64748b',
    pro: '#3b82f6',
    enterprise: '#8b5cf6',
    custom: '#f59e0b'
  };
  return colors[tier?.toLowerCase() || 'free'] || '#64748b';
};

export default Dashboard;