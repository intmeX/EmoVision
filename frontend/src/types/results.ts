// 结果展示与导出模块类型定义

import type { Detection } from './detection';
import type { EmotionResult } from './emotion';
import type { SourceInfo, SourceType } from './index';

/**
 * 历史帧元数据
 */
export interface StoredFrameMeta {
  /** 会话ID */
  sessionId: string;
  /** 帧ID */
  frameId: number;
  /** 时间戳 (ms) */
  timestamp: number;
  /** 源类型 */
  sourceType: SourceType;
  /** 源路径 */
  sourcePath?: string | null;

  /** 检测结果 */
  detections: Detection[];
  /** 情绪结果 */
  emotions: EmotionResult[];

  /** 图像引用 */
  imageRef: {
    /** 存储位置 */
    kind: 'memory' | 'indexeddb';
    /** 存储键 */
    key: string;
    /** MIME类型 */
    mime: 'image/jpeg';
    /** 字节大小 */
    byteLength: number;
    /** 图像宽度 */
    width: number;
    /** 图像高度 */
    height: number;
  };
}

/**
 * 结果会话摘要
 */
export interface ResultsSessionSummary {
  /** 会话ID */
  sessionId: string;
  /** 开始时间 */
  startedAt: number;
  /** 结束时间 */
  endedAt?: number;
  /** 源信息 */
  sourceInfo: SourceInfo | null;
  /** 已录制帧数 */
  totalFramesRecorded: number;
  /** 丢弃帧数 */
  droppedFrames: number;
}

/**
 * 帧索引（用于时间轴快速定位）
 */
export interface FrameIndex {
  /** 帧ID列表 */
  frameIds: number[];
  /** 时间戳列表 (与frameIds一一对应) */
  timestamps: number[];
  /** 关键帧间隔 */
  keyframeEvery: number;
}

/**
 * 录制策略配置
 */
export interface RecordingPolicy {
  /** 录制模式 */
  mode: 'all' | 'sampled' | 'keyframes';
  /** 采样帧率 (默认5fps) */
  sampleFps: number;
  /** 关键帧规则 */
  keyframeRules: {
    /** 检测数量变化时记录 */
    onDetectionCountChange: boolean;
    /** 主情绪变化时记录 */
    onDominantEmotionChange: boolean;
  };
  /** 限制 */
  limits: {
    /** 热存储最大帧数 (默认500) */
    maxHotFrames: number;
    /** 最大存储MB (默认300) */
    maxStorageMB?: number;
  };
  /** 存储选项 */
  store: {
    /** 是否持久化到IndexedDB */
    persistToIndexedDB: boolean;
    /** 是否存储完整图像 */
    storeFullImage: boolean;
    /** 是否存储缩略图 */
    storeThumbnail: boolean;
  };
}

/**
 * 默认录制策略
 */
export const DEFAULT_RECORDING_POLICY: RecordingPolicy = {
  mode: 'sampled',
  sampleFps: 5,
  keyframeRules: {
    onDetectionCountChange: true,
    onDominantEmotionChange: true,
  },
  limits: {
    maxHotFrames: 500,
    maxStorageMB: 300,
  },
  store: {
    persistToIndexedDB: false,
    storeFullImage: true,
    storeThumbnail: false,
  },
};

/**
 * 导出JSON格式 v1
 */
export interface ExportJsonV1 {
  /** 版本标识 */
  version: 'emovision-results-v1';
  /** 导出时间 */
  exportedAt: number;
  /** 会话信息 */
  session: ResultsSessionSummary;
  /** 帧数据 */
  frames: Array<{
    frameId: number;
    timestamp: number;
    detections: Detection[];
    emotions: EmotionResult[];
  }>;
}

/**
 * 视频导出能力
 */
export interface VideoExportCapabilities {
  /** 是否支持WebCodecs */
  webcodecs: boolean;
  /** 是否支持MediaRecorder */
  mediaRecorder: boolean;
  /** 是否支持SharedArrayBuffer */
  sharedArrayBuffer: boolean;
  /** 是否为安全上下文 */
  secureContext: boolean;
  /** 推荐容器格式 */
  preferredContainer: 'mp4' | 'webm';
}

/**
 * 导出状态
 */
export interface ExportState {
  json: {
    state: 'idle' | 'building' | 'done' | 'error';
    progress?: number;
    error?: string;
  };
  video: {
    state: 'idle' | 'encoding' | 'muxing' | 'done' | 'error';
    progress: number;
    error?: string;
  };
}

/**
 * 回看模式
 */
export type ReviewMode = 'live' | 'paused_review' | 'ended_review';

/**
 * 时间轴标记
 */
export interface TimelineMarker {
  /** 帧ID */
  frameId: number;
  /** 标记类型 */
  type: 'keyframe' | 'detection_change' | 'emotion_change';
  /** 标签 */
  label?: string;
}

/**
 * 带图像的历史帧（用于回看显示）
 */
export interface HistoryFrameWithImage {
  meta: StoredFrameMeta;
  blob: Blob;
}
