import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Button, Typography, Grid, Card, CardContent, Box, Alert, CircularProgress, IconButton, Chip, Avatar, LinearProgress, Fab } from '@mui/material';
import { CameraAlt, Search, Face, CheckCircle, Error, Person, SentimentVerySatisfied, SentimentDissatisfied, SentimentNeutral, MoodBad, Favorite, Videocam, VideocamOff, Public, Visibility, VisibilityOff, Opacity } from '@mui/icons-material';
import ConsentModal from './ConsentModal.tsx';
import EnrichResultsPage from './EnrichResultsPage.tsx';

const RecognizeView = () => {
    const [image, setImage] = useState(null);
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [severity, setSeverity] = useState('success');
    const [webcamActive, setWebcamActive] = useState(false);
    const [streamResults, setStreamResults] = useState(null);
    const [consentModalOpen, setConsentModalOpen] = useState(false);
    const [enrichResultsPage, setEnrichResultsPage] = useState(null);
    const [consentToken, setConsentToken] = useState(null);
    const [enrichingPerson, setEnrichingPerson] = useState(null);
    const [overlaysVisible, setOverlaysVisible] = useState(true);
    const [overlayOpacity, setOverlayOpacity] = useState(0.8);
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const overlayCanvasRef = useRef(null);
    const wsRef = useRef(null);
    const intervalRef = useRef(null);

    // Emotion-based theme adaptation
    const getEmotionTheme = (emotion) => {
        if (!emotion) return { primary: '#00bcd4', secondary: '#ff4081', background: 'linear-gradient(145deg, rgba(0, 188, 212, 0.1), rgba(255, 64, 129, 0.05))' };

        const dominant = emotion.dominant_emotion;
        switch (dominant) {
            case 'happy':
                return { primary: '#4caf50', secondary: '#8bc34a', background: 'linear-gradient(145deg, rgba(76, 175, 80, 0.1), rgba(139, 195, 74, 0.05))' };
            case 'sad':
                return { primary: '#2196f3', secondary: '#03a9f4', background: 'linear-gradient(145deg, rgba(33, 150, 243, 0.1), rgba(3, 169, 244, 0.05))' };
            case 'angry':
                return { primary: '#f44336', secondary: '#ff5722', background: 'linear-gradient(145deg, rgba(244, 67, 54, 0.1), rgba(255, 87, 34, 0.05))' };
            case 'fear':
                return { primary: '#9c27b0', secondary: '#673ab7', background: 'linear-gradient(145deg, rgba(156, 39, 176, 0.1), rgba(103, 58, 183, 0.05))' };
            case 'surprise':
                return { primary: '#ff9800', secondary: '#ffc107', background: 'linear-gradient(145deg, rgba(255, 152, 0, 0.1), rgba(255, 193, 7, 0.05))' };
            case 'disgust':
                return { primary: '#795548', secondary: '#607d8b', background: 'linear-gradient(145deg, rgba(121, 85, 72, 0.1), rgba(96, 125, 139, 0.05))' };
            default:
                return { primary: '#9e9e9e', secondary: '#757575', background: 'linear-gradient(145deg, rgba(158, 158, 158, 0.1), rgba(117, 117, 117, 0.05))' };
        }
    };

    const getEmotionIcon = (emotion) => {
        if (!emotion) return <SentimentNeutral />;

        const dominant = emotion.dominant_emotion;
        switch (dominant) {
            case 'happy':
                return <SentimentVerySatisfied />;
            case 'sad':
                return <SentimentDissatisfied />;
            case 'angry':
            case 'fear':
            case 'disgust':
                return <MoodBad />;
            case 'surprise':
                return <Favorite />;
            default:
                return <SentimentNeutral />;
        }
    };

    const drawOverlays = () => {
        const overlayCanvas = overlayCanvasRef.current;
        if (!overlayCanvas || !streamResults || !streamResults.faces || !overlaysVisible) return;

        const ctx = overlayCanvas.getContext('2d');
        const video = videoRef.current;
        if (!video) return;

        // Set canvas size to match video
        overlayCanvas.width = video.videoWidth;
        overlayCanvas.height = video.videoHeight;

        // Clear previous drawings
        ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        // Set global alpha for opacity
        ctx.globalAlpha = overlayOpacity;

        streamResults.faces.forEach((face, idx) => {
            const [x, y, w, h] = face.face_box;

            // Draw bounding box
            ctx.strokeStyle = face.matches.length > 0 ? '#4caf50' : '#f44336';
            ctx.lineWidth = 3;
            ctx.strokeRect(x, y, w, h);

            // Draw background for text
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillRect(x, y - 40, w, 40);

            // Draw text
            ctx.fillStyle = '#ffffff';
            ctx.font = '14px Arial';
            ctx.fillText(`Face ${idx + 1}`, x + 5, y - 25);

            if (face.matches.length > 0) {
                const match = face.matches[0];
                ctx.fillText(`${match.name} (${(match.score * 100).toFixed(1)}%)`, x + 5, y - 10);
            } else {
                ctx.fillText('Unknown', x + 5, y - 10);
            }

            // Draw emotion if available
            if (face.emotion) {
                const emotion = face.emotion.dominant_emotion;
                ctx.fillStyle = getEmotionColor(emotion);
                ctx.font = '12px Arial';
                ctx.fillText(emotion, x, y + h + 15);
            }

            // Draw age/gender if available
            if (face.age && face.gender) {
                ctx.fillStyle = '#ffffff';
                ctx.font = '12px Arial';
                ctx.fillText(`${face.age}, ${face.gender}`, x, y + h + 30);
            }
        });

        // Reset global alpha
        ctx.globalAlpha = 1.0;
    };

    const getEmotionColor = (emotion) => {
        switch (emotion) {
            case 'happy': return '#4caf50';
            case 'sad': return '#2196f3';
            case 'angry': return '#f44336';
            case 'fear': return '#9c27b0';
            case 'surprise': return '#ff9800';
            case 'disgust': return '#795548';
            default: return '#9e9e9e';
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!image) return;

        setLoading(true);
        setMessage('');
        const formData = new FormData();
        formData.append('image', image);

        // Demo token for testing - in production this would come from login
        const demoToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZGVtb191c2VyIiwicm9sZSI6InVzZXIiLCJleHAiOjE3NjE4NDg5NDB9.i-LyW82-OUXFtLb9ggtRzLE6Yh3zyMBSMd0TQMPJJw9g';

        try {
            const response = await axios.post('/api/recognize', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'Authorization': `Bearer ${demoToken}`
                }
            });
            setResults(response.data);
            setMessage('Recognition completed successfully');
            setSeverity('success');
        } catch (error) {
            console.error('Recognition failed');
            setMessage('Recognition failed. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const startWebcam = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            videoRef.current.srcObject = stream;
            setWebcamActive(true);
            setMessage('Webcam started successfully');
            setSeverity('success');

            // Connect to WebSocket
            wsRef.current = new WebSocket('ws://localhost:8000/api/recognize_stream');
            wsRef.current.onopen = () => {
                console.log('WebSocket connected');
            };
            wsRef.current.onmessage = (event) => {
                const data = JSON.parse(event.data);
                setStreamResults(data);
                // Draw overlays after receiving results
                setTimeout(drawOverlays, 100); // Small delay to ensure video is ready
            };
            wsRef.current.onerror = (error) => {
                console.error('WebSocket error:', error);
                setMessage('WebSocket connection failed');
                setSeverity('error');
            };

            // Start capturing frames
            intervalRef.current = setInterval(captureFrame, 500);
        } catch (error) {
            console.error('Error accessing webcam:', error);
            setMessage('Failed to access webcam. Please check permissions.');
            setSeverity('error');
        }
    };

    const stopWebcam = () => {
        if (videoRef.current && videoRef.current.srcObject) {
            const stream = videoRef.current.srcObject;
            const tracks = stream.getTracks();
            tracks.forEach(track => track.stop());
            videoRef.current.srcObject = null;
        }
        setWebcamActive(false);
        setStreamResults(null);
        // Clear overlays
        const overlayCanvas = overlayCanvasRef.current;
        if (overlayCanvas) {
            const ctx = overlayCanvas.getContext('2d');
            ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
        setMessage('Webcam stopped');
        setSeverity('info');
    };

    const captureFrame = () => {
        if (!videoRef.current || !canvasRef.current || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

        const canvas = canvasRef.current;
        const video = videoRef.current;
        const context = canvas.getContext('2d');

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob((blob) => {
            const reader = new FileReader();
            reader.onload = () => {
                const base64Data = reader.result.split(',')[1];
                wsRef.current.send(JSON.stringify({
                    type: 'frame',
                    data: base64Data
                }));
            };
            reader.readAsDataURL(blob);
        }, 'image/jpeg', 0.8);
    };

    const handleEnrichPublicProfile = (person) => {
        setEnrichingPerson(person);
        setConsentModalOpen(true);
    };

    const handleConsentGranted = (token) => {
        setConsentToken(token);
        performEnrichment(token);
    };

    const performEnrichment = async (token) => {
        if (!enrichingPerson) return;

        setLoading(true);
        setMessage('Enriching public profile...');

        try {
            const response = await axios.post('/api/public_enrich', {
                person_id: enrichingPerson.person_id,
                identifiers: { name: enrichingPerson.name || 'Unknown' },
                requested_by: 'user',
                purpose: 'Identity verification',
                consent_token: token,
                providers: ['mock'] // Use mock for demo, can add 'bing', 'wikipedia'
            });

            setEnrichResultsPage(response.data.enrich_id);
            setMessage('Public profile enrichment completed');
            setSeverity('success');
        } catch (error) {
            console.error('Enrichment failed:', error);
            setMessage('Public profile enrichment failed. Please try again.');
            setSeverity('error');
        } finally {
            setLoading(false);
        }
    };

    const handleBackFromEnrich = () => {
        setEnrichResultsPage(null);
        setConsentToken(null);
        setEnrichingPerson(null);
    };

    useEffect(() => {
        return () => {
            stopWebcam();
        };
    }, []);

    // Show enrichment results page if we have an enrich ID
    if (enrichResultsPage) {
        return <EnrichResultsPage enrichId={enrichResultsPage} onBack={handleBackFromEnrich} />;
    }

    return (
        <Box sx={{ maxWidth: 1000, mx: 'auto' }}>
            <Typography variant="h5" gutterBottom sx={{ mb: 4, textAlign: 'center', fontWeight: 600 }}>
                <CameraAlt sx={{ mr: 1, verticalAlign: 'middle' }} />
                Face Recognition
            </Typography>

            <Grid container spacing={4}>
                <Grid item xs={12}>
                    <Card sx={{ p: 4 }}>
                        <CardContent>
                            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
                                <Fab
                                    color={webcamActive ? 'secondary' : 'primary'}
                                    onClick={webcamActive ? stopWebcam : startWebcam}
                                    sx={{ mr: 2 }}
                                >
                                    {webcamActive ? <VideocamOff /> : <Videocam />}
                                </Fab>
                                <Typography variant="h6" sx={{ alignSelf: 'center' }}>
                                    {webcamActive ? 'Stop Webcam' : 'Start Webcam'}
                                </Typography>
                            </Box>

                            {webcamActive && (
                                <Box sx={{ textAlign: 'center', mb: 3, position: 'relative' }}>
                                    <video
                                        ref={videoRef}
                                        autoPlay
                                        playsInline
                                        muted
                                        style={{
                                            width: '100%',
                                            maxWidth: '500px',
                                            borderRadius: '16px',
                                            border: '2px solid #00bcd4'
                                        }}
                                    />
                                    <canvas
                                        ref={overlayCanvasRef}
                                        style={{
                                            position: 'absolute',
                                            top: 0,
                                            left: 0,
                                            width: '100%',
                                            maxWidth: '500px',
                                            height: 'auto',
                                            borderRadius: '16px',
                                            pointerEvents: 'none'
                                        }}
                                    />
                                    <canvas ref={canvasRef} style={{ display: 'none' }} />

                                    {/* Overlay Controls */}
                                    <Box sx={{
                                        position: 'absolute',
                                        top: 10,
                                        right: 10,
                                        display: 'flex',
                                        gap: 1,
                                        background: 'rgba(0, 0, 0, 0.7)',
                                        borderRadius: '8px',
                                        p: 1
                                    }}>
                                        <IconButton
                                            size="small"
                                            onClick={() => setOverlaysVisible(!overlaysVisible)}
                                            sx={{ color: 'white' }}
                                        >
                                            {overlaysVisible ? <Visibility /> : <VisibilityOff />}
                                        </IconButton>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <Opacity sx={{ color: 'white', fontSize: '1rem' }} />
                                            <input
                                                type="range"
                                                min="0.1"
                                                max="1"
                                                step="0.1"
                                                value={overlayOpacity}
                                                onChange={(e) => setOverlayOpacity(parseFloat(e.target.value))}
                                                style={{
                                                    width: '60px',
                                                    accentColor: '#00bcd4'
                                                }}
                                            />
                                        </Box>
                                    </Box>
                                </Box>
                            )}

                            <form onSubmit={handleSubmit}>
                                <Grid container spacing={3}>
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
                                                id="image-recognize"
                                                type="file"
                                                onChange={(e) => setImage(e.target.files?.[0] || null)}
                                            />
                                            <label htmlFor="image-recognize">
                                                <IconButton component="span" sx={{ fontSize: '3rem', color: '#00bcd4' }}>
                                                    <CameraAlt />
                                                </IconButton>
                                            </label>
                                            <Typography variant="h6" sx={{ mt: 2, color: 'text.secondary' }}>
                                                Upload Image for Recognition
                                            </Typography>
                                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                Select a clear photo containing faces to recognize
                                            </Typography>
                                            {image && (
                                                <Typography variant="body2" sx={{ mt: 1, color: '#00bcd4' }}>
                                                    {image.name} selected
                                                </Typography>
                                            )}
                                        </Box>
                                    </Grid>

                                    <Grid item xs={12}>
                                        <Button
                                            type="submit"
                                            variant="contained"
                                            fullWidth
                                            disabled={loading || !image}
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
                                            startIcon={loading ? <CircularProgress size={20} /> : <Search />}
                                        >
                                            {loading ? 'Recognizing...' : 'Recognize Faces'}
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

                {(results && results.faces && results.faces.length > 0) || (streamResults && streamResults.faces && streamResults.faces.length > 0) ? (
                    <Grid item xs={12}>
                        <Card sx={{ p: 4 }}>
                            <CardContent>
                                <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
                                    <Face sx={{ mr: 1, verticalAlign: 'middle' }} />
                                    {webcamActive ? 'Live Recognition Results' : 'Recognition Results'}
                                </Typography>

                                <Grid container spacing={3}>
                                    {(webcamActive ? streamResults?.faces || [] : results?.faces || []).map((face, idx) => {
                                        const emotionTheme = getEmotionTheme(face.emotion);
                                        const emotionIcon = getEmotionIcon(face.emotion);
                                        const person = face.matches && face.matches.length > 0 ? face.matches[0] : null;
                                        return (
                                            <Grid item xs={12} sm={6} md={4} key={idx}>
                                                <Card sx={{
                                                    p: 3,
                                                    background: emotionTheme.background,
                                                    border: `1px solid ${emotionTheme.primary}40`,
                                                    borderRadius: '16px',
                                                    textAlign: 'center',
                                                    transition: 'all 0.3s ease',
                                                    '&:hover': {
                                                        transform: 'translateY(-4px)',
                                                        boxShadow: `0 8px 24px ${emotionTheme.primary}30`,
                                                    }
                                                }}>
                                                    <Avatar sx={{
                                                        width: 60,
                                                        height: 60,
                                                        mx: 'auto',
                                                        mb: 2,
                                                        bgcolor: face.matches.length > 0 ? emotionTheme.primary : emotionTheme.secondary
                                                    }}>
                                                        <Person />
                                                    </Avatar>
                                                    <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                                                        Face {idx + 1}
                                                    </Typography>

                                                    {/* Emotion Display */}
                                                    {face.emotion && (
                                                        <Box sx={{ mb: 2 }}>
                                                            <Chip
                                                                icon={emotionIcon}
                                                                label={face.emotion.dominant_emotion}
                                                                sx={{
                                                                    fontSize: '0.9rem',
                                                                    fontWeight: 600,
                                                                    px: 1,
                                                                    py: 0.5,
                                                                    borderRadius: '12px',
                                                                    backgroundColor: emotionTheme.primary,
                                                                    color: 'white',
                                                                }}
                                                            />
                                                            {/* Emotion Scores */}
                                                            <Box sx={{ mt: 1 }}>
                                                                {Object.entries(face.emotion.emotions).map(([emotion, score]) => (
                                                                    <Box key={emotion} sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                                                                        <Typography variant="caption" sx={{ minWidth: 60, textAlign: 'left' }}>
                                                                            {emotion}
                                                                        </Typography>
                                                                        <LinearProgress
                                                                            variant="determinate"
                                                                            value={score * 100}
                                                                            sx={{
                                                                                flexGrow: 1,
                                                                                mx: 1,
                                                                                height: 6,
                                                                                borderRadius: 3,
                                                                                backgroundColor: 'rgba(255, 255, 255, 0.2)',
                                                                                '& .MuiLinearProgress-bar': {
                                                                                    backgroundColor: emotionTheme.secondary,
                                                                                }
                                                                            }}
                                                                        />
                                                                        <Typography variant="caption" sx={{ minWidth: 30 }}>
                                                                            {(score * 100).toFixed(0)}%
                                                                        </Typography>
                                                                    </Box>
                                                                ))}
                                                            </Box>
                                                        </Box>
                                                    )}

                                                    {face.matches.length > 0 ? (
                                                        <Box>
                                                            <Chip
                                                                label={face.matches[0].name}
                                                                sx={{
                                                                    fontSize: '1rem',
                                                                    fontWeight: 600,
                                                                    px: 2,
                                                                    py: 1,
                                                                    borderRadius: '12px',
                                                                    backgroundColor: emotionTheme.primary,
                                                                    color: 'white',
                                                                }}
                                                            />
                                                            <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                                                                Confidence: {(face.matches[0].score * 100).toFixed(1)}%
                                                            </Typography>

                                                            {/* Public Enrichment Button */}
                                                            <Button
                                                                variant="outlined"
                                                                size="small"
                                                                startIcon={<Public />}
                                                                onClick={() => handleEnrichPublicProfile({
                                                                    person_id: face.matches[0].person_id,
                                                                    name: face.matches[0].name
                                                                })}
                                                                sx={{
                                                                    mt: 2,
                                                                    borderRadius: '8px',
                                                                    borderColor: emotionTheme.primary,
                                                                    color: emotionTheme.primary,
                                                                    '&:hover': {
                                                                        borderColor: emotionTheme.secondary,
                                                                        backgroundColor: `${emotionTheme.primary}10`,
                                                                    }
                                                                }}
                                                            >
                                                                Enrich Public Profile
                                                            </Button>
                                                        </Box>
                                                    ) : (
                                                        <Chip
                                                            label="Unknown"
                                                            variant="outlined"
                                                            sx={{
                                                                fontSize: '1rem',
                                                                fontWeight: 600,
                                                                px: 2,
                                                                py: 1,
                                                                borderRadius: '12px',
                                                                borderColor: emotionTheme.secondary,
                                                                color: emotionTheme.secondary,
                                                            }}
                                                        />
                                                    )}

                                                    {/* Additional Info */}
                                                    {face.age && (
                                                        <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                                                            Age: {face.age}, Gender: {face.gender}
                                                        </Typography>
                                                    )}
                                                </Card>
                                            </Grid>
                                        );
                                    })}
                                </Grid>
                            </CardContent>
                        </Card>
                    </Grid>
                ) : webcamActive ? (
                    <Grid item xs={12}>
                        <Card sx={{ p: 4 }}>
                            <CardContent sx={{ textAlign: 'center' }}>
                                <Typography variant="h6" sx={{ color: 'text.secondary' }}>
                                    Waiting for faces to be detected...
                                </Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                ) : null}
            </Grid>

            {/* Consent Modal */}
            <ConsentModal
                open={consentModalOpen}
                onClose={() => setConsentModalOpen(false)}
                personId={enrichingPerson?.person_id}
                identifiers={{ name: enrichingPerson?.name || 'Unknown' }}
                onConsentGranted={handleConsentGranted}
            />
        </Box>
    );
};

export default RecognizeView;
