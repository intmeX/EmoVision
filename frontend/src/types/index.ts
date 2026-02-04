export * from './detection';
export * from './emotion';
export * from './config';

// 通用类型
export type PipelineState = 'idle' | 'running' | 'paused' | 'error';

export type SourceType = 'image' | 'video' | 'camera';

export interface SourceInfo {
  source_type: SourceType;
  path?: string | null;
  camera_id?: number | null;
  width: number;
  height: number;
  fps: number;
  total_frames: number;
  current_frame?: number;
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  timestamp: number;
}

// WebSocket消息类型
export interface FrameMessage {
  type: 'frame';
  timestamp: number;
  frame_id: number;
  image: string;  // Base64字符串或Object URL
  detections: import('./detection').Detection[];
  emotions: import('./emotion').EmotionResult[];
  /** 标记image是否为Object URL（需要手动释放） */
  isObjectUrl?: boolean;
}

/** 二进制帧头部消息（用于二进制WebSocket传输） */
export interface FrameHeaderMessage {
  type: 'frame_header';
  timestamp: number;
  frame_id: number;
  image_size: number;
  detections: import('./detection').Detection[];
  emotions: import('./emotion').EmotionResult[];
}

export interface StatusMessage {
  type: 'status';
  timestamp: number;
  pipeline_state: PipelineState;
  source_info: SourceInfo | null;
}

export interface StatsMessage {
  type: 'stats';
  timestamp: number;
  fps: number;
  latency_ms: number;
  detection_count: number;
  gpu_usage?: number | null;
}

export interface ErrorMessage {
  type: 'error';
  timestamp: number;
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
}

export type WSMessage = FrameMessage | StatusMessage | StatsMessage | ErrorMessage;
