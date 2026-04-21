import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Grid, Paper, List, ListItem, 
  ListItemText, Divider, Button, TextField, 
  Dialog, DialogTitle, DialogContent, DialogActions,
  Chip, Table, TableBody, TableCell, TableHead, TableRow
} from '@mui/material';
import { VpnKey, Business, People, Receipt } from '@mui/icons-material';
import API from '../services/api';

const AdminPanel = () => {
  const [orgs, setOrgs] = useState([]);
  const [activeOrg, setActiveOrg] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);
  const [isKeyDialogOpen, setIsKeyDialogOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');

  useEffect(() => {
    fetchOrgs();
  }, []);

  const fetchOrgs = async () => {
    try {
      const res = await API.get('/api/organizations');
      setOrgs(res.data);
      if (res.data.length > 0) {
        setActiveOrg(res.data[0]);
      }
    } catch (err) {
      console.error("Failed to fetch organizations");
    }
  };

  const generateKey = async () => {
    if (!activeOrg) return;
    try {
      await API.post(`/api/organizations/${activeOrg.org_id}/api-keys?name=${newKeyName}`);
      setIsKeyDialogOpen(false);
      setNewKeyName('');
      // Refresh or show key
    } catch (err) {
      console.error("Failed to generate API key");
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Admin Dashboard</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom><Business /> Organizations</Typography>
            <List>
              {orgs.map(org => (
                <ListItem 
                  button 
                  key={org.org_id} 
                  selected={activeOrg?.org_id === org.org_id}
                  onClick={() => setActiveOrg(org)}
                >
                  <ListItemText primary={org.name} secondary={org.subscription_tier} />
                </ListItem>
              ))}
              <ListItem button>
                <ListItemText primary="+ Create New Org" sx={{ color: 'primary.main' }} />
              </ListItem>
            </List>
          </Paper>
        </Grid>

        <Grid item xs={12} md={9}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom><People /> Organization Members</Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>User</TableCell>
                      <TableCell>Role</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell>Admin User</TableCell>
                      <TableCell><Chip label="Admin" size="small" color="primary" /></TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="h6"><VpnKey /> API Keys</Typography>
                  <Button size="small" onClick={() => setIsKeyDialogOpen(true)}>Generate Key</Button>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Manage API keys for server-side integrations.
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText primary="Production Key" secondary="fr_live_...4a2b" />
                    <Chip label="Active" size="small" color="success" />
                  </ListItem>
                </List>
              </Paper>
            </Grid>

            <Grid item xs={12}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom><Receipt /> Billing & Invoices</Typography>
                <Box sx={{ display: 'flex', gap: 4, mb: 2 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Current Plan</Typography>
                    <Typography variant="h5">{activeOrg?.subscription_tier.toUpperCase()}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Next Invoice</Typography>
                    <Typography variant="h5">$0.00</Typography>
                  </Box>
                </Box>
                <Button variant="outlined">Manage Subscription</Button>
              </Paper>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      <Dialog open={isKeyDialogOpen} onClose={() => setIsKeyDialogOpen(false)}>
        <DialogTitle>Generate New API Key</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Key Name"
            fullWidth
            variant="standard"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsKeyDialogOpen(false)}>Cancel</Button>
          <Button onClick={generateKey} variant="contained">Generate</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AdminPanel;
