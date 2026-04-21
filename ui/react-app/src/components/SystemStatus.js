import React, { useState, useEffect } from 'react';
import { 
  Paper, 
  Typography, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText, 
  Box, 
  CircularProgress,
  Chip
} from '@mui/material';
import { 
  CheckCircle, 
  Error, 
  Warning, 
  CloudQueue, 
  Payment, 
  SmartToy, 
  Search, 
  Storage 
} from '@mui/icons-material';
import { checkDependencies } from '../services/api';

const SystemStatus = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    try {
      const data = await checkDependencies();
      if (data.success) {
        setStatus(data.data);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError('Failed to fetch system status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (state) => {
    switch (state) {
      case 'healthy':
        return <CheckCircle color="success" />;
      case 'degraded':
        return <Warning color="warning" />;
      case 'unhealthy':
      case 'unconfigured':
        return <Error color="error" />;
      default:
        return <CloudQueue />;
    }
  };

  const getStatusColor = (state) => {
    switch (state) {
      case 'healthy': return 'success';
      case 'degraded': return 'warning';
      case 'unhealthy':
      case 'unconfigured': return 'error';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Paper sx={{ p: 2, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
        <CircularProgress size={24} sx={{ mr: 2 }} />
        <Typography>Loading System Status...</Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 2, bgcolor: 'error.light' }}>
        <Typography color="error">Error: {error}</Typography>
      </Paper>
    );
  }

  const { overall, dependencies } = status;

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">System Health</Typography>
        <Chip 
          label={overall.toUpperCase()} 
          color={getStatusColor(overall)} 
          size="small" 
        />
      </Box>
      <List dense>
        <ListItem>
          <ListItemIcon><Payment /></ListItemIcon>
          <ListItemText primary="Stripe (Payments)" />
          {getStatusIcon(dependencies.payments)}
        </ListItem>
        <ListItem>
          <ListItemIcon><SmartToy /></ListItemIcon>
          <ListItemText primary="OpenAI (LLM)" />
          {getStatusIcon(dependencies.llm)}
        </ListItem>
        <ListItem>
          <ListItemIcon><Search /></ListItemIcon>
          <ListItemText primary="Bing Search" />
          {getStatusIcon(dependencies.search_bing)}
        </ListItem>
        <ListItem>
          <ListItemIcon><Search /></ListItemIcon>
          <ListItemText primary="Wikipedia" />
          {getStatusIcon(dependencies.search_wikipedia)}
        </ListItem>
        <ListItem>
          <ListItemIcon><Storage /></ListItemIcon>
          <ListItemText primary="Database" />
          {getStatusIcon(dependencies.database)}
        </ListItem>
      </List>
    </Paper>
  );
};

export default SystemStatus;
