import React, { useState } from 'react';
import { 
  Box, Typography, Paper, Grid, Button, 
  Tabs, Tab, TextField, Divider, Chip,
  IconButton, List, ListItem, ListItemText
} from '@mui/material';
import { 
  Code, IntegrationInstructions, PlayArrow, 
  ContentCopy, Description 
} from '@mui/icons-material';

const DeveloperPlatform = () => {
  const [tab, setTab] = useState(0);
  const [apiKey, setApiKey] = useState('fr_live_a1b2c3d4e5f6g7h8i9j0');

  const codeSnippets = {
    python: `import requests

url = "https://api.faceai.pro/v2/recognize"
files = {"image": open("face.jpg", "rb")}
headers = {"Authorization": "Bearer ${apiKey}"}

response = requests.post(url, files=files, headers=headers)
print(response.json())`,
    javascript: `const axios = require('axios');
const fs = require('fs');

const url = "https://api.faceai.pro/v2/recognize";
const data = new FormData();
data.append('image', fs.createReadStream('face.jpg'));

const config = {
  headers: { 
    'Authorization': 'Bearer ${apiKey}',
    ...data.getHeaders()
  }
};

axios.post(url, data, config)
  .then(res => console.log(res.data))
  .catch(err => console.error(err));`
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Developer Platform</Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom><Code /> API Playground</Typography>
            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
              <Tabs value={tab} onChange={(e, v) => setTab(v)}>
                <Tab label="Python" />
                <Tab label="JavaScript" />
                <Tab label="cURL" />
              </Tabs>
            </Box>
            <Box sx={{ bgcolor: '#1e1e1e', p: 2, borderRadius: 1, position: 'relative' }}>
              <pre style={{ margin: 0, color: '#d4d4d4', overflowX: 'auto' }}>
                <code>{tab === 0 ? codeSnippets.python : codeSnippets.javascript}</code>
              </pre>
              <IconButton 
                size="small" 
                sx={{ position: 'absolute', top: 8, right: 8, color: 'white' }}
                onClick={() => navigator.clipboard.writeText(tab === 0 ? codeSnippets.python : codeSnippets.javascript)}
              >
                <ContentCopy fontSize="small" />
              </IconButton>
            </Box>
            <Button variant="contained" startIcon={<PlayArrow />} sx={{ mt: 2 }}>
              Test Request
            </Button>
          </Paper>

          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom><IntegrationInstructions /> Webhooks</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Receive real-time notifications when a recognition event occurs.
            </Typography>
            <TextField 
              fullWidth 
              label="Webhook URL" 
              placeholder="https://your-server.com/webhooks/faceai"
              sx={{ mb: 2 }}
            />
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip label="person.detected" onClick={() => {}} />
              <Chip label="person.unknown" onClick={() => {}} />
              <Chip label="system.health" variant="outlined" />
            </Box>
            <Button variant="outlined" sx={{ mt: 2 }}>Save Config</Button>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom><Description /> Documentation</Typography>
            <List dense>
              <ListItem button>
                <ListItemText primary="Authentication Guide" secondary="How to use Bearer tokens" />
              </ListItem>
              <ListItem button>
                <ListItemText primary="API Reference" secondary="Full list of endpoints" />
              </ListItem>
              <ListItem button>
                <ListItemText primary="SDK Installation" secondary="Python, JS, Go" />
              </ListItem>
              <ListItem button>
                <ListItemText primary="Rate Limits" secondary="Understanding quotas" />
              </ListItem>
            </List>
            <Button fullWidth variant="outlined" sx={{ mt: 2 }}>Open Docs</Button>
          </Paper>

          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>Active SDKs</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              <Chip icon={<Code />} label="Python v2.4" />
              <Chip icon={<Code />} label="Node.js v1.8" />
              <Chip icon={<Code />} label="Go v0.9 (Beta)" variant="outlined" />
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DeveloperPlatform;
