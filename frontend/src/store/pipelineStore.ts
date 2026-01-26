// 流水线状态管理

import { create } from 'zustand';
import type { 
  PipelineState, 
  SourceInfo, 
  Detection, 
  EmotionResult,
  FrameMessage,
  StatsMessage 
} from '../types';

interface PipelineStore {
  // 状态
  state: PipelineState;
  connected: boolean;
  sourceInfo: SourceInfo | null;
  
  // 帧数据
  currentFrame: string | null;
  frameId: number;
  detections: Detection[];
  emotions: EmotionResult[];
  
  // 统计信息
  fps: number;
  latency: number;
  detectionCount: number;
  
  // Actions
  setState: (state: PipelineState) => void;
  setConnected: (connected: boolean) => void;
  setSourceInfo: (info: SourceInfo | null) => void;
  updateFrame: (frame: FrameMessage) => void;
  updateStats: (stats: StatsMessage) => void;
  reset: () => void;
}

export const usePipelineStore = create<PipelineStore>((set) => ({
  // 初始状态
  state: 'idle',
  connected: false,
  sourceInfo: null,
  currentFrame: null,
  frameId: 0,
  detections: [],
  emotions: [],
  fps: 0,
  latency: 0,
  detectionCount: 0,
  
  // Actions
  setState: (state) => set({ state }),
  
  setConnected: (connected) => set({ connected }),
  
  setSourceInfo: (sourceInfo) => set({ sourceInfo }),
  
  updateFrame: (frame) => set({
    currentFrame: frame.image,
    frameId: frame.frame_id,
    detections: frame.detections,
    emotions: frame.emotions,
  }),
  
  updateStats: (stats) => set({
    fps: stats.fps,
    latency: stats.latency_ms,
    detectionCount: stats.detection_count,
  }),
  
  reset: () => set({
    state: 'idle',
    currentFrame: null,
    frameId: 0,
    detections: [],
    emotions: [],
    fps: 0,
    latency: 0,
    detectionCount: 0,
  }),
}));
