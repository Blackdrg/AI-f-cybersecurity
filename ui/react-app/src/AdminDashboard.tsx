import React, { useState } from 'react';
import axios from 'axios';
import { TextField, Button, Typography, Grid, Card, CardContent, Box, Alert, CircularProgress, Chip, Avatar, Divider, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Select, MenuItem, FormControl, InputLabel, List, ListItem, ListItemText, Switch, FormControlLabel } from '@mui/material';
import { LineChart, LineElement, ChartsXAxis, ChartsYAxis, ChartsGrid, ChartsTooltip, ChartsLegend } from '@mui/x-charts';
import { Dashboard, Person, Search, Delete, Analytics, TrendingUp, AccessTime, People, History, PlayArrow, VerifiedUser, Build, Storage, Assessment, Lock } from '@mui/icons-material';

const AdminDashboard = () => {
    const [personId, setPersonId] = useState('');
    const [person, setPerson] = useState(null);
    const [metrics, setMetrics] = useState(null);
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [severity, setSeverity] = useState('success');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [actionFilter, setActionFilter] = useState('');
    const [consentVault, setConsentVault] = useState([]);
    const [biasReport, setBiasReport] = useState(null);
    const [indexRebuildMessage, setIndexRebuildMessage] = useState('');
    const [webhooks, setWebhooks] = useState([]);
    const [plugins, setPlugins] = useState([]);
    const [analytics, setAnalytics] = useState(null);

    const fetchPerson = async () => {
        if (!personId) return;
        setLoading(true);
        setMessage('');
        try {
            const response = await axios.get(`/api/admin/persons/${personId}`);
            setPerson(response.data);
            setMessage('Person fetched successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Failed to fetch person');
            setMessage('Failed to fetch person. Please check the ID.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const deletePerson = async () => {
        if (!personId) return;
        setLoading(true);
        setMessage('');
        try {
            await axios.delete(`/api/admin/persons/${personId}`);
            setPerson(null);
            setMessage('Person deleted successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Failed to delete person');
            setMessage('Failed to delete person. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const fetchMetrics = async () => {
        setLoading(true);
        setMessage('');
        try {
            const response = await axios.get('/api/admin/metrics');
            setMetrics(response.data);
            setMessage('Metrics fetched successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Failed to fetch metrics');
            setMessage('Failed to fetch metrics. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const fetchLogs = async () => {
        setLoading(true);
        setMessage('');
        try {
            const params = {};
            if (startDate) params.start_date = startDate;
            if (endDate) params.end_date = endDate;
            if (actionFilter) params.action = actionFilter;
            const response = await axios.get('/api/admin/logs', { params });
            setLogs(response.data.logs);
            setMessage('Logs fetched successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Failed to fetch logs');
            setMessage('Failed to fetch logs. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const handlePlayback = (log) => {
        // Placeholder for event playback
        alert(`Playback for log: ${log.action} at ${log.timestamp}`);
    };

    const fetchConsentVault = async () => {
        setLoading(true);
        setMessage('');
        try {
            const response = await axios.get('/api/consent_vault');
            setConsentVault(response.data.consents);
            setMessage('Consent vault fetched successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Failed to fetch consent vault');
            setMessage('Failed to fetch consent vault. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const fetchBiasReport = async () => {
        setLoading(true);
        setMessage('');
        try {
            const response = await axios.get('/api/bias_report');
            setBiasReport(response.data);
            setMessage('Bias report fetched successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Failed to fetch bias report');
            setMessage('Failed to fetch bias report. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const rebuildIndex = async () => {
        setLoading(true);
        setMessage('');
        try {
            await axios.post('/api/index/rebuild');
            setIndexRebuildMessage('Index rebuilt successfully');
            setMessage('Index rebuilt successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Failed to rebuild index');
            setMessage('Failed to rebuild index. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const fetchWebhooks = async () => {
        setLoading(true);
        setMessage('');
        try {
            const response = await axios.get('/api/webhooks');
            setWebhooks(response.data);
            setMessage('Webhooks fetched successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Failed to fetch webhooks');
            setMessage('Failed to fetch webhooks. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const fetchPlugins = async () => {
        setLoading(true);
        setMessage('');
        try {
            const response = await axios.get('/api/plugins');
            setPlugins(response.data);
            setMessage('Plugins fetched successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Failed to fetch plugins');
            setMessage('Failed to fetch plugins. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const fetchAnalytics = async () => {
        setLoading(true);
        setMessage('');
        try {
            const response = await axios.get('/api/analytics');
            setAnalytics(response.data);
            setMessage('Analytics fetched successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Failed to fetch analytics');
            setMessage('Failed to fetch analytics. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    return (
        <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
            <Typography variant="h5" gutterBottom sx={{ mb: 4, textAlign: 'center', fontWeight: 600 }}>
                <Dashboard sx={{ mr: 1, verticalAlign: 'middle' }} />
                Admin Dashboard
            </Typography>

            <Grid container spacing={4}>
                {/* Person Management Section */}
                <Grid item xs={12} lg={6}>
                    <Card sx={{ p: 4, height: '100%' }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                                <Person sx={{ mr: 1, verticalAlign: 'middle' }} />
                                Person Management
                            </Typography>

                            <Grid container spacing={2}>
                                <Grid item xs={12}>
                                    <TextField
                                        fullWidth
                                        label="Person ID"
                                        variant="outlined"
                                        value={personId}
                                        onChange={(e) => setPersonId(e.target.value)}
                                        sx={{ mb: 2 }}
                                    />
                                </Grid>

                                <Grid item xs={6}>
                                    <Button
                                        fullWidth
                                        variant="contained"
                                        onClick={fetchPerson}
                                        disabled={loading || !personId}
                                        sx={{
                                            py: 1.5,
                                            fontWeight: 600,
                                            borderRadius: '12px',
                                            background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                            '&:hover': {
                                                background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                                                transform: 'translateY(-2px)',
                                            },
                                            '&:disabled': {
                                                background: 'rgba(255, 255, 255, 0.1)',
                                                color: 'rgba(255, 255, 255, 0.3)',
                                            }
                                        }}
                                        startIcon={<Search />}
                                    >
                                        Get Person
                                    </Button>
                                </Grid>

                                <Grid item xs={6}>
                                    <Button
                                        fullWidth
                                        variant="outlined"
                                        color="error"
                                        onClick={deletePerson}
                                        disabled={loading || !personId}
                                        sx={{
                                            py: 1.5,
                                            fontWeight: 600,
                                            borderRadius: '12px',
                                            borderColor: '#ff4081',
                                            color: '#ff4081',
                                            '&:hover': {
                                                borderColor: '#ff4081',
                                                background: 'rgba(255, 64, 129, 0.1)',
                                                transform: 'translateY(-2px)',
                                            },
                                            '&:disabled': {
                                                borderColor: 'rgba(255, 255, 255, 0.1)',
                                                color: 'rgba(255, 255, 255, 0.3)',
                                            }
                                        }}
                                        startIcon={<Delete />}
                                    >
                                        Delete Person
                                    </Button>
                                </Grid>
                            </Grid>

                            {person && (
                                <Box sx={{ mt: 3 }}>
                                    <Divider sx={{ mb: 2 }} />
                                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                                        Person Details
                                    </Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                        <Avatar sx={{ mr: 2, bgcolor: '#00bcd4' }}>
                                            <Person />
                                        </Avatar>
                                        <Box>
                                            <Typography variant="body1" sx={{ fontWeight: 600 }}>
                                                {person.name}
                                            </Typography>
                                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                ID: {person.person_id}
                                            </Typography>
                                        </Box>
                                    </Box>
                                    <Chip
                                        label={`${person.embeddings.length} Embeddings`}
                                        color="primary"
                                        sx={{
                                            fontSize: '0.9rem',
                                            fontWeight: 600,
                                            px: 2,
                                            py: 1,
                                            borderRadius: '12px',
                                        }}
                                    />
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Metrics Section */}
                <Grid item xs={12} lg={6}>
                    <Card sx={{ p: 4, height: '100%' }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                                <Analytics sx={{ mr: 1, verticalAlign: 'middle' }} />
                                System Metrics
                            </Typography>

                            <Button
                                fullWidth
                                variant="contained"
                                onClick={fetchMetrics}
                                disabled={loading}
                                sx={{
                                    py: 1.5,
                                    mb: 3,
                                    fontWeight: 600,
                                    borderRadius: '12px',
                                    background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                    '&:hover': {
                                        background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                                        transform: 'translateY(-2px)',
                                    },
                                    '&:disabled': {
                                        background: 'rgba(255, 255, 255, 0.1)',
                                        color: 'rgba(255, 255, 255, 0.3)',
                                    }
                                }}
                                startIcon={loading ? <CircularProgress size={20} /> : <TrendingUp />}
                            >
                                Fetch Metrics
                            </Button>

                            {metrics && (
                                <Box>
                                    <Divider sx={{ mb: 2 }} />
                                    <Grid container spacing={2}>
                                        <Grid item xs={12} sm={6}>
                                            <Card sx={{
                                                p: 2,
                                                background: 'linear-gradient(145deg, rgba(0, 188, 212, 0.1), rgba(255, 64, 129, 0.05))',
                                                border: '1px solid rgba(0, 188, 212, 0.3)',
                                                borderRadius: '12px',
                                                textAlign: 'center',
                                            }}>
                                                <People sx={{ fontSize: '2rem', color: '#00bcd4', mb: 1 }} />
                                                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                                    {metrics.recognition_count}
                                                </Typography>
                                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                    Recognitions
                                                </Typography>
                                            </Card>
                                        </Grid>

                                        <Grid item xs={12} sm={6}>
                                            <Card sx={{
                                                p: 2,
                                                background: 'linear-gradient(145deg, rgba(0, 188, 212, 0.1), rgba(255, 64, 129, 0.05))',
                                                border: '1px solid rgba(0, 188, 212, 0.3)',
                                                borderRadius: '12px',
                                                textAlign: 'center',
                                            }}>
                                                <Person sx={{ fontSize: '2rem', color: '#ff4081', mb: 1 }} />
                                                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                                    {metrics.enroll_count}
                                                </Typography>
                                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                    Enrollments
                                                </Typography>
                                            </Card>
                                        </Grid>

                                        <Grid item xs={12}>
                                            <Card sx={{
                                                p: 2,
                                                background: 'linear-gradient(145deg, rgba(0, 188, 212, 0.1), rgba(255, 64, 129, 0.05))',
                                                border: '1px solid rgba(0, 188, 212, 0.3)',
                                                borderRadius: '12px',
                                                textAlign: 'center',
                                            }}>
                                                <AccessTime sx={{ fontSize: '2rem', color: '#00bcd4', mb: 1 }} />
                                                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                                    {metrics.avg_latency_ms} ms
                                                </Typography>
                                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                    Average Latency
                                                </Typography>
                                            </Card>
                                        </Grid>
                                    </Grid>
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Consent and Privacy Management Section */}
                <Grid item xs={12} lg={6}>
                    <Card sx={{ p: 4, height: '100%' }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                                <VerifiedUser sx={{ mr: 1, verticalAlign: 'middle' }} />
                                Consent & Privacy Management
                            </Typography>

                            <Button
                                fullWidth
                                variant="contained"
                                onClick={fetchConsentVault}
                                disabled={loading}
                                sx={{
                                    py: 1.5,
                                    mb: 3,
                                    fontWeight: 600,
                                    borderRadius: '12px',
                                    background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                    '&:hover': {
                                        background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                                        transform: 'translateY(-2px)',
                                    },
                                    '&:disabled': {
                                        background: 'rgba(255, 255, 255, 0.1)',
                                        color: 'rgba(255, 255, 255, 0.3)',
                                    }
                                }}
                                startIcon={loading ? <CircularProgress size={20} /> : <Lock />}
                            >
                                Fetch Consent Vault
                            </Button>

                            {consentVault.length > 0 && (
                                <Box>
                                    <Divider sx={{ mb: 2 }} />
                                    <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                                        User Consents
                                    </Typography>
                                    <List dense>
                                        {consentVault.map((consent, index) => (
                                            <ListItem key={index}>
                                                <ListItemText
                                                    primary={`${consent.biometric_type}: ${consent.granted ? 'Granted' : 'Revoked'}`}
                                                    secondary={`User ID: ${consent.user_id}`}
                                                />
                                                <FormControlLabel
                                                    control={<Switch checked={consent.granted} disabled />}
                                                    label=""
                                                />
                                            </ListItem>
                                        ))}
                                    </List>
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Model Performance Monitoring Section */}
                <Grid item xs={12} lg={6}>
                    <Card sx={{ p: 4, height: '100%' }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                                <Assessment sx={{ mr: 1, verticalAlign: 'middle' }} />
                                Model Performance Monitoring
                            </Typography>

                            <Button
                                fullWidth
                                variant="contained"
                                onClick={fetchBiasReport}
                                disabled={loading}
                                sx={{
                                    py: 1.5,
                                    mb: 3,
                                    fontWeight: 600,
                                    borderRadius: '12px',
                                    background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                    '&:hover': {
                                        background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                                        transform: 'translateY(-2px)',
                                    },
                                    '&:disabled': {
                                        background: 'rgba(255, 255, 255, 0.1)',
                                        color: 'rgba(255, 255, 255, 0.3)',
                                    }
                                }}
                                startIcon={loading ? <CircularProgress size={20} /> : <Assessment />}
                            >
                                Fetch Bias Report
                            </Button>

                            {biasReport && (
                                <Box>
                                    <Divider sx={{ mb: 2 }} />
                                    <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                                        Bias Metrics
                                    </Typography>
                                    <Grid container spacing={2}>
                                        <Grid item xs={12}>
                                            <Card sx={{
                                                p: 2,
                                                background: 'linear-gradient(145deg, rgba(0, 188, 212, 0.1), rgba(255, 64, 129, 0.05))',
                                                border: '1px solid rgba(0, 188, 212, 0.3)',
                                                borderRadius: '12px',
                                                textAlign: 'center',
                                            }}>
                                                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                                    {biasReport.demographic_parity_difference}
                                                </Typography>
                                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                    Demographic Parity Difference
                                                </Typography>
                                            </Card>
                                        </Grid>
                                        <Grid item xs={12}>
                                            <Card sx={{
                                                p: 2,
                                                background: 'linear-gradient(145deg, rgba(0, 188, 212, 0.1), rgba(255, 64, 129, 0.05))',
                                                border: '1px solid rgba(0, 188, 212, 0.3)',
                                                borderRadius: '12px',
                                                textAlign: 'center',
                                            }}>
                                                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                                                    {biasReport.equalized_odds_difference}
                                                </Typography>
                                                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                    Equalized Odds Difference
                                                </Typography>
                                            </Card>
                                        </Grid>
                                    </Grid>
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Vector DB and Index Management Section */}
                <Grid item xs={12} lg={6}>
                    <Card sx={{ p: 4, height: '100%' }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                                <Storage sx={{ mr: 1, verticalAlign: 'middle' }} />
                                Vector DB & Index Management
                            </Typography>

                            <Button
                                fullWidth
                                variant="contained"
                                onClick={rebuildIndex}
                                disabled={loading}
                                sx={{
                                    py: 1.5,
                                    mb: 3,
                                    fontWeight: 600,
                                    borderRadius: '12px',
                                    background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                    '&:hover': {
                                        background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                                        transform: 'translateY(-2px)',
                                    },
                                    '&:disabled': {
                                        background: 'rgba(255, 255, 255, 0.1)',
                                        color: 'rgba(255, 255, 255, 0.3)',
                                    }
                                }}
                                startIcon={loading ? <CircularProgress size={20} /> : <Build />}
                            >
                                Rebuild Index
                            </Button>

                            {indexRebuildMessage && (
                                <Box>
                                    <Divider sx={{ mb: 2 }} />
                                    <Alert severity="success" sx={{ borderRadius: '12px' }}>
                                        {indexRebuildMessage}
                                    </Alert>
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Webhooks and Plugins Management Section */}
                <Grid item xs={12} lg={6}>
                    <Card sx={{ p: 4, mt: 4 }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                                <Build sx={{ mr: 1, verticalAlign: 'middle' }} />
                                Webhooks & Plugins Management
                            </Typography>

                            <Grid container spacing={2} sx={{ mb: 3 }}>
                                <Grid item xs={12} sm={6}>
                                    <Button
                                        fullWidth
                                        variant="contained"
                                        onClick={fetchWebhooks}
                                        disabled={loading}
                                        sx={{
                                            py: 1.5,
                                            fontWeight: 600,
                                            borderRadius: '12px',
                                            background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                            '&:hover': {
                                                background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                                                transform: 'translateY(-2px)',
                                            },
                                            '&:disabled': {
                                                background: 'rgba(255, 255, 255, 0.1)',
                                                color: 'rgba(255, 255, 255, 0.3)',
                                            }
                                        }}
                                        startIcon={loading ? <CircularProgress size={20} /> : <Build />}
                                    >
                                        Fetch Webhooks
                                    </Button>
                                </Grid>
                                <Grid item xs={12} sm={6}>
                                    <Button
                                        fullWidth
                                        variant="contained"
                                        onClick={fetchPlugins}
                                        disabled={loading}
                                        sx={{
                                            py: 1.5,
                                            fontWeight: 600,
                                            borderRadius: '12px',
                                            background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                            '&:hover': {
                                                background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                                                transform: 'translateY(-2px)',
                                            },
                                            '&:disabled': {
                                                background: 'rgba(255, 255, 255, 0.1)',
                                                color: 'rgba(255, 255, 255, 0.3)',
                                            }
                                        }}
                                        startIcon={loading ? <CircularProgress size={20} /> : <Build />}
                                    >
                                        Fetch Plugins
                                    </Button>
                                </Grid>
                            </Grid>

                            {webhooks.length > 0 && (
                                <Box sx={{ mb: 3 }}>
                                    <Divider sx={{ mb: 2 }} />
                                    <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                                        Webhooks
                                    </Typography>
                                    <List dense>
                                        {webhooks.map((webhook, index) => (
                                            <ListItem key={index}>
                                                <ListItemText
                                                    primary={webhook.url}
                                                    secondary={`Event: ${webhook.event}, Active: ${webhook.active}`}
                                                />
                                            </ListItem>
                                        ))}
                                    </List>
                                </Box>
                            )}

                            {plugins.length > 0 && (
                                <Box>
                                    <Divider sx={{ mb: 2 }} />
                                    <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                                        Plugins
                                    </Typography>
                                    <List dense>
                                        {plugins.map((plugin, index) => (
                                            <ListItem key={index}>
                                                <ListItemText
                                                    primary={plugin.name}
                                                    secondary={`Type: ${plugin.type}, Enabled: ${plugin.enabled}`}
                                                />
                                            </ListItem>
                                        ))}
                                    </List>
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Cloud Analytics Section */}
                <Grid item xs={12}>
                    <Card sx={{ p: 4, mt: 4 }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                                <Analytics sx={{ mr: 1, verticalAlign: 'middle' }} />
                                Cloud Analytics
                            </Typography>

                            <Button
                                fullWidth
                                variant="contained"
                                onClick={fetchAnalytics}
                                disabled={loading}
                                sx={{
                                    py: 1.5,
                                    mb: 3,
                                    fontWeight: 600,
                                    borderRadius: '12px',
                                    background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                    '&:hover': {
                                        background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                                        transform: 'translateY(-2px)',
                                    },
                                    '&:disabled': {
                                        background: 'rgba(255, 255, 255, 0.1)',
                                        color: 'rgba(255, 255, 255, 0.3)',
                                    }
                                }}
                                startIcon={loading ? <CircularProgress size={20} /> : <Analytics />}
                            >
                                Fetch Analytics
                            </Button>

                            {analytics && (
                                <Box>
                                    <Divider sx={{ mb: 2 }} />
                                    <Grid container spacing={2}>
                                        <Grid item xs={12} md={6}>
                                            <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                                                Time-Series Metrics (Last 30 Days)
                                            </Typography>
                                            <LineChart
                                                width={500}
                                                height={300}
                                                data={analytics.time_series}
                                                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                                            >
                                                <ChartsGrid />
                                                <ChartsXAxis />
                                                <ChartsYAxis />
                                                <ChartsTooltip />
                                                <ChartsLegend />
                                                <LineElement type="monotone" dataKey="recognitions" stroke="#8884d8" />
                                                <LineElement type="monotone" dataKey="enrollments" stroke="#82ca9d" />
                                            </LineChart>
                                        </Grid>
                                        <Grid item xs={12} md={6}>
                                            <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                                                Bias Trends
                                            </Typography>
                                            <LineChart
                                                width={500}
                                                height={300}
                                                data={analytics.bias_trends}
                                                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                                            >
                                                <ChartsGrid />
                                                <ChartsXAxis />
                                                <ChartsYAxis />
                                                <ChartsTooltip />
                                                <ChartsLegend />
                                                <LineElement type="monotone" dataKey="dpd" stroke="#ff7300" />
                                            </LineChart>
                                        </Grid>
                                        <Grid item xs={12}>
                                            <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                                                Edge Device Stats
                                            </Typography>
                                            <TableContainer component={Paper}>
                                                <Table>
                                                    <TableHead>
                                                        <TableRow>
                                                            <TableCell>Device ID</TableCell>
                                                            <TableCell>Status</TableCell>
                                                            <TableCell>Last Seen</TableCell>
                                                        </TableRow>
                                                    </TableHead>
                                                    <TableBody>
                                                        {analytics.device_stats.map((device, index) => (
                                                            <TableRow key={index}>
                                                                <TableCell>{device.device_id}</TableCell>
                                                                <TableCell>{device.status}</TableCell>
                                                                <TableCell>{new Date(device.last_seen).toLocaleString()}</TableCell>
                                                            </TableRow>
                                                        ))}
                                                    </TableBody>
                                                </Table>
                                            </TableContainer>
                                        </Grid>
                                    </Grid>
                                </Box>
                            )}
                        </CardContent>
                    </Card>
                </Grid>

                {/* Historical Logs Section */}
                <Grid item xs={12}>
                    <Card sx={{ p: 4, mt: 4 }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                                <History sx={{ mr: 1, verticalAlign: 'middle' }} />
                                Historical Logs
                            </Typography>

                            <Grid container spacing={2} sx={{ mb: 3 }}>
                                <Grid item xs={12} sm={3}>
                                    <TextField
                                        fullWidth
                                        label="Start Date"
                                        type="date"
                                        InputLabelProps={{ shrink: true }}
                                        value={startDate}
                                        onChange={(e) => setStartDate(e.target.value)}
                                    />
                                </Grid>
                                <Grid item xs={12} sm={3}>
                                    <TextField
                                        fullWidth
                                        label="End Date"
                                        type="date"
                                        InputLabelProps={{ shrink: true }}
                                        value={endDate}
                                        onChange={(e) => setEndDate(e.target.value)}
                                    />
                                </Grid>
                                <Grid item xs={12} sm={3}>
                                    <FormControl fullWidth>
                                        <InputLabel>Action</InputLabel>
                                        <Select
                                            value={actionFilter}
                                            onChange={(e) => setActionFilter(e.target.value)}
                                            label="Action"
                                        >
                                            <MenuItem value="">All</MenuItem>
                                            <MenuItem value="recognize">Recognize</MenuItem>
                                            <MenuItem value="enroll">Enroll</MenuItem>
                                            <MenuItem value="delete">Delete</MenuItem>
                                        </Select>
                                    </FormControl>
                                </Grid>
                                <Grid item xs={12} sm={3}>
                                    <Button
                                        fullWidth
                                        variant="contained"
                                        onClick={fetchLogs}
                                        disabled={loading}
                                        sx={{
                                            py: 1.5,
                                            fontWeight: 600,
                                            borderRadius: '12px',
                                            background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                            '&:hover': {
                                                background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                                                transform: 'translateY(-2px)',
                                            },
                                            '&:disabled': {
                                                background: 'rgba(255, 255, 255, 0.1)',
                                                color: 'rgba(255, 255, 255, 0.3)',
                                            }
                                        }}
                                        startIcon={loading ? <CircularProgress size={20} /> : <History />}
                                    >
                                        Fetch Logs
                                    </Button>
                                </Grid>
                            </Grid>

                            {logs.length > 0 && (
                                <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
                                    <Table stickyHeader>
                                        <TableHead>
                                            <TableRow>
                                                <TableCell sx={{ fontWeight: 600 }}>Timestamp</TableCell>
                                                <TableCell sx={{ fontWeight: 600 }}>Action</TableCell>
                                                <TableCell sx={{ fontWeight: 600 }}>Person ID</TableCell>
                                                <TableCell sx={{ fontWeight: 600 }}>Details</TableCell>
                                                <TableCell sx={{ fontWeight: 600 }}>Playback</TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            {logs.map((log, index) => (
                                                <TableRow key={index}>
                                                    <TableCell>{new Date(log.timestamp).toLocaleString()}</TableCell>
                                                    <TableCell>{log.action}</TableCell>
                                                    <TableCell>{log.person_id || 'N/A'}</TableCell>
                                                    <TableCell>{JSON.stringify(log.details)}</TableCell>
                                                    <TableCell>
                                                        <Button
                                                            variant="outlined"
                                                            size="small"
                                                            onClick={() => handlePlayback(log)}
                                                            startIcon={<PlayArrow />}
                                                        >
                                                            Play
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </TableContainer>
                            )}
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
                        >
                            {message}
                        </Alert>
                    </Grid>
                )}
            </Grid>
        </Box>
    );
};

export default AdminDashboard;
