import React, { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Card,
    CardContent,
    Grid,
    Chip,
    Button,
    Alert,
    CircularProgress,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    List,
    ListItem,
    ListItemText,
    Divider,
    IconButton,
    Tooltip
} from '@mui/material';
import {
    ExpandMore,
    Launch,
    Flag,
    Search,
    Public,
    Verified,
    ReportProblem
} from '@mui/icons-material';
import axios from 'axios';

interface EnrichResult {
    provider: string;
    title: string;
    snippet: string;
    url: string;
    confidence: number;
}

interface EnrichResultsPageProps {
    enrichId: string;
    onBack: () => void;
}

const EnrichResultsPage: React.FC<EnrichResultsPageProps> = ({ enrichId, onBack }) => {
    const [results, setResults] = useState<EnrichResult[] | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [flagging, setFlagging] = useState(false);

    useEffect(() => {
        fetchResults();
    }, [enrichId]);

    const fetchResults = async () => {
        try {
            const response = await axios.get(`/api/public_enrich/${enrichId}`);
            setResults(response.data.summary);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load results');
        } finally {
            setLoading(false);
        }
    };

    const handleFlagForReview = async () => {
        setFlagging(true);
        try {
            await axios.post(`/api/public_enrich/flag_for_review`, {
                enrich_id: enrichId,
                reason: 'User flagged for manual review'
            });
            alert('Result flagged for review. Our team will investigate.');
        } catch (err: any) {
            alert('Failed to flag result: ' + (err.response?.data?.detail || 'Unknown error'));
        } finally {
            setFlagging(false);
        }
    };

    const getConfidenceColor = (confidence: number) => {
        if (confidence >= 0.8) return 'success';
        if (confidence >= 0.6) return 'warning';
        return 'error';
    };

    const getConfidenceLabel = (confidence: number) => {
        if (confidence >= 0.8) return 'High';
        if (confidence >= 0.6) return 'Medium';
        return 'Low';
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
                <CircularProgress size={60} />
                <Typography variant="h6" sx={{ ml: 2 }}>Loading enrichment results...</Typography>
            </Box>
        );
    }

    if (error) {
        return (
            <Box sx={{ p: 4 }}>
                <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                </Alert>
                <Button variant="outlined" onClick={onBack}>
                    Back to Recognition
                </Button>
            </Box>
        );
    }

    return (
        <Box sx={{ maxWidth: 1200, mx: 'auto', p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
                <Typography variant="h4" sx={{ fontWeight: 600 }}>
                    <Public sx={{ mr: 1, verticalAlign: 'middle' }} />
                    Public Profile Enrichment Results
                </Typography>
                <Box>
                    <Button
                        variant="outlined"
                        onClick={handleFlagForReview}
                        disabled={flagging}
                        startIcon={flagging ? <CircularProgress size={16} /> : <Flag />}
                        sx={{ mr: 2, borderRadius: '8px' }}
                    >
                        {flagging ? 'Flagging...' : 'Flag for Review'}
                    </Button>
                    <Button
                        variant="contained"
                        onClick={onBack}
                        sx={{
                            borderRadius: '8px',
                            background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                            '&:hover': {
                                background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                            }
                        }}
                    >
                        Back to Recognition
                    </Button>
                </Box>
            </Box>

            <Alert severity="info" sx={{ mb: 3, borderRadius: '8px' }}>
                <Typography variant="body2">
                    <strong>Privacy Notice:</strong> All sensitive information has been automatically redacted from these results.
                    Results are stored securely for 7 days and then permanently deleted.
                </Typography>
            </Alert>

            {results && results.length > 0 ? (
                <Grid container spacing={3}>
                    {results.map((result, idx) => (
                        <Grid item xs={12} key={idx}>
                            <Card sx={{
                                borderRadius: '12px',
                                boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                                '&:hover': {
                                    boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
                                    transform: 'translateY(-2px)',
                                    transition: 'all 0.3s ease'
                                }
                            }}>
                                <CardContent sx={{ p: 3 }}>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                                        <Box sx={{ flex: 1 }}>
                                            <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                                                {result.title}
                                            </Typography>
                                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                                                <Chip
                                                    label={result.provider}
                                                    variant="outlined"
                                                    size="small"
                                                    sx={{ mr: 1 }}
                                                />
                                                <Chip
                                                    label={`${getConfidenceLabel(result.confidence)} Confidence`}
                                                    color={getConfidenceColor(result.confidence)}
                                                    size="small"
                                                    sx={{ mr: 1 }}
                                                />
                                                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                                                    {(result.confidence * 100).toFixed(1)}% confidence
                                                </Typography>
                                            </Box>
                                        </Box>
                                        <Tooltip title="Open in new tab">
                                            <IconButton
                                                href={result.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                sx={{ color: 'primary.main' }}
                                            >
                                                <Launch />
                                            </IconButton>
                                        </Tooltip>
                                    </Box>

                                    <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.6 }}>
                                        {result.snippet}
                                    </Typography>

                                    <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'monospace' }}>
                                        {result.url}
                                    </Typography>
                                </CardContent>
                            </Card>
                        </Grid>
                    ))}
                </Grid>
            ) : (
                <Card sx={{ p: 4, textAlign: 'center', borderRadius: '12px' }}>
                    <CardContent>
                        <ReportProblem sx={{ fontSize: '4rem', color: 'text.secondary', mb: 2 }} />
                        <Typography variant="h6" sx={{ mb: 1 }}>
                            No Results Found
                        </Typography>
                        <Typography variant="body1" sx={{ color: 'text.secondary' }}>
                            No public information was found for the provided identifiers.
                            This could mean the person has a low online presence or the search was too specific.
                        </Typography>
                    </CardContent>
                </Card>
            )}

            <Box sx={{ mt: 4, p: 3, bgcolor: 'grey.50', borderRadius: '12px' }}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                    <Verified sx={{ mr: 1, verticalAlign: 'middle' }} />
                    How Enrichment Works
                </Typography>
                <Typography variant="body2" sx={{ mb: 2 }}>
                    Public profile enrichment searches trusted public sources to gather additional context about individuals.
                    This helps with identity verification and risk assessment.
                </Typography>

                <Accordion sx={{ boxShadow: 'none', '&:before': { display: 'none' } }}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                            Technical Details
                        </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                        <List dense>
                            <ListItem>
                                <ListItemText
                                    primary="Multi-Source Aggregation"
                                    secondary="Results are collected from multiple providers and ranked by relevance"
                                />
                            </ListItem>
                            <Divider />
                            <ListItem>
                                <ListItemText
                                    primary="Automatic Redaction"
                                    secondary="Sensitive information (SSN, addresses, emails, phone numbers) is automatically removed"
                                />
                            </ListItem>
                            <Divider />
                            <ListItem>
                                <ListItemText
                                    primary="Audit Logging"
                                    secondary="All enrichment activities are logged for compliance and security"
                                />
                            </ListItem>
                            <Divider />
                            <ListItem>
                                <ListItemText
                                    primary="Temporary Storage"
                                    secondary="Results are stored for 7 days maximum, then automatically deleted"
                                />
                            </ListItem>
                        </List>
                    </AccordionDetails>
                </Accordion>
            </Box>
        </Box>
    );
};

export default EnrichResultsPage;
