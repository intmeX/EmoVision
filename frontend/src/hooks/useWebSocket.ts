/**
 * WebSocket连接Hook
 * 
 * 管理WebSocket连接并分发消息到FrameManager和Zustand store
 */

import { useEffect, useCallback } from 'react';
import { wsService, type FrameMessageWithBlob } from '@/services/websocket';
import { frameManager } from '@/services/frameManager';
import { frameHistoryRecorder } from '@/services/frameHistoryRecorder';
import { usePipelineStore, useResultsStore } from '@/store';
import type { WSMessage, EventMessage } from '@/types';

export function useWebSocket() {
  const { 
    setConnected, 
    setState, 
    setSourceInfo, 
    updateStats 
  } = usePipelineStore();
  
  const resultsActions = useResultsStore((state) => state.actions);
  
  const handleMessage = useCallback((message: WSMessage) => {
    switch (message.type) {
      case 'frame': {
        // 帧数据通过FrameManager分发，不触发React重渲染
        const frameMsg = message as FrameMessageWithBlob;
        
        // 更新帧管理器（用于实时显示）
        frameManager.updateFrame({
          image: frameMsg.image,
          frameId: frameMsg.frame_id,
          detections: frameMsg.detections,
          emotions: frameMsg.emotions,
          timestamp: frameMsg.timestamp,
        });
        
        // 通知历史记录器（用于回看和导出）
        if (frameMsg.imageBlob) {
          frameHistoryRecorder.onFrame({
            frameId: frameMsg.frame_id,
            timestamp: frameMsg.timestamp,
            detections: frameMsg.detections,
            emotions: frameMsg.emotions,
            imageBlob: frameMsg.imageBlob,
          });
        }
        break;
      }
      case 'status':
        setState(message.pipeline_state);
        setSourceInfo(message.source_info);
        break;
      case 'stats':
        updateStats(message);
        break;
      case 'event': {
        // 处理生命周期事件
        const eventMsg = message as EventMessage;
        if (eventMsg.name === 'eos') {
          // 视频/图像播放结束
          console.log('收到EOS事件:', eventMsg.reason, 'frame_id:', eventMsg.frame_id);
          resultsActions.markEnded();
        }
        break;
      }
      case 'error':
        console.error('流水线错误:', message.message);
        break;
    }
  }, [setState, setSourceInfo, updateStats, resultsActions]);
  
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
