import { useState, useEffect, useRef, useCallback } from 'react';

interface RecognitionResult {
  [key: string]: unknown;
}

interface UseRecognitionStreamOptions {
  autoReconnect?: boolean;
  autoConnect?: boolean;
  onResult?: (data: RecognitionResult) => void;
}

interface UseRecognitionStreamReturn {
  lastResult: RecognitionResult | null;
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  error: string | null;
  connect: () => void;
  disconnect: () => void;
  send: (data: unknown) => void;
}

/**
 * useRecognitionStream Hook
 * Manages WebSocket connection for real-time biometric streaming.
 */
export const useRecognitionStream = (url: string, options: UseRecognitionStreamOptions = {}): UseRecognitionStreamReturn => {
  const [lastResult, setLastResult] = useState<RecognitionResult | null>(null);
  const [status, setStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [error, setError] = useState<string | null>(null);
  
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
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
          const data: RecognitionResult = JSON.parse(event.data);
          setLastResult(data);
          if (options.onResult) options.onResult(data);
        } catch (err: unknown) {
          console.error('Failed to parse WS message:', err);
        }
      };
      
      socket.onerror = (err: Event) => {
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
    } catch (err: unknown) {
      setStatus('error');
      setError(err instanceof Error ? err.message : String(err));
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
  
  const send = useCallback((data: unknown) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
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


