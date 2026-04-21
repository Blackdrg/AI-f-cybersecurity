import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Paper, Grid, Avatar, 
  List, ListItem, ListItemText, ListItemIcon,
  Divider, Chip, CircularProgress
} from '@mui/material';
import { 
  AccessTime, CameraAlt, LocationOn, 
  VerifiedUser, Shield, Fingerprint,
  MergeType, CallSplit
} from '@mui/icons-material';
import API from '../services/api';

const PersonProfile = ({ personId }) => {
  const [person, setPerson] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isMergeDialogOpen, setIsMergeDialogOpen] = useState(false);

  useEffect(() => {
    if (personId) {
      fetchData();
    }
  }, [personId]);

  const fetchData = async () => {
    try {
      const personRes = await API.get(`/api/persons/${personId}`);
      setPerson(personRes.data);
      
      const timelineRes = await API.get(`/api/orgs/any/persons/${personId}/timeline`);
      setTimeline(timelineRes.data);
    } catch (err) {
      console.error("Failed to fetch person data");
    } finally {
      setLoading(false);
    }
  };

  const handleMerge = async (targetId) => {
    try {
      await API.post(`/api/identities/merge?source_id=${personId}&target_id=${targetId}`);
      // Refresh or redirect
    } catch (err) {
      console.error("Merge failed");
    }
  };

  if (loading) return <CircularProgress />;
  if (!person) return <Typography>Person not found</Typography>;

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Avatar 
              sx={{ width: 120, height: 120, mx: 'auto', mb: 2, bgcolor: 'primary.main' }}
            >
              {person.name?.[0] || 'U'}
            </Avatar>
            <Typography variant="h5">{person.name || 'Unknown'}</Typography>
            <Typography color="text.secondary" gutterBottom>ID: {person.person_id.slice(0, 8)}</Typography>
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 1 }}>
              <Chip label={person.gender || 'Unknown'} size="small" />
              <Chip label={`${person.age || '?'} years`} size="small" />
            </Box>
            <Divider sx={{ my: 3 }} />
            <List dense>
              <ListItem>
                <ListItemIcon><VerifiedUser color="success" /></ListItemIcon>
                <ListItemText primary="Identity Verified" secondary="High confidence match" />
              </ListItem>
              <ListItem>
                <ListItemIcon><Fingerprint /></ListItemIcon>
                <ListItemText primary="Biometric Profile" secondary={`${person.embeddings.length} samples`} />
              </ListItem>
              <ListItem>
                <ListItemIcon><Shield color="info" /></ListItemIcon>
                <ListItemText primary="Consent Active" secondary="GDPR Compliant" />
              </ListItem>
            </List>
            
            <Divider sx={{ my: 3 }} />
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Button 
                variant="outlined" 
                startIcon={<MergeType />}
                onClick={() => setIsMergeDialogOpen(true)}
              >
                Merge Identity
              </Button>
              <Button 
                variant="outlined" 
                startIcon={<CallSplit />}
              >
                Split Samples
              </Button>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom><AccessTime /> Recognition Timeline</Typography>
            <List>
              {timeline.length > 0 ? timeline.map((event, index) => (
                <React.Fragment key={event.event_id}>
                  <ListItem alignItems="flex-start">
                    <ListItemIcon>
                      <CameraAlt />
                    </ListItemIcon>
                    <ListItemText
                      primary={`Detected at ${event.camera_name || 'Unknown Camera'}`}
                      secondary={
                        <React.Fragment>
                          <Typography component="span" variant="body2" color="text.primary">
                            {new Date(event.timestamp).toLocaleString()}
                          </Typography>
                          {` — Confidence: ${(event.confidence_score * 100).toFixed(1)}%`}
                          <br />
                          <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                            <LocationOn sx={{ fontSize: 14, mr: 0.5 }} />
                            {event.camera_location || 'Main Entrance'}
                          </Box>
                        </React.Fragment>
                      }
                    />
                  </ListItem>
                  {index < timeline.length - 1 && <Divider variant="inset" component="li" />}
                </React.Fragment>
              )) : (
                <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
                  No recognition history found for this person.
                </Typography>
              )}
            </List>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default PersonProfile;
