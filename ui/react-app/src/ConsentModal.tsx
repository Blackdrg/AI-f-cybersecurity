import React, { useState } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Typography,
    Box,
    Checkbox,
    FormControlLabel,
    Alert,
    CircularProgress,
    Chip,
    Divider,
    List,
    ListItem,
    ListItemIcon,
    ListItemText
} from '@mui/material';
import {
    PrivacyTip,
    Search,
    Storage,
    Delete,
    Security,
    Info,
    CheckCircle
} from '@mui/icons-material';
import axios from 'axios';

interface ConsentModalProps {
    open: boolean;
    onClose: () => void;
    personId?: string;
    identifiers: { [key: string]: string };
    onConsentGranted: (token: string) => void;
}

const ConsentModal: React.FC<ConsentModalProps> = ({
    open,
    onClose,
    personId,
    identifiers,
    onConsentGranted
}) => {
    const [accepted, setAccepted] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleGrantConsent = async () => {
        if (!accepted) return;

        setLoading(true);
        setError('');

        try {
            const response = await axios.post('/api/public_enrich/consent', {
                subject_id: personId,
                purpose: 'Public profile enrichment for identity verification',
                consent_text_version: 'v1'
            });

            onConsentGranted(response.data.token);
            onClose();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to grant consent');
        } finally {
            setLoading(false);
        }
    };

    const providers = [
        { name: 'Bing Search', description: 'Web search results from Bing' },
        { name: 'Wikipedia', description: 'Information from Wikipedia articles' }
    ];

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="md"
            fullWidth
            PaperProps={{
                sx: {
                    borderRadius: '16px',
                    p: 2
                }
            }}
        >
            <DialogTitle sx={{
                textAlign: 'center',
                fontSize: '1.5rem',
                fontWeight: 600,
                color: 'primary.main'
            }}>
                <PrivacyTip sx={{ mr: 1, verticalAlign: 'middle' }} />
                Consent for Public Profile Enrichment
            </DialogTitle>

            <DialogContent>
                <Box sx={{ mb: 3 }}>
                    <Typography variant="h6" gutterBottom>
                        What is Public Profile Enrichment?
                    </Typography>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                        Public profile enrichment helps verify identities by searching publicly available information
                        from trusted sources. This can provide additional context about individuals for security and
                        verification purposes.
                    </Typography>

                    <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                        Search Query
                    </Typography>
                    <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: '8px', mb: 2 }}>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                            {Object.entries(identifiers).map(([key, value]) => `${key}: ${value}`).join(', ')}
                        </Typography>
                    </Box>

                    <Typography variant="h6" gutterBottom>
                        Data Sources
                    </Typography>
                    <List dense>
                        {providers.map((provider, idx) => (
                            <ListItem key={idx}>
                                <ListItemIcon>
                                    <Search color="primary" />
                                </ListItemIcon>
                                <ListItemText
                                    primary={provider.name}
                                    secondary={provider.description}
                                />
                            </ListItem>
                        ))}
                    </List>

                    <Divider sx={{ my: 3 }} />

                    <Typography variant="h6" gutterBottom>
                        Privacy & Security Measures
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Security sx={{ mr: 1, color: 'success.main' }} />
                            <Typography variant="body2">
                                All results are automatically redacted to remove sensitive information (SSN, addresses, emails, etc.)
                            </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Storage sx={{ mr: 1, color: 'info.main' }} />
                            <Typography variant="body2">
                                Enrichment results are stored securely for 7 days and then automatically deleted
                            </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Delete sx={{ mr: 1, color: 'warning.main' }} />
                            <Typography variant="body2">
                                You can revoke this consent at any time, which will immediately delete all associated data
                            </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Info sx={{ mr: 1, color: 'primary.main' }} />
                            <Typography variant="body2">
                                All enrichment activities are logged for audit purposes and compliance
                            </Typography>
                        </Box>
                    </Box>

                    <Alert severity="info" sx={{ mt: 3, borderRadius: '8px' }}>
                        <Typography variant="body2">
                            <strong>Important:</strong> This consent is specific to this search query and expires after 24 hours.
                            You will need to provide consent again for future enrichments.
                        </Typography>
                    </Alert>

                    {error && (
                        <Alert severity="error" sx={{ mt: 2, borderRadius: '8px' }}>
                            {error}
                        </Alert>
                    )}
                </Box>

                <FormControlLabel
                    control={
                        <Checkbox
                            checked={accepted}
                            onChange={(e) => setAccepted(e.target.checked)}
                            color="primary"
                        />
                    }
                    label={
                        <Typography variant="body2">
                            I understand and consent to the public profile enrichment using the information above.
                            I acknowledge that results may contain sensitive information that will be redacted.
                        </Typography>
                    }
                    sx={{ alignItems: 'flex-start', mt: 2 }}
                />
            </DialogContent>

            <DialogActions sx={{ p: 3, pt: 0 }}>
                <Button
                    onClick={onClose}
                    variant="outlined"
                    sx={{ borderRadius: '8px', px: 3 }}
                >
                    Cancel
                </Button>
                <Button
                    onClick={handleGrantConsent}
                    variant="contained"
                    disabled={!accepted || loading}
                    sx={{
                        borderRadius: '8px',
                        px: 3,
                        background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                        '&:hover': {
                            background: 'linear-gradient(45deg, #00bcd4 50%, #ff4081 100%)',
                        }
                    }}
                    startIcon={loading ? <CircularProgress size={16} /> : <CheckCircle />}
                >
                    {loading ? 'Granting Consent...' : 'Grant Consent'}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default ConsentModal;
