/**
 * 帧缓冲区服务
 * 
 * 缓冲帧数据以平滑播放，处理网络抖动
 */

import type { FrameData } from '@/services/frameManager';

interface BufferedFrame {
  data: FrameData;
  receivedAt: number;
}

/**
 * 帧缓冲区类
 * 
 * 实现帧缓冲以平滑网络抖动导致的卡顿
 */
class FrameBuffer {
  private buffer: BufferedFrame[] = [];
  private maxSize: number = 3;  // 最多缓冲3帧
  private playbackDelay: number = 50; // 50ms播放延迟

  /**
   * 添加帧到缓冲区
   */
  push(frame: FrameData): void {
    this.buffer.push({
      data: frame,
      receivedAt: performance.now(),
    });
    
    // 超出缓冲区大小时丢弃旧帧
    while (this.buffer.length > this.maxSize) {
      this.buffer.shift();
    }
  }

  /**
   * 获取应该播放的帧
   * 
   * 基于播放延迟返回合适的帧
   * 如果没有满足延迟条件的帧但缓冲区有帧，返回最新帧（避免黑屏）
   */
  getPlayableFrame(): FrameData | null {
    if (this.buffer.length === 0) {
      return null;
    }
    
    const now = performance.now();
    const targetTime = now - this.playbackDelay;
    
    // 找到最接近目标时间的帧
    let bestFrame: BufferedFrame | null = null;
    let bestIndex = -1;
    
    for (let i = 0; i < this.buffer.length; i++) {
      const frame = this.buffer[i];
      if (frame.receivedAt <= targetTime) {
        bestFrame = frame;
        bestIndex = i;
      }
    }
    
    // 移除已播放的帧
    if (bestIndex >= 0) {
      this.buffer.splice(0, bestIndex + 1);
      return bestFrame!.data;
    }
    
    // 如果没有满足延迟条件的帧，但缓冲区已满，返回最旧的帧
    // 这样可以避免视频黑屏，同时保持一定的缓冲
    if (this.buffer.length >= this.maxSize) {
      const oldestFrame = this.buffer.shift();
      return oldestFrame ? oldestFrame.data : null;
    }
    
    return null;
  }

  /**
   * 清空缓冲区
   */
  clear(): void {
    this.buffer = [];
  }

  /**
   * 获取缓冲区大小
   */
  size(): number {
    return this.buffer.length;
  }

  /**
   * 设置最大缓冲区大小
   */
  setMaxSize(size: number): void {
    this.maxSize = size;
  }

  /**
   * 设置播放延迟
   */
  setPlaybackDelay(delay: number): void {
    this.playbackDelay = delay;
  }
}

/** 全局帧缓冲区单例 */
export const frameBuffer = new FrameBuffer();
