import React, { useEffect, useRef, useState } from 'react';
import { Paper, Typography, Box, Chip } from '@mui/material';
import { Camera, Person, Warning } from '@mui/icons-material';

const LiveCameraFeed = ({ cameraId = 'cam1', orgId = 'org123' }) => {
  const videoRef = useRef(null);
  const wsRef = useRef(null);
  const [status, setStatus] = useState('disconnected');
  const [recentFaces, setRecentFaces] = useState([]);
  const [unknownCount, setUnknownCount] = useState(0);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/stream_recognize?org_id=${orgId}&camera_id=${cameraId}`);
    
    ws.onopen = () => {
      setStatus('connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.frame) {
        // Mock frame overlay - in real, canvas draw bbox
        const img = new Image();
        img.src = `data:image/jpeg;base64,${data.frame}`;
        img.onload = () => {
          const ctx = videoRef.current?.getContext('2d');
          if (ctx) {
            ctx.drawImage(img, 0, 0, 640, 480);
            // Draw faces
            data.faces?.forEach(face => {
              ctx.strokeStyle = face.confidence > 0.6 ? 'green' : 'red';
              ctx.strokeRect(face.bbox[0], face.bbox[1], face.bbox[2], face.bbox[3]);
              ctx.fillStyle = face.name ? 'green' : 'red';
              ctx.fillText(face.name || 'Unknown', face.bbox[0], face.bbox[1] - 5);
            });
          }
        };
      }
      if (data.faces) {
        const known = data.faces.filter(f => f.name);
        const unknown = data.faces.filter(f => !f.name);
        setRecentFaces(known.slice(0,5));
        setUnknownCount(unknown.length);
      }
    };

    ws.onclose = () => setStatus('disconnected');
    ws.onerror = () => setStatus('error');

    wsRef.current = ws;

    return () => ws.close();
  }, [cameraId, orgId]);

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">
          <Camera sx={{ mr: 1 }} />
          Live Feed - {cameraId}
        </Typography>
        <Chip label={status} color={status === 'connected' ? 'success' : 'error'} />
      </Box>
      <canvas ref={videoRef} width={640} height={480} style={{ width: '100%', border: '1px solid #444' }} />
      <Box sx={{ mt: 2 }}>
        <Typography variant="body2">Unknown Faces: {unknownCount}</Typography>
        <Typography variant="body2">Recent: {recentFaces.map(f => f.name).join(', ') || 'None'}</Typography>
      </Box>
    </Paper>
  );
};

export default LiveCameraFeed;

