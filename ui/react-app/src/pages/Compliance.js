import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Paper, Grid, Button, 
  Table, TableBody, TableCell, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions,
  Alert, Chip, List, ListItem, ListItemText
} from '@mui/material';
import { 
  Gavel, Download, DeleteForever, 
  Security, Policy, Visibility 
} from '@mui/icons-material';
import API from '../services/api';

const Compliance = () => {
  const [consents, setConsents] = useState([]);
  const [isExportDialogOpen, setIsExportDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  useEffect(() => {
    // fetchConsents();
  }, []);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Compliance & Privacy</Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom><Gavel /> Consent Dashboard</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Overview of active biometric consents and their expiration status.
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Subject</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Expires</TableCell>
                  <TableCell>Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>John Doe</TableCell>
                  <TableCell>Face</TableCell>
                  <TableCell><Chip label="Active" color="success" size="small" /></TableCell>
                  <TableCell>2026-12-31</TableCell>
                  <TableCell>
                    <Button size="small" startIcon={<Visibility />}>View</Button>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Paper>

          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom><Security /> Data Retention Policy</Typography>
            <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="subtitle2">Automated Purge</Typography>
              <Typography variant="body2">
                Unidentified recognition events are deleted after 30 days.
                Audit logs are retained for 1 year.
              </Typography>
              <Button variant="outlined" size="small" sx={{ mt: 2 }}>Edit Policy</Button>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom><Download /> GDPR Data Export</Typography>
            <Typography variant="body2" sx={{ mb: 2 }}>
              Generate a machine-readable ZIP archive of all data associated with a specific identity.
            </Typography>
            <Button 
              fullWidth 
              variant="contained" 
              startIcon={<Download />}
              onClick={() => setIsExportDialogOpen(true)}
            >
              Export Identity Data
            </Button>
          </Paper>

          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom color="error"><DeleteForever /> Right to be Forgotten</Typography>
            <Typography variant="body2" sx={{ mb: 2 }}>
              Permanently delete all biometric templates and historical records for an individual.
            </Typography>
            <Button 
              fullWidth 
              variant="outlined" 
              color="error" 
              startIcon={<DeleteForever />}
              onClick={() => setIsDeleteDialogOpen(true)}
            >
              Delete Identity
            </Button>
          </Paper>
        </Grid>
      </Grid>

      <Dialog open={isExportDialogOpen} onClose={() => setIsExportDialogOpen(false)}>
        <DialogTitle>Data Export Request</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            The export process will gather all embeddings, recognition history, and consent logs into a JSON file. 
            This may take a few moments.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsExportDialogOpen(false)}>Cancel</Button>
          <Button variant="contained">Start Export</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={isDeleteDialogOpen} onClose={() => setIsDeleteDialogOpen(false)}>
        <DialogTitle sx={{ color: 'error.main' }}>Confirm Permanent Deletion</DialogTitle>
        <DialogContent>
          <Alert severity="warning">
            This action is irreversible. All biometric data and recognition history for this person will be wiped from the system.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsDeleteDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="error">Delete Everything</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Compliance;
