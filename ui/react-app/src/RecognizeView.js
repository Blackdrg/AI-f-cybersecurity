import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Button, Typography, Grid, Card, CardContent, Box, Alert, CircularProgress, IconButton, Chip, Avatar, LinearProgress, Fab, Paper, Divider } from '@mui/material';
import { CameraAlt, Search, Face, CheckCircle, Error, Person, SentimentVerySatisfied, SentimentDissatisfied, SentimentNeutral, MoodBad, Favorite, Videocam, VideocamOff, BarChart, PieChart } from '@mui/icons-material';

const RecognizeView = () => {
    const [image, setImage] = useState(null);
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [severity, setSeverity] = useState('success');
    const [webcamActive, setWebcamActive] = useState(false);
    const [streamResults, setStreamResults] = useState(null);
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const overlayCanvasRef = useRef(null);
    const wsRef = useRef(null);
    const intervalRef = useRef(null);

    // Emotion-based theme adaptation with enhanced animations
    const getEmotionTheme = (emotion) => {
        if (!emotion) return {
            primary: '#00bcd4',
            secondary: '#ff4081',
            background: 'linear-gradient(145deg, rgba(0, 188, 212, 0.1), rgba(255, 64, 129, 0.05))',
            animation: 'pulse-cyan 2s infinite',
            intensity: 0.5
        };

        const dominant = emotion.dominant_emotion;
        const intensity = emotion.emotions[dominant] || 0.5;

        switch (dominant) {
            case 'happy':
                return {
                    primary: '#4caf50',
                    secondary: '#8bc34a',
                    background: `linear-gradient(145deg, rgba(76, 175, 80, ${0.1 + intensity * 0.2}), rgba(139, 195, 74, ${0.05 + intensity * 0.1}))`,
                    animation: `pulse-green ${2 - intensity}s infinite`,
                    intensity
                };
            case 'sad':
                return {
                    primary: '#2196f3',
                    secondary: '#03a9f4',
                    background: `linear-gradient(145deg, rgba(33, 150, 243, ${0.1 + intensity * 0.2}), rgba(3, 169, 244, ${0.05 + intensity * 0.1}))`,
                    animation: `pulse-blue ${2 - intensity}s infinite`,
                    intensity
                };
            case 'angry':
                return {
                    primary: '#f44336',
                    secondary: '#ff5722',
                    background: `linear-gradient(145deg, rgba(244, 67, 54, ${0.1 + intensity * 0.2}), rgba(255, 87, 34, ${0.05 + intensity * 0.1}))`,
                    animation: `pulse-red ${2 - intensity}s infinite`,
                    intensity
                };
            case 'fear':
                return {
                    primary: '#9c27b0',
                    secondary: '#673ab7',
                    background: `linear-gradient(145deg, rgba(156, 39, 176, ${0.1 + intensity * 0.2}), rgba(103, 58, 183, ${0.05 + intensity * 0.1}))`,
                    animation: `pulse-purple ${2 - intensity}s infinite`,
                    intensity
                };
            case 'surprise':
                return {
                    primary: '#ff9800',
                    secondary: '#ffc107',
                    background: `linear-gradient(145deg, rgba(255, 152, 0, ${0.1 + intensity * 0.2}), rgba(255, 193, 7, ${0.05 + intensity * 0.1}))`,
                    animation: `pulse-orange ${2 - intensity}s infinite`,
                    intensity
                };
            case 'disgust':
                return {
                    primary: '#795548',
                    secondary: '#607d8b',
                    background: `linear-gradient(145deg, rgba(121, 85, 72, ${0.1 + intensity * 0.2}), rgba(96, 125, 139, ${0.05 + intensity * 0.1}))`,
                    animation: `pulse-brown ${2 - intensity}s infinite`,
                    intensity
                };
            default:
                return {
                    primary: '#9e9e9e',
                    secondary: '#757575',
                    background: `linear-gradient(145deg, rgba(158, 158, 158, ${0.1 + intensity * 0.2}), rgba(117, 117, 117, ${0.05 + intensity * 0.1}))`,
                    animation: `pulse-gray ${2 - intensity}s infinite`,
                    intensity
                };
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
        if (!overlayCanvas || !streamResults || !streamResults.faces) return;

        const ctx = overlayCanvas.getContext('2d');
        const video = videoRef.current;
        if (!video) return;

        // Set canvas size to match video
        overlayCanvas.width = video.videoWidth;
        overlayCanvas.height = video.videoHeight;

        // Clear previous drawings
        ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

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

            // Draw behavior if available
            if (face.behavior) {
                ctx.fillStyle = '#ffff00';
                ctx.font = '12px Arial';
                ctx.fillText(`Behavior: ${face.behavior.dominant_behavior}`, x, y + h + 45);
            }
        });
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

    // Calculate emotion summary for dashboard
    const calculateEmotionSummary = (faces) => {
        if (!faces || faces.length === 0) return null;

        const emotionCounts = {};
        const emotionScores = {};
        let totalFaces = faces.length;

        faces.forEach(face => {
            if (face.emotion) {
                const dominant = face.emotion.dominant_emotion;
                emotionCounts[dominant] = (emotionCounts[dominant] || 0) + 1;
                emotionScores[dominant] = (emotionScores[dominant] || 0) + (face.emotion.emotions[dominant] || 0);
            }
        });

        const summary = Object.keys(emotionCounts).map(emotion => ({
            emotion,
            count: emotionCounts[emotion],
            percentage: (emotionCounts[emotion] / totalFaces) * 100,
            avgScore: emotionScores[emotion] / emotionCounts[emotion]
        }));

        // Sort by count descending
        summary.sort((a, b) => b.count - a.count);

        return summary;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!image) return;

        setLoading(true);
        setMessage('');
        const formData = new FormData();
        formData.append('image', image);

        try {
            const response = await axios.post('/api/recognize', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
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

    useEffect(() => {
        return () => {
            stopWebcam();
        };
    }, []);

    // Add CSS animations for emotion themes
    const emotionStyles = `
        @keyframes pulse-green { 0%, 100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.4); } 50% { box-shadow: 0 0 0 8px rgba(76, 175, 80, 0); } }
        @keyframes pulse-blue { 0%, 100% { box-shadow: 0 0 0 0 rgba(33, 150, 243, 0.4); } 50% { box-shadow: 0 0 0 8px rgba(33, 150, 243, 0); } }
        @keyframes pulse-red { 0%, 100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.4); } 50% { box-shadow: 0 0 0 8px rgba(244, 67, 54, 0); } }
        @keyframes pulse-purple { 0%, 100% { box-shadow: 0 0 0 0 rgba(156, 39, 176, 0.4); } 50% { box-shadow: 0 0 0 8px rgba(156, 39, 176, 0); } }
        @keyframes pulse-orange { 0%, 100% { box-shadow: 0 0 0 0 rgba(255, 152, 0, 0.4); } 50% { box-shadow: 0 0 0 8px rgba(255, 152, 0, 0); } }
        @keyframes pulse-brown { 0%, 100% { box-shadow: 0 0 0 0 rgba(121, 85, 72, 0.4); } 50% { box-shadow: 0 0 0 8px rgba(121, 85, 72, 0); } }
        @keyframes pulse-gray { 0%, 100% { box-shadow: 0 0 0 0 rgba(158, 158, 158, 0.4); } 50% { box-shadow: 0 0 0 8px rgba(158, 158, 158, 0); } }
        @keyframes pulse-cyan { 0%, 100% { box-shadow: 0 0 0 0 rgba(0, 188, 212, 0.4); } 50% { box-shadow: 0 0 0 8px rgba(0, 188, 212, 0); } }
    `;

    return (
        <>
            <style>{emotionStyles}</style>
            <Box sx={{
                maxWidth: 1200,
                mx: 'auto',
                transition: 'all 0.5s ease',
                background: (() => {
                    const currentFaces = webcamActive ? streamResults?.faces || [] : results?.faces || [];
                    const emotionSummary = calculateEmotionSummary(currentFaces);
                    if (emotionSummary && emotionSummary.length > 0) {
                        const dominantEmotion = emotionSummary[0].emotion;
                        const theme = getEmotionTheme({ dominant_emotion: dominantEmotion, emotions: { [dominantEmotion]: emotionSummary[0].avgScore } });
                        return theme.background;
                    }
                    return 'transparent';
                })(),
                borderRadius: '16px',
                p: 2
            }}>
                <Typography variant="h5" gutterBottom sx={{
                    mb: 4,
                    textAlign: 'center',
                    fontWeight: 600,
                    transition: 'all 0.3s ease',
                    color: (() => {
                        const currentFaces = webcamActive ? streamResults?.faces || [] : results?.faces || [];
                        const emotionSummary = calculateEmotionSummary(currentFaces);
                        if (emotionSummary && emotionSummary.length > 0) {
                            const dominantEmotion = emotionSummary[0].emotion;
                            const theme = getEmotionTheme({ dominant_emotion: dominantEmotion, emotions: { [dominantEmotion]: emotionSummary[0].avgScore } });
                            return theme.primary;
                        }
                        return 'text.primary';
                    })()
                }}>
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

                                {/* Emotion Summary Dashboard */}
                                {(() => {
                                    const currentFaces = webcamActive ? streamResults?.faces || [] : results?.faces || [];
                                    const emotionSummary = calculateEmotionSummary(currentFaces);
                                    if (emotionSummary && emotionSummary.length > 0) {
                                        return (
                                            <Box sx={{ mb: 4 }}>
                                                <Paper sx={{ p: 3, borderRadius: '16px', background: 'linear-gradient(145deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02))' }}>
                                                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                                                        <BarChart sx={{ mr: 1 }} />
                                                        Emotion Summary Dashboard
                                                    </Typography>
                                                    <Divider sx={{ mb: 2 }} />
                                                    <Grid container spacing={2}>
                                                        {emotionSummary.map((item, idx) => {
                                                            const theme = getEmotionTheme({ dominant_emotion: item.emotion, emotions: { [item.emotion]: item.avgScore } });
                                                            const icon = getEmotionIcon({ dominant_emotion: item.emotion });
                                                            return (
                                                                <Grid item xs={12} sm={6} md={3} key={idx}>
                                                                    <Box sx={{
                                                                        p: 2,
                                                                        borderRadius: '12px',
                                                                        background: theme.background,
                                                                        border: `1px solid ${theme.primary}40`,
                                                                        textAlign: 'center',
                                                                        transition: 'all 0.3s ease',
                                                                        animation: theme.animation,
                                                                        '&:hover': {
                                                                            transform: 'scale(1.05)',
                                                                            boxShadow: `0 4px 12px ${theme.primary}30`,
                                                                        }
                                                                    }}>
                                                                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 1 }}>
                                                                            {icon}
                                                                            <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
                                                                                {item.emotion.charAt(0).toUpperCase() + item.emotion.slice(1)}
                                                                            </Typography>
                                                                        </Box>
                                                                        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                                            {item.count} face{item.count > 1 ? 's' : ''} ({item.percentage.toFixed(1)}%)
                                                                        </Typography>
                                                                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                                                                            Avg: {(item.avgScore * 100).toFixed(0)}%
                                                                        </Typography>
                                                                    </Box>
                                                                </Grid>
                                                            );
                                                        })}
                                                    </Grid>
                                                </Paper>
                                            </Box>
                                        );
                                    }
                                    return null;
                                })()}

                                <Grid container spacing={3}>
                                    {(webcamActive ? streamResults?.faces || [] : results?.faces || []).map((face, idx) => {
                                        const emotionTheme = getEmotionTheme(face.emotion);
                                        const emotionIcon = getEmotionIcon(face.emotion);
                                        const intensity = emotionTheme.intensity || 0.5;
                                        return (
                                            <Grid item xs={12} sm={6} md={4} key={idx} sx={{
                                                transition: 'all 0.3s ease',
                                                transform: intensity > 0.7 ? 'scale(1.02)' : 'scale(1)',
                                            }}>
                                                <Card sx={{
                                                    p: intensity > 0.7 ? 4 : 3,
                                                    background: emotionTheme.background,
                                                    border: `1px solid ${emotionTheme.primary}40`,
                                                    borderRadius: '16px',
                                                    textAlign: 'center',
                                                    transition: 'all 0.3s ease',
                                                    animation: emotionTheme.animation,
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
                                                                    fontSize: intensity > 0.7 ? '1rem' : '0.9rem',
                                                                    fontWeight: intensity > 0.7 ? 700 : 600,
                                                                    px: intensity > 0.7 ? 1.5 : 1,
                                                                    py: intensity > 0.7 ? 0.75 : 0.5,
                                                                    borderRadius: '12px',
                                                                    backgroundColor: emotionTheme.primary,
                                                                    color: 'white',
                                                                    transition: 'all 0.3s ease',
                                                                    '&:hover': {
                                                                        transform: 'scale(1.05)',
                                                                    }
                                                                }}
                                                            />
                                                            {/* Emotion Scores */}
                                                            <Box sx={{ mt: 1 }}>
                                                                {Object.entries(face.emotion.emotions).map(([emotion, score]) => (
                                                                    <Box key={emotion} sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                                                                        <Typography variant="caption" sx={{
                                                                            minWidth: 60,
                                                                            textAlign: 'left',
                                                                            fontWeight: emotion === face.emotion.dominant_emotion ? 600 : 400,
                                                                            color: emotion === face.emotion.dominant_emotion ? emotionTheme.primary : 'text.secondary'
                                                                        }}>
                                                                            {emotion}
                                                                        </Typography>
                                                                        <LinearProgress
                                                                            variant="determinate"
                                                                            value={score * 100}
                                                                            sx={{
                                                                                flexGrow: 1,
                                                                                mx: 1,
                                                                                height: intensity > 0.7 ? 8 : 6,
                                                                                borderRadius: 3,
                                                                                backgroundColor: 'rgba(255, 255, 255, 0.2)',
                                                                                '& .MuiLinearProgress-bar': {
                                                                                    backgroundColor: emotion === face.emotion.dominant_emotion ? emotionTheme.primary : emotionTheme.secondary,
                                                                                    transition: 'all 0.3s ease',
                                                                                }
                                                                            }}
                                                                        />
                                                                        <Typography variant="caption" sx={{
                                                                            minWidth: 30,
                                                                            fontWeight: emotion === face.emotion.dominant_emotion ? 600 : 400,
                                                                            color: emotion === face.emotion.dominant_emotion ? emotionTheme.primary : 'text.secondary'
                                                                        }}>
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

                                                    {/* Behavior Display */}
                                                    {face.behavior && (
                                                        <Box sx={{ mt: 1 }}>
                                                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                                                Behavior: {face.behavior.dominant_behavior}
                                                            </Typography>
                                                        </Box>
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
            </Box>
        </>
    );
};

export default RecognizeView;
