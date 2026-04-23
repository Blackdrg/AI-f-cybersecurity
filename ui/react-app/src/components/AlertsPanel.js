import React, { useState, useEffect } from 'react';
import { Paper, Typography, List, ListItem, ListItemText, Chip, Badge } from '@mui/material';
import { Warning, Notifications } from '@mui/icons-material';

const AlertsPanel = ({ orgId = 'org123' }) => {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await fetch(`/api/orgs/${orgId}/alerts`);
        const data = await res.json();
        setAlerts(data.slice(0,10));  // Latest 10
      } catch (e) {
        console.error('Alerts fetch error', e);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, [orgId]);

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Badge badgeContent={alerts.length} color="error">
          <Notifications />
        </Badge>
        <Typography variant="h6" sx={{ ml: 1 }}>Alerts</Typography>
      </Box>
      <List dense>
        {alerts.map((alert, i) => (
          <ListItem key={i}>
            <Warning color="error" sx={{ mr: 1 }} />
            <ListItemText 
              primary={alert.rule_name || 'Unknown person detected'}
              secondary={new Date(alert.event_timestamp).toLocaleString()}
            />
            <Chip label={alert.severity || 'medium'} size="small" />
          </ListItem>
        ))}
        {alerts.length === 0 && <Typography variant="body2" color="text.secondary">No alerts</Typography>}
      </List>
    </Paper>
  );
};

export default AlertsPanel;

