/**
 * 帧历史记录器
 * 
 * 订阅帧流，按录制策略存储帧数据
 */

import type {
  Detection,
  EmotionResult,
  StoredFrameMeta,
  RecordingPolicy,
  SourceInfo,
} from '@/types';
import { historyRepository } from './historyRepository';
import { useResultsStore } from '@/store';

/**
 * 帧数据输入
 */
export interface FrameInput {
  frameId: number;
  timestamp: number;
  detections: Detection[];
  emotions: EmotionResult[];
  imageBlob: Blob;
}

/**
 * 帧历史记录器类
 * 
 * 根据录制策略决定是否存储帧
 */
class FrameHistoryRecorder {
  /** 当前会话ID */
  private sessionId: string | null = null;
  
  /** 录制策略 */
  private policy: RecordingPolicy = {
    mode: 'all',  // 默认记录所有帧，确保完整性
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
      persistToIndexedDB: true,  // 启用IndexedDB持久化，防止旧帧丢失
      storeFullImage: true,
      storeThumbnail: false,
    },
  };
  
  /** 上一帧的检测数量 */
  private lastDetectionCount: number = 0;
  
  /** 上一帧的主情绪 */
  private lastDominantEmotion: string | null = null;
  
  /** 上一次采样的时间戳 */
  private lastSampleTime: number = 0;
  
  /** 采样间隔（毫秒） */
  private sampleIntervalMs: number = 200; // 5fps = 200ms
  
  /** 源信息 */
  private sourceInfo: SourceInfo | null = null;
  
  /** 图像尺寸缓存 */
  private imageSize: { width: number; height: number } | null = null;
  
  /**
   * 开始新的录制会话
   */
  startSession(
    sessionId: string,
    sourceInfo: SourceInfo | null,
    policy?: Partial<RecordingPolicy>
  ): void {
    this.sessionId = sessionId;
    this.sourceInfo = sourceInfo;
    this.lastDetectionCount = 0;
    this.lastDominantEmotion = null;
    this.lastSampleTime = 0;
    this.imageSize = null;
    
    if (policy) {
      this.policy = { ...this.policy, ...policy };
    }
    
    this.sampleIntervalMs = 1000 / this.policy.sampleFps;
    
    // 初始化存储库
    historyRepository.startSession(sessionId, this.policy);
    
    console.log(`[FrameHistoryRecorder] 开始录制会话: ${sessionId}, mode=${this.policy.mode}`);
  }
  
  /**
   * 停止录制会话
   */
  stopSession(): void {
    console.log(`[FrameHistoryRecorder] 停止录制会话: ${this.sessionId}`);
    this.sessionId = null;
    this.sourceInfo = null;
    this.imageSize = null;
  }
  
  /**
   * 清空会话数据
   */
  clearSession(): void {
    this.stopSession();
    historyRepository.clear();
  }
  
  /**
   * 处理新帧
   */
  async onFrame(input: FrameInput): Promise<void> {
    if (!this.sessionId) {
      return;
    }
    
    // 检查是否应该记录此帧
    const shouldRecord = this.shouldRecordFrame(input);
    
    if (!shouldRecord) {
      // 更新丢弃计数
      useResultsStore.getState().actions.incrementDroppedFrames();
      return;
    }
    
    // 获取图像尺寸（首次时解析）
    if (!this.imageSize) {
      this.imageSize = await this.getImageSize(input.imageBlob);
    }
    
    // 构建元数据
    const meta: StoredFrameMeta = {
      sessionId: this.sessionId,
      frameId: input.frameId,
      timestamp: input.timestamp,
      sourceType: this.sourceInfo?.source_type ?? 'video',
      sourcePath: this.sourceInfo?.path,
      detections: input.detections,
      emotions: input.emotions,
      imageRef: {
        kind: 'memory',
        key: `${this.sessionId}:${input.frameId}`,
        mime: 'image/jpeg',
        byteLength: input.imageBlob.size,
        width: this.imageSize?.width ?? 0,
        height: this.imageSize?.height ?? 0,
      },
    };
    
    // 存储帧
    const stored = await historyRepository.storeFrame(meta, input.imageBlob);
    
    if (stored) {
      // 更新状态（传递情绪数据用于时间轴可视化）
      const actions = useResultsStore.getState().actions;
      actions.addFrameToIndex(input.frameId, input.timestamp, input.emotions);
      actions.incrementRecordedFrames();
      
      // 更新上一帧状态
      this.lastDetectionCount = input.detections.length;
      this.lastDominantEmotion = this.getDominantEmotion(input.emotions);
      this.lastSampleTime = input.timestamp;
    }
  }
  
  /**
   * 判断是否应该记录此帧
   */
  private shouldRecordFrame(input: FrameInput): boolean {
    const { mode, keyframeRules } = this.policy;
    
    // 全部记录模式
    if (mode === 'all') {
      return true;
    }
    
    // 关键帧模式
    if (mode === 'keyframes') {
      return this.isKeyframe(input, keyframeRules);
    }
    
    // 采样模式（默认）
    if (mode === 'sampled') {
      // 检查时间间隔
      const timeSinceLastSample = input.timestamp - this.lastSampleTime;
      if (timeSinceLastSample >= this.sampleIntervalMs) {
        return true;
      }
      
      // 即使未到采样时间，关键帧也要记录
      if (this.isKeyframe(input, keyframeRules)) {
        return true;
      }
    }
    
    return false;
  }
  
  /**
   * 判断是否为关键帧
   */
  private isKeyframe(
    input: FrameInput,
    rules: RecordingPolicy['keyframeRules']
  ): boolean {
    // 检测数量变化
    if (rules.onDetectionCountChange) {
      if (input.detections.length !== this.lastDetectionCount) {
        return true;
      }
    }
    
    // 主情绪变化
    if (rules.onDominantEmotionChange) {
      const currentDominant = this.getDominantEmotion(input.emotions);
      if (currentDominant !== this.lastDominantEmotion) {
        return true;
      }
    }
    
    return false;
  }
  
  /**
   * 获取主情绪
   */
  private getDominantEmotion(emotions: EmotionResult[]): string | null {
    if (emotions.length === 0) {
      return null;
    }
    
    // 找到置信度最高的情绪
    let maxConfidence = 0;
    let dominant: string | null = null;
    
    for (const emotion of emotions) {
      if (emotion.confidence > maxConfidence) {
        maxConfidence = emotion.confidence;
        dominant = emotion.dominant_emotion;
      }
    }
    
    return dominant;
  }
  
  /**
   * 获取图像尺寸
   */
  private async getImageSize(blob: Blob): Promise<{ width: number; height: number }> {
    return new Promise((resolve) => {
      const img = new Image();
      const url = URL.createObjectURL(blob);
      
      img.onload = () => {
        URL.revokeObjectURL(url);
        resolve({ width: img.naturalWidth, height: img.naturalHeight });
      };
      
      img.onerror = () => {
        URL.revokeObjectURL(url);
        resolve({ width: 0, height: 0 });
      };
      
      img.src = url;
    });
  }
  
  /**
   * 获取当前会话ID
   */
  getSessionId(): string | null {
    return this.sessionId;
  }
  
  /**
   * 获取录制策略
   */
  getPolicy(): RecordingPolicy {
    return { ...this.policy };
  }
  
  /**
   * 更新录制策略
   */
  setPolicy(policy: Partial<RecordingPolicy>): void {
    this.policy = { ...this.policy, ...policy };
    this.sampleIntervalMs = 1000 / this.policy.sampleFps;
  }
}

/** 全局帧历史记录器单例 */
export const frameHistoryRecorder = new FrameHistoryRecorder();
