import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Container, AppBar, Toolbar, Typography, Tabs, Tab, Box, Paper, Grid, keyframes } from '@mui/material';
import { Face, Search, AdminPanelSettings, Security, CameraAlt, PersonAdd, Dashboard, SmartToy } from '@mui/icons-material';
import EnrollmentForm from './EnrollmentForm';
import RecognizeViewEnriched from './RecognizeViewEnriched';
import AdminDashboard from './AdminDashboard';
import AIAssistant from './AIAssistant';

// Keyframes for animated background
const gradientShift = keyframes`
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
`;

const particleFloat = keyframes`
    0% { transform: translateY(0px) rotate(0deg); opacity: 0.7; }
    50% { transform: translateY(-20px) rotate(180deg); opacity: 1; }
    100% { transform: translateY(0px) rotate(360deg); opacity: 0.7; }
`;

const theme = createTheme({
    palette: {
        mode: 'dark',
        primary: {
            main: '#00bcd4',
        },
        secondary: {
            main: '#ff4081',
        },
        background: {
            default: '#0a0a0a',
            paper: '#1a1a1a',
        },
        text: {
            primary: '#ffffff',
            secondary: 'rgba(255, 255, 255, 0.7)',
        },
    },
    typography: {
        fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
        h4: {
            fontWeight: 600,
            background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontSize: 'clamp(1.5rem, 4vw, 2.5rem)', // Responsive font size for UHD
        },
        h6: {
            fontWeight: 700,
            fontSize: 'clamp(1rem, 2.5vw, 1.25rem)',
        },
        body1: {
            fontSize: 'clamp(0.875rem, 2vw, 1rem)',
        },
    },
    components: {
        MuiCssBaseline: {
            styleOverrides: {
                '@media (min-resolution: 2dppx)': { // High-DPI support for UHD
                    '*': {
                        imageRendering: 'crisp-edges',
                    },
                },
                '@media (min-width: 7680px)': { // 8K UHD media query
                    body: {
                        fontSize: '1.2em',
                    },
                },
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: {
                    backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.05))',
                    backdropFilter: 'blur(20px)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    boxShadow: '0 16px 64px rgba(0, 188, 212, 0.15), 0 4px 32px rgba(255, 64, 129, 0.1)',
                    transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                },
            },
        },
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: '16px',
                    textTransform: 'none',
                    fontWeight: 600,
                    boxShadow: '0 8px 28px 0 rgba(0, 188, 212, 0.39)',
                    transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&:hover': {
                        boxShadow: '0 12px 40px rgba(0, 188, 212, 0.23)',
                        transform: 'translateY(-4px) scale(1.02)',
                        background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                    },
                    '&:active': {
                        transform: 'translateY(-2px) scale(0.98)',
                    },
                },
            },
        },
        MuiTextField: {
            styleOverrides: {
                root: {
                    '& .MuiOutlinedInput-root': {
                        borderRadius: '16px',
                        background: 'linear-gradient(145deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.04))',
                        backdropFilter: 'blur(20px)',
                        transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                        '& fieldset': {
                            borderColor: 'rgba(0, 188, 212, 0.4)',
                            borderWidth: '2px',
                        },
                        '&:hover fieldset': {
                            borderColor: 'rgba(0, 188, 212, 0.6)',
                            boxShadow: '0 0 30px rgba(0, 188, 212, 0.2)',
                        },
                        '&.Mui-focused fieldset': {
                            borderColor: '#00bcd4',
                            boxShadow: '0 0 40px rgba(0, 188, 212, 0.4)',
                        },
                    },
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    borderRadius: '24px',
                    background: 'linear-gradient(145deg, rgba(26, 26, 26, 0.95), rgba(33, 33, 33, 0.95))',
                    backdropFilter: 'blur(30px)',
                    border: '1px solid rgba(0, 188, 212, 0.3)',
                    boxShadow: '0 16px 64px rgba(0, 188, 212, 0.15), 0 4px 32px rgba(255, 64, 129, 0.1)',
                    transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&:hover': {
                        transform: 'translateY(-8px) scale(1.01)',
                        boxShadow: '0 24px 80px rgba(0, 188, 212, 0.25), 0 8px 40px rgba(255, 64, 129, 0.2)',
                    },
                },
            },
        },
        MuiTab: {
            styleOverrides: {
                root: {
                    borderRadius: '16px 16px 0 0',
                    transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                    fontSize: 'clamp(0.875rem, 2vw, 1.1rem)',
                    minHeight: '72px',
                    '&.Mui-selected': {
                        background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                        color: 'white',
                        boxShadow: '0 8px 32px rgba(0, 188, 212, 0.5)',
                        transform: 'scale(1.02)',
                    },
                    '&:hover': {
                        background: 'rgba(0, 188, 212, 0.15)',
                        transform: 'translateY(-4px) scale(1.01)',
                        boxShadow: '0 4px 16px rgba(0, 188, 212, 0.2)',
                    },
                },
            },
        },
        MuiIcon: {
            styleOverrides: {
                root: {
                    fontSize: 'clamp(1.5rem, 3vw, 2rem)', // Scalable icons for UHD
                },
            },
        },
    },
});

