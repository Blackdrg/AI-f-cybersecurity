// src/components/AIFloatingAssistant.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Box, Button, Tooltip, Chip, Typography, IconButton } from '@mui/material';
import { motion } from 'framer-motion';
import { ChatBubbleOutline, MicNone, Mic, StopCircle, AccountCircle, Close } from '@mui/icons-material';

interface AIFloatingAssistantProps {
  isListening?: boolean;
  isProcessing?: boolean;
  onStartListening?: () => void;
  onStopListening?: () => void;
  onSendMessage?: (message: string) => void;
}

const AIFloatingAssistant = ({ 
  isListening = false, 
  isProcessing = false,
  onStartListening,
  onStopListening,
  onSendMessage
}: AIFloatingAssistantProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Array<{ text: string; isUser: boolean }>>([
    { text: "Hello, I'm your AI assistant. How can I help you today?", isUser: false }
  ]);
  const [inputValue, setInputValue] = useState('');
  const micRef = useRef(null);

  // Simulate AI thinking animation
  useEffect(() => {
    if (isProcessing) {
      // Add a thinking message
      setMessages(prev => [...prev, { text: "Thinking...", isUser: false }]);
      
      // Simulate processing delay
      const timer = setTimeout(() => {
        // Remove thinking message and add response
        setMessages(prev => {
          const updated = [...prev];
          updated.pop(); // Remove thinking message
          return [...updated, { text: "I've analyzed the data and identified 3 potential security threats in the western sector.", isUser: false }];
        });
      }, 2000);
      
      return () => clearTimeout(timer);
    }
  }, [isProcessing]);

  const handleSendMessage = () => {
    if (inputValue.trim() === '') return;
    
    const userMessage = inputValue;
    setInputValue('');
    setMessages(prev => [...prev, { text: userMessage, isUser: true }]);
    
    // Call the callback if provided
    if (onSendMessage) {
      onSendMessage(userMessage);
    }
    
    // Simulate AI response
    setTimeout(() => {
      setMessages(prev => [...prev, { text: "I've completed the requested action. Would you like me to initiate a deeper scan?", isUser: false }]);
    }, 1500);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  return (
    <Box sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1500 }}>
      {/* Main assistant button */}
      <Tooltip title="AI Assistant">
        <motion.div
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsOpen(!isOpen)}
        >
          <Box
            sx={{
              width: 60,
              height: 60,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #00ffff 0%, #00bcd4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 30px rgba(0, 255, 255, 0.5)',
              border: '2px solid rgba(0, 255, 255, 0.3)',
              position: 'relative'
            }}
          >
            {!isListening ? (
              <ChatBubbleOutline 
                sx={{ color: 'white', fontSize: 24 }} 
              />
            ) : (
              <>
                {!isProcessing ? (
                  <MicNone 
                    sx={{ color: 'white', fontSize: 24 }} 
                  />
                ) : (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <Mic 
                      sx={{ color: 'white', fontSize: 24 }} 
                    />
                  </motion.div>
                )}
              </>
            )}
            {/* Status indicator */}
            <Box
              sx={{
                position: 'absolute',
                bottom: -2,
                right: -2,
                width: 16,
                height: 16,
                borderRadius: '50%',
                background: isListening 
                  ? (isProcessing ? '#ff00ff' : '#00ff00') 
                  : '#00ffff',
                border: '2px solid rgba(10, 10, 10, 0.8)',
                boxShadow: '0 0 10px rgba(0, 255, 255, 0.7)'
              }}
            />
          </Box>
        </motion.div>
      </Tooltip>
      
      {/* Chat panel */}
      <motion.div
        initial={{ scale: 0, y: 20 }}
        animate={{ scale: isOpen ? 1 : 0, y: isOpen ? 0 : 20 }}
        exit={{ scale: 0, y: 20 }}
        transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
        style={{
          position: 'fixed',
          bottom: 100,
          right: 24,
          width: 320,
          maxHeight: '80vh',
          zIndex: 1501
        }}
      >
        <Box
          sx={{
            borderRadius: '20px',
            background: 'rgba(10, 10, 10, 0.8)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}
        >
          {/* Header */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              px: 4,
              py: 3,
              borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
              background: 'linear-gradient(to right, rgba(0, 255, 255, 0.1), rgba(0, 188, 212, 0.1))'
            }}
          >
            <Typography variant="h6" color="text.primary" sx={{ fontWeight: 600 }}>
              AI Assistant
            </Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Tooltip title="Clear Chat">
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => {
                    setMessages([
                      { text: "Hello, I'm your AI assistant. How can I help you today?", isUser: false }
                    ]);
                  }}
                  sx={{ p: 1, color: 'text.secondary' }}
                >
                  <ChatBubbleOutline sx={{ fontSize: 18 }} />
                </Button>
              </Tooltip>
              <Tooltip title="Close">
                <IconButton onClick={() => setIsOpen(false)} sx={{ p: 1, color: 'text.secondary' }}>
                  <Close sx={{ fontSize: 18 }} />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          
          {/* Messages */}
          <Box
            sx={{
              flex: 1,
              overflowY: 'auto',
              px: 4,
              py: 3,
              display: 'flex',
              flexDirection: 'column',
              gap: 2
            }}
          >
            {messages.map((msg, index) => (
              <Box
                key={index}
                sx={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 2
                }}
              >
                {msg.isUser ? null : (
                  <Box sx={{ width: 32, height: 32, borderRadius: '50%', background: 'rgba(0, 255, 255, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <ChatBubbleOutline sx={{ color: '#00ffff', fontSize: 16 }} />
                  </Box>
                )}
                <Box
                  sx={{
                    maxWidth: '80%',
                    padding: msg.isUser ? 8 : 12,
                    borderRadius: msg.isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                    background: msg.isUser 
                      ? 'rgba(0, 188, 212, 0.3)' 
                      : 'rgba(0, 255, 255, 0.1)',
                    color: msg.isUser ? 'white' : 'text.primary',
                    wordWrap: 'break-word'
                  }}
                >
                  {msg.text}
                </Box>
                {msg.isUser ? (
                  <Box sx={{ width: 32, height: 32, borderRadius: '50%', background: 'rgba(255, 255, 255, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <AccountCircle sx={{ color: '#00bcd4', fontSize: 16 }} />
                  </Box>
                ) : null}
              </Box>
            ))}
          </Box>
          
          {/* Input */}
          <Box sx={{ px: 4, py: 3, borderTop: '1px solid rgba(255, 255, 255, 0.1)', background: 'rgba(0, 0, 0, 0.2)' }}>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Box
                component="input"
                type="text"
                value={inputValue}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask me anything..."
                sx={{
                  flex: 1,
                  padding: '10px 14px',
                  borderRadius: '12px',
                  border: 'none',
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: 'white',
                  fontSize: '0.9rem',
                  outline: 'none',
                  '&::placeholder': {
                    color: 'rgba(255, 255, 255, 0.5)'
                  }
                }}
              />
              <Button
                variant="contained"
                sx={{
                  borderRadius: '12px',
                  px: 3,
                  background: isListening 
                    ? (isProcessing ? '#ff00ff' : '#00ff00') 
                    : '#00bcd4',
                  color: 'white',
                  fontWeight: 600,
                  textTransform: 'none',
                  '&:hover': {
                    background: isListening 
                      ? (isProcessing ? '#ff00ff' : '#00ff00') 
                      : '#0097a7'
                  }
                }}
                disabled={isListening && !isProcessing}
                onClick={handleSendMessage}
              >
                {isListening ? (isProcessing ? 'Stop' : 'Send') : 'Send'}
              </Button>
            </Box>
          </Box>
        </Box>
      </motion.div>
    </Box>
  );
};

export default AIFloatingAssistant;


