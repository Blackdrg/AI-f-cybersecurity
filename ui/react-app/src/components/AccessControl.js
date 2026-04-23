import React, { useState } from 'react';
import { Paper, Typography, Button, Switch, Box } from '@mui/material';
import { LockOpen } from '@mui/icons-material';

const AccessControl = () => {
  const [doorUnlocked, setDoorUnlocked] = useState(false);

  const triggerUnlock = async () => {
    try {
      await fetch('/api/webhooks/door_unlock', { method: 'POST' });
      setDoorUnlocked(true);
      setTimeout(() => setDoorUnlocked(false), 5000);
    } catch (e) {
      console.error('Unlock failed', e);
    }
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>Access Control</Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <LockOpen sx={{ mr: 1 }} color={doorUnlocked ? 'success' : 'action'} />
        <Typography>Door Lock</Typography>
        <Switch sx={{ ml: 2 }} />
      </Box>
      <Button variant="contained" onClick={triggerUnlock} disabled={doorUnlocked}>
        {doorUnlocked ? 'Unlocked (5s)' : 'Unlock Door'}
      </Button>
    </Paper>
  );
};

export default AccessControl;