function TabPanel(props) {
    const { children, value, index, ...other } = props;

    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            id={`simple-tabpanel-${index}`}
            aria-labelledby={`simple-tab-${index}`}
            {...other}
        >
            {value === index && (
                <Box sx={{ p: 3 }}>
                    {children}
                </Box>
            )}
        </div>
    );
}

function App() {
    const [value, setValue] = useState(0);

    const handleChange = (event, newValue) => {
        setValue(newValue);
    };

    return (
        <ThemeProvider theme={theme}>
            <CssBaseline />
            <Box sx={{
                flexGrow: 1,
                minHeight: '100vh',
                background: 'linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%)',
                backgroundSize: '400% 400%',
                animation: `${gradientShift} 15s ease infinite`,
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: '10%',
                    left: '10%',
                    width: '20px',
                    height: '20px',
                    background: 'rgba(0, 188, 212, 0.3)',
                    borderRadius: '50%',
                    animation: `${particleFloat} 8s ease-in-out infinite`,
                },
                '&::after': {
                    content: '""',
                    position: 'absolute',
                    top: '60%',
                    right: '15%',
                    width: '15px',
                    height: '15px',
                    background: 'rgba(255, 64, 129, 0.3)',
                    borderRadius: '50%',
                    animation: `${particleFloat} 10s ease-in-out infinite reverse`,
                },
            }}>
                <AppBar position="static" elevation={0} sx={{
                    background: 'rgba(26, 26, 26, 0.95)',
                    backdropFilter: 'blur(20px)',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                    boxShadow: '0 4px 20px rgba(0, 188, 212, 0.1)',
                }}>
                    <Toolbar>
                        <Security sx={{ mr: 2, color: '#00bcd4', fontSize: '2rem' }} />
                        <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 700 }}>
                            AI Face Recognition System
                        </Typography>
                        <Typography variant="body2" sx={{ opacity: 0.7 }}>
                            Privacy-First • Consent-Driven • Enterprise-Grade
                        </Typography>
                    </Toolbar>
                </AppBar>

                <Container maxWidth="xl" sx={{ mt: 6, mb: 6 }}>
                    <Grid container spacing={6}>
                        <Grid item xs={12}>
                            <Paper elevation={6} sx={{
                                p: 6,
                                background: 'linear-gradient(145deg, rgba(26, 26, 26, 0.95), rgba(33, 33, 33, 0.95))',
                                borderRadius: '32px',
                                border: '1px solid rgba(0, 188, 212, 0.3)',
                                boxShadow: '0 32px 96px rgba(0, 188, 212, 0.2), 0 16px 64px rgba(255, 64, 129, 0.1)',
                                backdropFilter: 'blur(40px)',
                                position: 'relative',
                                '&::before': {
                                    content: '""',
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    bottom: 0,
                                    background: 'linear-gradient(45deg, rgba(0, 188, 212, 0.08), rgba(255, 64, 129, 0.08))',
                                    borderRadius: '32px',
                                    zIndex: -1,
                                }
                            }}>
                                <Typography variant="h4" gutterBottom align="center" sx={{ mb: 6 }}>
                                    Advanced Face Recognition Platform
                                </Typography>

                                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 4 }}>
                                    <Tabs
                                        value={value}
                                        onChange={handleChange}
                                        aria-label="face recognition tabs"
                                        sx={{
                                            '& .MuiTab-root': {
                                                minHeight: 80,
                                                fontSize: '1.2rem',
                                                fontWeight: 600,
                                                borderRadius: '20px 20px 0 0',
                                                mr: 2,
                                                '&.Mui-selected': {
                                                    background: 'linear-gradient(45deg, #00bcd4 30%, #ff4081 90%)',
                                                    color: 'white',
                                                },
                                            },
                                        }}
                                    >
                                        <Tab icon={<PersonAdd />} label="Enroll Person" iconPosition="start" />
                                        <Tab icon={<CameraAlt />} label="Recognize Face" iconPosition="start" />
                                        <Tab icon={<SmartToy />} label="AI Assistant" iconPosition="start" />
                                        <Tab icon={<Dashboard />} label="Admin Panel" iconPosition="start" />
                                    </Tabs>
                                </Box>

                                <TabPanel value={value} index={0}>
                                    <EnrollmentForm />
                                </TabPanel>
                                <TabPanel value={value} index={1}>
                                    <RecognizeViewEnriched />
                                </TabPanel>
                                <TabPanel value={value} index={2}>
                                    <AIAssistant />
                                </TabPanel>
                                <TabPanel value={value} index={3}>
                                    <AdminDashboard />
                                </TabPanel>
                            </Paper>
                        </Grid>
                    </Grid>
                </Container>
            </Box>
        </ThemeProvider>
    );
}

export default App;
