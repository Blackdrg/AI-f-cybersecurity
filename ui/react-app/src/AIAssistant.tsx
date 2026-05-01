import React, { useState } from 'react';
import axios from 'axios';
import { TextField, Button, Typography, Paper, Box, Avatar, CircularProgress, Alert } from '@mui/material';
import { Send, SmartToy } from '@mui/icons-material';

const AIAssistant = () => {
    const [query, setQuery] = useState('');
    const [conversation, setConversation] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError('');

        // Add user message to conversation
        const userMessage = { role: 'user', content: query };
        setConversation(prev => [...prev, userMessage]);

        try {
            const response = await axios.post('/api/ai/assistant', { query });
            const aiMessage = {
                role: 'assistant',
                content: response.data.response,
                model: response.data.model_used
            };
            setConversation(prev => [...prev, aiMessage]);
            setQuery('');
        } catch (error) {
            console.error('AI Assistant error:', error);
            setError('Failed to get AI response. Please try again.');
        }
        setLoading(false);
    };

    return (
        <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
            <Typography variant="h4" gutterBottom style={{ display: 'flex', alignItems: 'center' }}>
                <SmartToy style={{ marginRight: '10px' }} />
                AI Assistant
            </Typography>
            <Typography variant="body1" color="textSecondary" gutterBottom>
                Ask me anything about face recognition, computer vision, or get help with your recognition tasks.
            </Typography>

            {/* Conversation Display */}
            <Paper elevation={2} style={{ height: '400px', overflowY: 'auto', padding: '20px', marginBottom: '20px' }}>
                {conversation.length === 0 ? (
                    <Box style={{ textAlign: 'center', color: '#666', marginTop: '150px' }}>
                        <SmartToy style={{ fontSize: '48px', marginBottom: '10px' }} />
                        <Typography variant="h6">How can I help you today?</Typography>
                        <Typography variant="body2">
                            Try asking about face recognition algorithms, best practices, or troubleshooting tips.
                        </Typography>
                    </Box>
                ) : (
                    conversation.map((message, index) => (
                        <Box key={index} style={{ marginBottom: '20px', display: 'flex' }}>
                            <Avatar style={{ marginRight: '10px', backgroundColor: message.role === 'user' ? '#1976d2' : '#4caf50' }}>
                                {message.role === 'user' ? 'U' : <SmartToy />}
                            </Avatar>
                            <Box style={{ flex: 1 }}>
                                <Typography variant="subtitle2" style={{ fontWeight: 'bold' }}>
                                    {message.role === 'user' ? 'You' : 'AI Assistant'}
                                    {message.model && (
                                        <span style={{ fontSize: '0.8em', color: '#666', marginLeft: '10px' }}>
                                            ({message.model})
                                        </span>
                                    )}
                                </Typography>
                                <Typography variant="body1" style={{ whiteSpace: 'pre-wrap' }}>
                                    {message.content}
                                </Typography>
                            </Box>
                        </Box>
                    ))
                )}
                {loading && (
                    <Box style={{ display: 'flex', alignItems: 'center', marginTop: '20px' }}>
                        <Avatar style={{ marginRight: '10px', backgroundColor: '#4caf50' }}>
                            <SmartToy />
                        </Avatar>
                        <CircularProgress size={20} style={{ marginRight: '10px' }} />
                        <Typography variant="body2" color="textSecondary">AI is thinking...</Typography>
                    </Box>
                )}
            </Paper>

            {/* Input Form */}
            <form onSubmit={handleSubmit}>
                <Box style={{ display: 'flex', gap: '10px' }}>
                    <TextField
                        fullWidth
                        variant="outlined"
                        placeholder="Ask me about face recognition, computer vision, or any related topic..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        disabled={loading}
                        multiline
                        maxRows={3}
                    />
                    <Button
                        type="submit"
                        variant="contained"
                        color="primary"
                        disabled={loading || !query.trim()}
                        style={{ minWidth: '100px' }}
                        startIcon={loading ? <CircularProgress size={20} /> : <Send />}
                    >
                        {loading ? 'Sending' : 'Send'}
                    </Button>
                </Box>
            </form>

            {error && (
                <Alert severity="error" style={{ marginTop: '20px' }}>
                    {error}
                </Alert>
            )}

            {/* Example Questions */}
            <Box style={{ marginTop: '30px' }}>
                <Typography variant="h6" gutterBottom>Example Questions:</Typography>
                <Box style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                    {[
                        "How does face recognition work?",
                        "What are the best practices for face recognition?",
                        "How to improve recognition accuracy?",
                        "Explain facial landmark detection",
                        "What are common face recognition challenges?"
                    ].map((question, index) => (
                        <Button
                            key={index}
                            variant="outlined"
                            size="small"
                            onClick={() => setQuery(question)}
                            disabled={loading}
                        >
                            {question}
                        </Button>
                    ))}
                </Box>
            </Box>
        </div>
    );
};

export default AIAssistant;
