/**
 * WebSocket Manager — Enterprise AI Platform
 *
 * Auto-reconnect, heartbeat, event buffering, topic subscriptions.
 */

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

export interface WSMessage {
  topic: string;
  type: string;
  data: unknown;
  timestamp?: string;
}

type MessageHandler = (message: WSMessage) => void;
type StatusHandler = (status: ConnectionStatus) => void;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 20;
  private reconnectBaseDelay = 1000;
  private reconnectMaxDelay = 30000;
  private heartbeatInterval = 30000;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private subscriptions = new Map<string, Set<MessageHandler>>();
  private statusHandlers = new Set<StatusHandler>();
  private sendBuffer: string[] = [];
  private _status: ConnectionStatus = 'disconnected';
  private intentionalClose = false;

  constructor(url: string) {
    this.url = url;
  }

  get status(): ConnectionStatus { return this._status; }
  get isConnected(): boolean { return this._status === 'connected'; }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.intentionalClose = false;
    this.setStatus('connecting');
    try {
      let url = this.url;
      if (process.env.NODE_ENV === 'development') {
        const token = sessionStorage.getItem('token') || localStorage.getItem('token');
        if (token) url += `${url.includes('?') ? '&' : '?'}token=${token}`;
      }
      this.ws = new WebSocket(url);
      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setStatus('connected');
        this.startHeartbeat();
        this.flushSendBuffer();
        for (const topic of this.subscriptions.keys()) {
          this.send({ type: 'subscribe', topic });
        }
      };
      this.ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          if (msg.type === 'pong') return;
          this.subscriptions.get(msg.topic)?.forEach((h) => h(msg));
          this.subscriptions.get('*')?.forEach((h) => h(msg));
        } catch { /* ignore parse errors */ }
      };
      this.ws.onerror = () => this.setStatus('error');
      this.ws.onclose = () => {
        this.stopHeartbeat();
        this.ws = null;
        if (!this.intentionalClose) {
          this.setStatus('reconnecting');
          this.scheduleReconnect();
        } else {
          this.setStatus('disconnected');
        }
      };
    } catch {
      this.setStatus('error');
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.intentionalClose = true;
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.stopHeartbeat();
    if (this.ws) { this.ws.close(1000); this.ws = null; }
    this.setStatus('disconnected');
  }

  subscribe(topic: string, handler: MessageHandler): () => void {
    if (!this.subscriptions.has(topic)) this.subscriptions.set(topic, new Set());
    this.subscriptions.get(topic)!.add(handler);
    this.send({ type: 'subscribe', topic });
    return () => {
      const handlers = this.subscriptions.get(topic);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.subscriptions.delete(topic);
          this.send({ type: 'unsubscribe', topic });
        }
      }
    };
  }

  onStatusChange(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  send(data: unknown): void {
    const msg = typeof data === 'string' ? data : JSON.stringify(data);
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(msg);
    } else if (this.sendBuffer.length < 100) {
      this.sendBuffer.push(msg);
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.setStatus('error');
      return;
    }
    const delay = Math.min(this.reconnectBaseDelay * Math.pow(2, this.reconnectAttempts), this.reconnectMaxDelay);
    this.reconnectTimeout = setTimeout(() => { this.reconnectAttempts++; this.connect(); }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => this.send({ type: 'ping', timestamp: Date.now() }), this.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) { clearInterval(this.heartbeatTimer); this.heartbeatTimer = null; }
  }

  private flushSendBuffer(): void {
    while (this.sendBuffer.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(this.sendBuffer.shift()!);
    }
  }

  private setStatus(status: ConnectionStatus): void {
    this._status = status;
    this.statusHandlers.forEach((h) => h(status));
  }
}

const WS_URL = (process.env.REACT_APP_WS_URL || 'ws://localhost:8000') + '/ws';
export const wsManager = new WebSocketManager(WS_URL);
export default wsManager;
