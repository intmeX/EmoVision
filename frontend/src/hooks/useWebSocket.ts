// WebSocket连接Hook

import { useEffect, useCallback } from 'react';
import { wsService } from '../services/websocket';
import { usePipelineStore } from '../store';
import type { WSMessage } from '../types';

export function useWebSocket() {
  const { 
    setConnected, 
    setState, 
    setSourceInfo, 
    updateFrame, 
    updateStats 
  } = usePipelineStore();
  
  const handleMessage = useCallback((message: WSMessage) => {
    switch (message.type) {
      case 'frame':
        updateFrame(message);
        break;
      case 'status':
        setState(message.pipeline_state);
        setSourceInfo(message.source_info);
        break;
      case 'stats':
        updateStats(message);
        break;
      case 'error':
        console.error('流水线错误:', message.message);
        break;
    }
  }, [setState, setSourceInfo, updateFrame, updateStats]);
  
  const handleConnection = useCallback((connected: boolean) => {
    setConnected(connected);
  }, [setConnected]);
  
  useEffect(() => {
    // 连接WebSocket
    wsService.connect();
    
    // 注册消息处理
    const unsubMessage = wsService.onMessage(handleMessage);
    const unsubConnection = wsService.onConnection(handleConnection);
    
    return () => {
      unsubMessage();
      unsubConnection();
      wsService.disconnect();
    };
  }, [handleMessage, handleConnection]);
  
  const sendControl = useCallback((action: 'start' | 'stop' | 'pause' | 'resume') => {
    wsService.send(action);
  }, []);
  
  return { sendControl };
}
