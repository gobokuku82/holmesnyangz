// WebSocket Service for real-time updates

export interface WebSocketMessage {
  type: 'query' | 'response' | 'event' | 'error' | 'ping' | 'pong';
  content?: string;
  metadata?: any;
  timestamp: string;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectInterval: number = 5000;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  connect(sessionId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
      this.ws = new WebSocket(`${wsUrl}/${sessionId}`);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.clearReconnectTimer();
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.scheduleReconnect(sessionId);
      };
    });
  }

  disconnect(): void {
    this.clearReconnectTimer();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  sendQuery(query: string): void {
    this.send({
      type: 'query',
      content: query,
      timestamp: new Date().toISOString(),
    });
  }

  on(event: string, callback: (data: any) => void): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  off(event: string, callback: (data: any) => void): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.delete(callback);
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    // Emit to specific event listeners
    const callbacks = this.listeners.get(message.type);
    if (callbacks) {
      callbacks.forEach(callback => callback(message));
    }

    // Emit to general message listeners
    const allCallbacks = this.listeners.get('message');
    if (allCallbacks) {
      allCallbacks.forEach(callback => callback(message));
    }
  }

  private scheduleReconnect(sessionId: string): void {
    this.clearReconnectTimer();
    this.reconnectTimer = setTimeout(() => {
      console.log('Attempting to reconnect WebSocket...');
      this.connect(sessionId).catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, this.reconnectInterval);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

export default new WebSocketService();