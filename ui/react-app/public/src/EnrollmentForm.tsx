import React, { useState } from 'react';
import axios from 'axios';
import { TextField, Button, Checkbox, FormControlLabel, Typography, Grid, Card, CardContent, Box, Alert, CircularProgress, IconButton } from '@mui/material';
import { PersonAdd, CloudUpload, CheckCircle, Error } from '@mui/icons-material';

const EnrollmentForm = () => {
    const [name, setName] = useState('');
    const [images, setImages] = useState(null);
    const [consent, setConsent] = useState(false);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [severity, setSeverity] = useState('success');

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!images || !consent) return;

        setLoading(true);
        const formData = new FormData();
        for (let i = 0; i < images.length; i++) {
            formData.append('images', images[i]);
        }
        formData.append('name', name);
        formData.append('metadata', JSON.stringify({}));
        formData.append('consent', consent.toString());

        try {
            const response = await axios.post('/api/enroll', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setMessage(`Enrolled successfully: ${response.data.person_id}`);
            setSeverity('success');
        } catch (error) {
            const errorMessage = error.response?.data?.detail || 'Enrollment failed';
            setMessage(errorMessage);
            setSeverity('error');
        }
        setLoading(false);
    };

    return (
        <Box sx={{ maxWidth: 800, mx: 'auto' }}>
            <Typography variant="h5" gutterBottom sx={{ mb: 4, textAlign: 'center', fontWeight: 600 }}>
                <PersonAdd sx={{ mr: 1, verticalAlign: 'middle' }} />
                Enroll New Person
            </Typography>

            <Grid container spacing={4}>
                <Grid item xs={12}>
                    <Card sx={{ p: 3 }}>
                        <CardContent>
                            <form onSubmit={handleSubmit}>
                                <Grid container spacing={3}>
                                    <Grid item xs={12}>
                                        <TextField
                                            fullWidth
                                            label="Full Name"
                                            variant="outlined"
                                            value={name}
                                            onChange={(e) => setName(e.target.value)}
                                            required
                                            sx={{ mb: 2 }}
                                        />
                                    </Grid>

                                    <Grid item xs={12}>
                                        <Box sx={{
                                            border: '2px dashed rgba(0, 188, 212, 0.5)',
                                            borderRadius: '16px',
                                            p: 4,
                                            textAlign: 'center',
                                            background: 'linear-gradient(145deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0.01))',
                                            transition: 'all 0.3s ease',
                                            '&:hover': {
                                                borderColor: '#00bcd4',
                                                background: 'linear-gradient(145deg, rgba(0, 188, 212, 0.05), rgba(0, 188, 212, 0.02))',
                                            }
                                        }}>
                                            <input
                                                accept="image/*"
                                                style={{ display: 'none' }}
                                                id="image-upload"
                                                multiple
                                                type="file"
                                                onChange={(e) => setImages(e.target.files)}
                                            />
                                            <label htmlFor="image-upload">
                                                <IconButton component="span" sx={{ fontSize: '3rem', color: '#00bcd4' }}>
                                                    <CloudUpload />
                                                </IconButton>
                                            </label>
                                            <Typography variant="h6" sx={{ mt: 2, color: 'text.secondary' }}>
                                                Upload Face Images
                                            </Typography>
                                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                Select multiple high-quality images for better recognition
                                            </Typography>
                                            {images && (
                                                <Typography variant="body2" sx={{ mt: 1, color: '#00bcd4' }}>
                                                    {images.length} file(s) selected
                                                </Typography>
                                            )}
                                        </Box>
                                    </Grid>

                                    <Grid item xs={12}>
                                        <FormControlLabel
                                            control={
                                                <Checkbox
                                                    checked={consent}
                                                    onChange={(e) => setConsent(e.target.checked)}
                                                    color="primary"
                                                    sx={{
                                                        '& .MuiSvgIcon-root': {
                                                            fontSize: '1.5rem',
                                                        }
                                                    }}
                                                />
                                            }
                                            label={
                                                <Typography variant="body1">
                                                    I consent to face recognition enrollment and understand my data will be processed securely
                                                </Typography>
                                            }
                                            sx={{ alignItems: 'flex-start' }}
                                        />
                                    </Grid>

                                    <Grid item xs={12}>
                                        <Button
                                            type="submit"
                                            variant="contained"
                                            fullWidth
                                            disabled={loading || !consent || !name || !images}
                                            sx={{
                                                py: 2,
                                                fontSize: '1.1rem',
                                                fontWeight: 600,
                                                borderRadius: '16px',
                                                background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                                boxShadow: '0 8px 32px rgba(0, 188, 212, 0.4)',
                                                '&:hover': {
                                                    background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                                                    boxShadow: '0 12px 40px rgba(0, 188, 212, 0.6)',
                                                    transform: 'translateY(-2px)',
                                                },
                                                '&:disabled': {
                                                    background: 'rgba(255, 255, 255, 0.1)',
                                                    color: 'rgba(255, 255, 255, 0.3)',
                                                }
                                            }}
                                            startIcon={loading ? <CircularProgress size={20} /> : <CheckCircle />}
                                        >
                                            {loading ? 'Enrolling...' : 'Enroll Person'}
                                        </Button>
                                    </Grid>
                                </Grid>
                            </form>
                        </CardContent>
                    </Card>
                </Grid>

                {message && (
                    <Grid item xs={12}>
                        <Alert
                            severity={severity}
                            sx={{
                                borderRadius: '16px',
                                fontSize: '1rem',
                                '& .MuiAlert-icon': {
                                    fontSize: '1.5rem',
                                }
                            }}
                            icon={severity === 'success' ? <CheckCircle /> : <Error />}
                        >
                            {message}
                        </Alert>
                    </Grid>
                )}
            </Grid>
        </Box>
    );
};

export default EnrollmentForm;
