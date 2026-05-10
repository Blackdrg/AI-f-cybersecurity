import React, { useState, FormEvent } from 'react';
import axios from 'axios';
import { TextField, Button, Typography, Paper, Box, Avatar, CircularProgress, Alert } from '@mui/material';
import { Send, SmartToy } from '@mui/icons-material';
import './AIAssistant.css';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    model?: string;
}

const AIAssistant = () => {
    const [query, setQuery] = useState('');
    const [conversation, setConversation] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError('');

        // Add user message to conversation
        const userMessage: Message = { role: 'user', content: query };
        setConversation(prev => [...prev, userMessage]);

        try {
            const response = await axios.post('/api/ai/assistant', { query });
            const aiMessage: Message = {
                role: 'assistant',
                content: response.data.response,
                model: response.data.model_used
            };
            setConversation(prev => [...prev, aiMessage]);
            setQuery('');
        } catch (error: any) {
            console.error('AI Assistant error:', error);
            setError('Failed to get AI response. Please try again.');
        }
        setLoading(false);
    };

    return (
        <div className="ai-assistant-container">
            <Typography variant="h4" gutterBottom className="ai-assistant-header">
                <SmartToy className="ai-assistant-header-icon" />
                AI Assistant
            </Typography>
            <Typography variant="body1" color="textSecondary" gutterBottom>
                Ask me anything about face recognition, computer vision, or get help with your recognition tasks.
            </Typography>

            {/* Conversation Display */}
            <Paper elevation={2} className="conversation-paper">
                {conversation.length === 0 ? (
                    <Box className="empty-state-box">
                        <SmartToy className="empty-state-icon" />
                        <Typography variant="h6">How can I help you today?</Typography>
                        <Typography variant="body2">
                            Try asking about face recognition algorithms, best practices, or troubleshooting tips.
                        </Typography>
                    </Box>
                ) : (
                    conversation.map((message, index) => (
                        <Box key={index} className="message-box">
                            <Avatar className={message.role === 'user' ? 'avatar-user' : 'avatar-ai'}>
                                {message.role === 'user' ? 'U' : <SmartToy />}
                            </Avatar>
                            <Box className="message-content">
                                <Typography variant="subtitle2" className="message-sender">
                                    {message.role === 'user' ? 'You' : 'AI Assistant'}
                                    {message.model && (
                                        <span className="model-info">
                                            ({message.model})
                                        </span>
                                    )}
                                </Typography>
                                <Typography variant="body1" className="message-text">
                                    {message.content}
                                </Typography>
                            </Box>
                        </Box>
                    ))
                )}
                {loading && (
                    <Box className="loading-box">
                        <Avatar className="avatar-ai">
                            <SmartToy />
                        </Avatar>
                        <CircularProgress size={20} className="loading-progress" />
                        <Typography variant="body2" color="textSecondary">AI is thinking...</Typography>
                    </Box>
                )}
            </Paper>

            {/* Input Form */}
            <form onSubmit={handleSubmit}>
                <Box className="input-box">
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
                        className="send-button"
                        startIcon={loading ? <CircularProgress size={20} /> : <Send />}
                    >
                        {loading ? 'Sending' : 'Send'}
                    </Button>
                </Box>
            </form>

            {error && (
                <Alert severity="error" className="error-alert">
                    {error}
                </Alert>
            )}

            {/* Example Questions */}
            <Box className="example-questions-container">
                <Typography variant="h6" gutterBottom>Example Questions:</Typography>
                <Box className="example-questions-box">
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
