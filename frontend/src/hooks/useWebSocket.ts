/**
 * WebSocket连接Hook
 * 
 * 管理WebSocket连接并分发消息到FrameManager和Zustand store
 */

import { useEffect, useCallback } from 'react';
import { wsService } from '@/services/websocket';
import { frameManager } from '@/services/frameManager';
import { usePipelineStore } from '@/store';
import type { WSMessage, FrameMessage } from '@/types';

export function useWebSocket() {
  const { 
    setConnected, 
    setState, 
    setSourceInfo, 
    updateStats 
  } = usePipelineStore();
  
  const handleMessage = useCallback((message: WSMessage) => {
    switch (message.type) {
      case 'frame': {
        // 帧数据通过FrameManager分发，不触发React重渲染
        const frameMsg = message as FrameMessage;
        frameManager.updateFrame({
          image: frameMsg.image,
          frameId: frameMsg.frame_id,
          detections: frameMsg.detections,
          emotions: frameMsg.emotions,
          timestamp: frameMsg.timestamp,
        });
        break;
      }
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
  }, [setState, setSourceInfo, updateStats]);
  
  const handleConnection = useCallback((connected: boolean) => {
    setConnected(connected);
    if (!connected) {
      // 断开连接时清除帧数据
      frameManager.clear();
    }
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
