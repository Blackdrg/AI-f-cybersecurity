import React from 'react';
import { Card, CardContent, Typography, Box, Chip, LinearProgress } from '@mui/material';
import { Face, SentimentSatisfied, Person, Security } from '@mui/icons-material';

const ResultCard = ({ data, timeTaken }) => {
  if (!data || !data.faces || data.faces.length === 0) {
    return (
      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="h6">No face detected</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1, opacity: 0.7 }}>
        Processing time: {(timeTaken * 1000).toFixed(0)}ms
      </Typography>
      {data.faces.map((face, index) => {
        const match = face.matches && face.matches.length > 0 ? face.matches[0] : null;
        const confidence = match ? (match.score * 100).toFixed(1) : 0;
        const spoofScore = face.spoof_score ? (face.spoof_score * 100).toFixed(1) : 0;

        return (
          <Card key={index} sx={{ mb: 2, borderLeft: '4px solid', borderLeftColor: face.is_unknown ? 'warning.main' : 'success.main' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
                    {face.is_unknown ? 'Unknown Person' : (match?.name || 'Identified')}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Face ID: {face.face_embedding_id.substring(0, 8)}...
                  </Typography>
                </Box>
                <Chip 
                  label={`${confidence}% Match`} 
                  color={parseFloat(confidence) > 80 ? "success" : "warning"}
                  icon={<Security />}
                />
              </Box>

              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                <Box>
                  <Typography variant="caption" display="block">Emotion</Typography>
                  <Typography variant="body1" sx={{ display: 'flex', alignItems: 'center' }}>
                    <SentimentSatisfied sx={{ mr: 1, fontSize: '1rem' }} />
                    {face.emotion?.dominant_emotion || 'N/A'}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" display="block">Age / Gender</Typography>
                  <Typography variant="body1" sx={{ display: 'flex', alignItems: 'center' }}>
                    <Person sx={{ mr: 1, fontSize: '1rem' }} />
                    {face.age ? `${face.age}y` : 'N/A'} / {face.gender || 'N/A'}
                  </Typography>
                </Box>
                <Box sx={{ gridColumn: 'span 2' }}>
                  <Typography variant="caption" display="block">Spoof Protection Score</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <LinearProgress 
                      variant="determinate" 
                      value={100 - spoofScore} 
                      sx={{ flexGrow: 1, mr: 1, height: 8, borderRadius: 4 }}
                      color={parseFloat(spoofScore) < 50 ? "success" : "error"}
                    />
                    <Typography variant="body2">{(100 - spoofScore).toFixed(0)}% Real</Typography>
                  </Box>
                </Box>
              </Box>
            </CardContent>
          </Card>
        );
      })}
    </Box>
  );
};

export default ResultCard;
