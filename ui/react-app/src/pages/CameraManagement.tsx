import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Grid, Paper, Button, 
  TextField, Dialog, DialogTitle, DialogContent, 
  DialogActions, Card, CardContent, CardMedia,
  Chip, IconButton, List, ListItem, ListItemText
} from '@mui/material';
import { CameraAlt, VideocamOff, Add, Settings, Delete } from '@mui/icons-material';
import API from '../services/api';

const CameraManagement = () => {
  const [cameras, setCameras] = useState([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newCamera, setNewCamera] = useState({ name: '', rtsp_url: '', location: '' });

  useEffect(() => {
    fetchCameras();
  }, []);

  const fetchCameras = async () => {
    try {
      // For demo, we use a placeholder org_id
      const res = await API.get('/api/orgs/any/cameras');
      setCameras(res.data);
    } catch (err) {
      console.error("Failed to fetch cameras");
    }
  };

  const handleAddCamera = async () => {
    try {
      await API.post('/api/orgs/any/cameras', newCamera);
      setIsDialogOpen(false);
      setNewCamera({ name: '', rtsp_url: '', location: '' });
      fetchCameras();
    } catch (err) {
      console.error("Failed to add camera");
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Camera Management</Typography>
        <Button 
          variant="contained" 
          startIcon={<Add />}
          onClick={() => setIsDialogOpen(true)}
        >
          Add Camera
        </Button>
      </Box>

      <Grid container spacing={3}>
        {cameras.length > 0 ? cameras.map(camera => (
          <Grid item xs={12} md={6} lg={4} key={camera.camera_id}>
            <Card>
              <Box sx={{ position: 'relative', bgcolor: '#000', pt: '56.25%' }}>
                <Box 
                  sx={{ 
                    position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexDirection: 'column', color: 'rgba(255,255,255,0.3)'
                  }}
                >
                  <VideocamOff sx={{ fontSize: 48, mb: 1 }} />
                  <Typography variant="caption">Stream Offline</Typography>
                </Box>
                <Chip 
                  label={camera.status.toUpperCase()} 
                  size="small"
                  color={camera.status === 'online' ? 'success' : 'error'}
                  sx={{ position: 'absolute', top: 8, right: 8 }}
                />
              </Box>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box>
                    <Typography variant="h6">{camera.name}</Typography>
                    <Typography variant="body2" color="text.secondary">{camera.location || 'No location set'}</Typography>
                  </Box>
                  <Box>
                    <IconButton size="small"><Settings /></IconButton>
                    <IconButton size="small" color="error"><Delete /></IconButton>
                  </Box>
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block', wordBreak: 'break-all' }}>
                  {camera.rtsp_url || 'No RTSP URL'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )) : (
          <Grid item xs={12}>
            <Paper sx={{ p: 8, textAlign: 'center', bgcolor: 'background.default', border: '2px dashed #333' }}>
              <CameraAlt sx={{ fontSize: 64, mb: 2, opacity: 0.2 }} />
              <Typography variant="h6" color="text.secondary">No cameras configured</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Connect your RTSP streams to start live monitoring.
              </Typography>
              <Button variant="outlined" onClick={() => setIsDialogOpen(true)}>Connect First Camera</Button>
            </Paper>
          </Grid>
        )}
      </Grid>

      <Dialog open={isDialogOpen} onClose={() => setIsDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Camera Stream</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField 
              label="Camera Name" 
              fullWidth 
              value={newCamera.name}
              onChange={(e) => setNewCamera({...newCamera, name: e.target.value})}
            />
            <TextField 
              label="RTSP Stream URL" 
              fullWidth 
              placeholder="rtsp://admin:password@192.168.1.100:554/stream1"
              value={newCamera.rtsp_url}
              onChange={(e) => setNewCamera({...newCamera, rtsp_url: e.target.value})}
            />
            <TextField 
              label="Location (e.g., Main Entrance)" 
              fullWidth 
              value={newCamera.location}
              onChange={(e) => setNewCamera({...newCamera, location: e.target.value})}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddCamera}>Add Camera</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CameraManagement;
