/**
 * 帧管理器服务
 * 
 * 在React状态之外管理帧数据，避免每帧触发重渲染
 */

import type { Detection, EmotionResult } from '@/types';

export interface FrameData {
  /** 图像数据（Base64字符串或Object URL） */
  image: string;
  /** 帧ID */
  frameId: number;
  /** 检测结果 */
  detections: Detection[];
  /** 情绪识别结果 */
  emotions: EmotionResult[];
  /** 时间戳 */
  timestamp: number;
}

type FrameCallback = (frame: FrameData) => void;

/**
 * 帧管理器类
 * 
 * 使用发布/订阅模式分发帧数据，不触发React状态更新
 */
class FrameManager {
  private callbacks: Set<FrameCallback> = new Set();
  private latestFrame: FrameData | null = null;

  /**
   * 更新帧数据
   * 
   * 直接通知所有订阅者，不触发React状态更新
   */
  updateFrame(frame: FrameData): void {
    this.latestFrame = frame;
    this.callbacks.forEach(cb => cb(frame));
  }

  /**
   * 订阅帧更新
   * 
   * @param callback 帧更新回调函数
   * @returns 取消订阅函数
   */
  subscribe(callback: FrameCallback): () => void {
    this.callbacks.add(callback);
    return () => this.callbacks.delete(callback);
  }

  /**
   * 获取最新帧
   */
  getLatestFrame(): FrameData | null {
    return this.latestFrame;
  }

  /**
   * 清除帧数据
   */
  clear(): void {
    this.latestFrame = null;
  }
}

/** 全局帧管理器单例 */
export const frameManager = new FrameManager();
