/**
 * WebSocket React Hooks
 *
 * Provides React hooks for subscribing to WebSocket topics
 * and tracking connection status.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { wsManager, type ConnectionStatus, type WSMessage } from './manager';

/**
 * Hook to track WebSocket connection status.
 */
export function useWSStatus(): ConnectionStatus {
  const [status, setStatus] = useState<ConnectionStatus>(wsManager.status);

  useEffect(() => {
    const unsub = wsManager.onStatusChange(setStatus);
    return unsub;
  }, []);

  return status;
}

/**
 * Hook to subscribe to a WebSocket topic and receive messages.
 */
export function useWSSubscription<T = unknown>(
  topic: string,
  options: { enabled?: boolean } = {},
) {
  const { enabled = true } = options;
  const [lastMessage, setLastMessage] = useState<T | null>(null);
  const [messages, setMessages] = useState<T[]>([]);
  const maxMessages = 50;

  useEffect(() => {
    if (!enabled) return;

    const unsub = wsManager.subscribe(topic, (msg: WSMessage) => {
      const data = msg.data as T;
      setLastMessage(data);
      setMessages((prev) => [data, ...prev].slice(0, maxMessages));
    });

    return unsub;
  }, [topic, enabled]);

  const clear = useCallback(() => {
    setLastMessage(null);
    setMessages([]);
  }, []);

  return { lastMessage, messages, clear };
}

/**
 * Hook for real-time dashboard metrics.
 */
export function useRealtimeMetrics() {
  return useWSSubscription<Record<string, unknown>>('metrics');
}

/**
 * Hook for real-time alert notifications.
 */
export function useRealtimeAlerts() {
  return useWSSubscription<Record<string, unknown>>('alerts');
}

/**
 * Hook for AI inference streaming.
 */
export function useRealtimeInference() {
  return useWSSubscription<Record<string, unknown>>('inference');
}

/**
 * Hook to connect/disconnect WebSocket on mount/unmount.
 */
export function useWSConnection(autoConnect = true) {
  const status = useWSStatus();
  const connectedRef = useRef(false);

  useEffect(() => {
    if (autoConnect && !connectedRef.current) {
      connectedRef.current = true;
      wsManager.connect();
    }

    return () => {
      // Don't disconnect on unmount — keep connection alive
      // across route changes. Only disconnect on logout.
    };
  }, [autoConnect]);

  const connect = useCallback(() => wsManager.connect(), []);
  const disconnect = useCallback(() => wsManager.disconnect(), []);
  const send = useCallback((data: unknown) => wsManager.send(data), []);

  return { status, connect, disconnect, send };
}
