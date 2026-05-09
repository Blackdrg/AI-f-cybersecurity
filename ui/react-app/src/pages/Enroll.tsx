import React, { useState } from 'react';
import { Box, Typography, TextField, Button, Paper,  
  Checkbox, FormControlLabel, Alert, CircularProgress,
  List, ListItem, ListItemText, IconButton } from '@mui/material';
import { Grid } from '@mui/material';
import { Delete, CloudUpload, PersonAdd, Image as ImageIcon } from '@mui/icons-material';
import { enroll } from '../services/api';

const EnrollPage = () => {
  const [name, setName] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [consent, setConsent] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setFiles([...files, ...newFiles]);
      
      const newPreviews = newFiles.map(file => URL.createObjectURL(file));
      setPreviews([...previews, ...newPreviews]);
    }
  };

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
    URL.revokeObjectURL(previews[index]);
    setPreviews(previews.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) {
      setError("Please select at least one image");
      return;
    }
    if (!consent) {
      setError("Consent is required for enrollment");
      return;
    }

    setIsProcessing(true);
    setError(null);
    setMessage(null);

    try {
      const res = await enroll(files, name, consent);
      setMessage(res.data.message);
      setName('');
      setFiles([]);
      previews.forEach(p => URL.revokeObjectURL(p));
      setPreviews([]);
      setConsent(false);
    } catch (err: any) {
      setError(err.message || "Failed to enroll person");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Box maxWidth={800} sx={{ margin: '0 auto' }}>
      <Typography variant="h4" gutterBottom>Enroll New Person</Typography>
      <Paper sx={{ p: 4 }}>
        <form onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12 }}>
              <TextField
                fullWidth
                label="Full Name"
                value={name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
                required
                disabled={isProcessing}
              />
            </Grid>
            
            <Grid size={{ xs: 12 }}>
              <Typography variant="subtitle1" gutterBottom>Upload Images (Multiple recommended)</Typography>
              <Button
                variant="outlined"
                component="label"
                startIcon={<CloudUpload />}
                disabled={isProcessing}
                sx={{ mb: 2, p: 4, border: '2px dashed #333', width: '100%' }}
              >
                Drop images here or click to upload
                <input type="file" multiple hidden onChange={handleFileChange} accept="image/*" />
              </Button>
              
              <Grid container spacing={1} sx={{ mt: 1 }}>
                {previews.map((preview, index) => (
                  <Grid size={{ xs: 4, sm: 3, md: 2 }} key={index}>
                    <Box sx={{ position: 'relative', pt: '100%' }}>
                      <img 
                        src={preview} 
                        alt={`Preview ${index}`} 
                        style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'cover', borderRadius: 4 }} 
                      />
                      <IconButton 
                        size="small" 
                        sx={{ position: 'absolute', top: 2, right: 2, bgcolor: 'rgba(0,0,0,0.5)', '&:hover': { bgcolor: 'rgba(0,0,0,0.8)' } }}
                        onClick={() => removeFile(index)}
                        disabled={isProcessing}
                      >
                        <Delete fontSize="small" color="error" />
                      </IconButton>
                    </Box>
                  </Grid>
                ))}
                {files.length === 0 && (
                  <Grid size={{ xs: 12 }}>
                    <Box sx={{ p: 4, textAlign: 'center', bgcolor: 'background.default', borderRadius: 1, opacity: 0.5 }}>
                      <ImageIcon sx={{ fontSize: 48, mb: 1 }} />
                      <Typography>No images selected</Typography>
                    </Box>
                  </Grid>
                )}
              </Grid>
            </Grid>
            
            <Grid size={{ xs: 12 }}>
              <FormControlLabel
                control={
                   <Checkbox 
                     checked={consent} 
                     onChange={(e: React.ChangeEvent<HTMLInputElement>) => setConsent(e.target.checked)} 
                     disabled={isProcessing}
                     required
                   />
                }
                label="I consent to the collection and processing of my biometric data for identification purposes. ✅"
              />
            </Grid>
            
            <Grid size={{ xs: 12 }}>
              {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
              {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
              
              <Button
                fullWidth
                variant="contained"
                size="large"
                type="submit"
                disabled={isProcessing}
                startIcon={isProcessing ? <CircularProgress size={20} /> : <PersonAdd />}
              >
                {isProcessing ? "Enrolling..." : "Complete Enrollment"}
              </Button>
            </Grid>
          </Grid>
        </form>
      </Paper>
    </Box>
  );
};

export default EnrollPage;
