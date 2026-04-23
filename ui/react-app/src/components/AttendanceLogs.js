import React, { useState, useEffect } from 'react';
import { Paper, Typography, List, ListItem, ListItemText, IconButton, Chip } from '@mui/material';
import { Download, Search } from '@mui/icons-material';

const AttendanceLogs = ({ orgId = 'org123' }) => {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      const res = await fetch(`/api/orgs/${orgId}/logs`);
      const data = await res.json();
      setLogs(data.slice(0,20));
    } catch (e) {
      console.error(e);
    }
  };

  const exportCSV = () => {
    const csv = logs.map(log => `${log.timestamp},${log.person_name || 'Unknown'},${log.camera},${log.action}`).join('\\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'attendance.csv';
    a.click();
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">Attendance Logs</Typography>
        <IconButton onClick={exportCSV} title="Export CSV">
          <Download />
        </IconButton>
      </Box>
      <List dense>
        {logs.map((log, i) => (
          <ListItem key={i}>
            <ListItemText 
              primary={log.person_name || 'Unknown'}
              secondary={`${log.timestamp} - ${log.camera} - ${log.action}`}
            />
            <Chip label={log.role || 'Visitor'} size="small" />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};

export default AttendanceLogs;

