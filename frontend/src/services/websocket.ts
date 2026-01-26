// WebSocket服务

import type { WSMessage } from '../types';

type MessageHandler = (message: WSMessage) => void;
type ConnectionHandler = (connected: boolean) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private connectionHandlers: Set<ConnectionHandler> = new Set();
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/stream`;
    
    try {
      this.ws = new WebSocket(url);
      
      this.ws.onopen = () => {
        console.log('WebSocket 已连接');
        this.reconnectAttempts = 0;
        this.notifyConnectionChange(true);
      };
      
      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WSMessage;
          this.notifyMessage(message);
        } catch (error) {
          console.error('解析WebSocket消息失败:', error);
        }
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket 已断开');
        this.notifyConnectionChange(false);
        this.scheduleReconnect();
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
      };
    } catch (error) {
      console.error('WebSocket 连接失败:', error);
      this.scheduleReconnect();
    }
  }
  
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
  
  send(action: 'start' | 'stop' | 'pause' | 'resume'): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action }));
    }
  }
  
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }
  
  onConnection(handler: ConnectionHandler): () => void {
    this.connectionHandlers.add(handler);
    return () => this.connectionHandlers.delete(handler);
  }
  
  private notifyMessage(message: WSMessage): void {
    this.messageHandlers.forEach((handler) => handler(message));
  }
  
  private notifyConnectionChange(connected: boolean): void {
    this.connectionHandlers.forEach((handler) => handler(connected));
  }
  
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('WebSocket 重连次数已达上限');
      return;
    }
    
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * this.reconnectAttempts;
    
    console.log(`${delay}ms 后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimer = window.setTimeout(() => {
      this.connect();
    }, delay);
  }
}

export const wsService = new WebSocketService();
