import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Button, Typography,  Card, CardContent, Box, Alert, CircularProgress, IconButton, Chip, Avatar, LinearProgress, Fab, Paper, Divider } from '@mui/material';
import { Grid } from '@mui/material';
import { CameraAlt, Search, Face, CheckCircle, Error, Person, SentimentVerySatisfied, SentimentDissatisfied, SentimentNeutral, MoodBad, Favorite, Videocam, VideocamOff, BarChart, PieChart } from '@mui/icons-material';

import type { Face as FaceType, RecognitionResult } from '../types';

interface RecognizeViewProps {
  result?: RecognitionResult | null;
}

const RecognizeView: React.FC<RecognizeViewProps> = ({ result }) => {
    const [image, setImage] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [severity, setSeverity] = useState<'success' | 'error' | 'info' | 'warning'>('success');
    const [webcamActive, setWebcamActive] = useState(false);
    const [results, setResults] = useState<RecognitionResult | null>(null);
    const [streamResults, setStreamResults] = useState<RecognitionResult | null>(null);
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const intervalRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        if (result) {
            setResults(result);
        }
    }, [result]);

    const getEmotionColor = (emotion: string): string => {
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

    const calculateEmotionSummary = (faces: FaceType[]) => {
        if (!faces || faces.length === 0) return null;

        const emotionCounts: Record<string, number> = {};
        const emotionScores: Record<string, number> = {};
        let totalFaces = faces.length;

        faces.forEach((face: FaceType) => {
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

        summary.sort((a, b) => b.count - a.count);

        return summary;
    };

    const handleSubmit = async (e: React.FormEvent) => {
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
        } catch (error: any) {
            console.error('Recognition failed');
            setMessage('Recognition failed. Please try again.');
            setSeverity('error');
        }
        setLoading(false);
    };

    const startWebcam = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            if (videoRef.current) videoRef.current!.srcObject = stream;
            setWebcamActive(true);
            setMessage('Webcam started successfully');
            setSeverity('success');

            // Connect to WebSocket
            const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
            const wsProtocol = baseURL.startsWith('https') ? 'wss' : 'ws';
            const host = baseURL.replace(/^https?:\/\//, '');
            wsRef.current = new WebSocket(`${wsProtocol}://${host}/api/recognize_stream`);
            wsRef.current.onopen = () => {
                console.log('WebSocket connected');
            };
            wsRef.current.onmessage = (event: MessageEvent) => {
                const data = JSON.parse(event.data);
                setStreamResults(data);
            };
            wsRef.current.onerror = (error: Event) => {
                console.error('WebSocket error:', error);
                setMessage('WebSocket connection failed');
                setSeverity('error');
            };

            intervalRef.current = setInterval(captureFrame, 500);
        } catch (error: any) {
            console.error('Error accessing webcam:', error);
            setMessage('Failed to access webcam. Please check permissions.');
            setSeverity('error');
        }
    };

    const stopWebcam = () => {
        if (videoRef.current && videoRef.current.srcObject) {
            const stream = videoRef.current.srcObject as MediaStream;
            const tracks = stream.getTracks();
            tracks.forEach((track: MediaStreamTrack) => track.stop());
            videoRef.current.srcObject = null;
        }
        setWebcamActive(false);
        setStreamResults(null);
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
        const context = canvas.getContext('2d')!;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob((blob: Blob | null) => {
            if (!blob) return;
            const reader = new FileReader();
            reader.onload = () => {
                const base64Data = (reader.result as string).split(',')[1]!;
                wsRef.current!.send(JSON.stringify({
                    type: 'frame',
                    data: base64Data
                }));
            };
            reader.readAsDataURL(blob);
        }, 'image/jpeg', 0.8);
    };

    const drawOverlays = () => {
        const overlayCanvas = overlayCanvasRef.current;
        if (!overlayCanvas || !streamResults || !streamResults.faces || !videoRef.current) return;

        const ctx = overlayCanvas.getContext('2d')!;
        const video = videoRef.current;
        overlayCanvas.width = video!.videoWidth;
        overlayCanvas.height = video!.videoHeight;
        ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        streamResults.faces.forEach((face: FaceType, idx: number) => {
            const [x, y, w, h] = face.face_box;

            ctx.strokeStyle = face.matches.length > 0 ? '#4caf50' : '#f44336';
            ctx.lineWidth = 3;
            ctx.strokeRect(x, y, w, h);

            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            ctx.fillRect(x, y - 40, w, 40);

            ctx.fillStyle = '#ffffff';
            ctx.font = '14px Arial';
            ctx.fillText(`Face ${idx + 1}`, x + 5, y - 25);

            if (face.matches.length > 0) {
                const match = face.matches[0];
                ctx.fillText(`${match.name} (${(match.score * 100).toFixed(1)}%)`, x + 5, y - 10);
            } else {
                ctx.fillText('Unknown', x + 5, y - 10);
            }

            if (face.emotion) {
                const emotion = face.emotion.dominant_emotion;
                ctx!.fillStyle = getEmotionColor(emotion);
                ctx!.font = '12px Arial';
                ctx!.fillText(emotion, x, y + h + 15);
            }

            if (face.age && face.gender) {
                ctx!.fillStyle = '#ffffff';
                ctx!.font = '12px Arial';
                ctx!.fillText(`${face.age}, ${face.gender}`, x, y + h + 30);
            }

            if (face.behavior) {
                ctx!.fillStyle = '#ffff00';
                ctx!.font = '12px Arial';
                ctx!.fillText(`Behavior: ${face.behavior.dominant_behavior}`, x, y + h + 45);
            }
        });
    };

    useEffect(() => {
        return () => {
            stopWebcam();
        };
    }, []);

    useEffect(() => {
        if (streamResults) {
            setTimeout(drawOverlays, 100);
        }
    }, [streamResults]);

    return (
        <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
            <Typography variant="h4" gutterBottom sx={{ mb: 4, textAlign: 'center' }}>
                Face Recognition
            </Typography>

            <Grid spacing={3}>
                <Grid size={{ xs: 12 }}>
                    <Card>
                        <CardContent>
                            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mb: 3 }}>
                                <Fab color={webcamActive ? 'secondary' : 'primary'} onClick={webcamActive ? stopWebcam : startWebcam}>
                                    {webcamActive ? <VideocamOff /> : <Videocam />}
                                </Fab>
                                <Typography variant="h6" align="center" sx={{ alignSelf: 'center' }}>
                                    {webcamActive ? 'Live Recognition Active' : 'Start Webcam Recognition'}
                                </Typography>
                            </Box>

                            {webcamActive && (
                                <Box sx={{ position: 'relative', textAlign: 'center' }}>
                                    <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', maxWidth: '640px', borderRadius: '8px' }} />
                                    <canvas ref={overlayCanvasRef} style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }} />
                                    <canvas ref={canvasRef} style={{ display: 'none' }} />
                                </Box>
                            )}

                            <form onSubmit={handleSubmit}>
                                <Grid spacing={3}>
                                    <Grid size={{ xs: 12 }}>
                                        <Button variant="contained" component="label" startIcon={<CameraAlt />}>
                                            Upload Image
                                            <input type="file" accept="image/*" hidden onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                                                const file = e.target.files?.[0] || null;
                                                setImage(file);
                                            }} />
                                        </Button>
                                    </Grid>
                                    <Grid size={{ xs: 12 }}>
                                        <Button type="submit" variant="contained" fullWidth color="primary" disabled={loading || !image}>
                                            {loading ? <CircularProgress size={24} /> : <Search />}
                                            {loading ? 'Analyzing...' : 'Analyze Image'}
                                        </Button>
                                    </Grid>
                                </Grid>
                            </form>
                        </CardContent>
                    </Card>
                </Grid>

                {message && (
                    <Grid size={{ xs: 12 }}>
                        <Alert severity={severity} onClose={() => setMessage('')}>
                            {message}
                        </Alert>
                    </Grid>
                )}

                {results && (
                    <Grid size={{ xs: 12 }}>
                        <Card>
                            <CardContent>
                                <Typography variant="h5">Results</Typography>
                                {/* Results content */}
                            </CardContent>
                        </Card>
                    </Grid>
                )}
            </Grid>
        </Box>
    );
};

export default RecognizeView;

