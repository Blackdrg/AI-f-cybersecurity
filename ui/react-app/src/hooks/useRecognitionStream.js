import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useRecognitionStream Hook
 * Manages WebSocket connection for real-time biometric streaming.
 */
export const useRecognitionStream = (url, options = {}) => {
  const [lastResult, setLastResult] = useState(null);
  const [status, setStatus] = useState('disconnected'); // disconnected, connecting, connected, error
  const [error, setError] = useState(null);
  
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  
  const connect = useCallback(() => {
    if (socketRef.current) return;
    
    setStatus('connecting');
    const token = localStorage.getItem('token');
    const wsUrl = `${url}?token=${token}`;
    
    try {
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;
      
      socket.onopen = () => {
        setStatus('connected');
        setError(null);
        console.log('Recognition WebSocket connected');
      };
      
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastResult(data);
          if (options.onResult) options.onResult(data);
        } catch (err) {
          console.error('Failed to parse WS message:', err);
        }
      };
      
      socket.onerror = (err) => {
        setStatus('error');
        setError('WebSocket error');
        console.error('WebSocket Error:', err);
      };
      
      socket.onclose = () => {
        setStatus('disconnected');
        socketRef.current = null;
        console.log('Recognition WebSocket closed');
        
        // Auto-reconnect
        if (options.autoReconnect !== false) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
        }
      };
    } catch (err) {
      setStatus('error');
      setError(err.message);
    }
  }, [url, options]);
  
  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    setStatus('disconnected');
  }, []);
  
  const send = useCallback((data) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(typeof data === 'string' ? data : JSON.stringify(data));
    } else {
      console.warn('Cannot send: WebSocket is not open');
    }
  }, []);

  useEffect(() => {
    if (options.autoConnect) {
      connect();
    }
    return () => disconnect();
  }, [connect, disconnect, options.autoConnect]);

  return {
    lastResult,
    status,
    error,
    connect,
    disconnect,
    send
  };
};
