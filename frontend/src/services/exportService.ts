/**
 * 导出服务
 * 
 * 提供 JSON 和视频导出功能
 * 
 * 视频导出策略：
 * - 首选：mediabunny (WebCodecs + MP4) - 高质量、高性能
 * - 降级：MediaRecorder (WebM) - 兼容性更好
 */

import type { ExportJsonV1 } from '@/types';
import { historyRepository } from './historyRepository';
import { useResultsStore } from '@/store';
import { detectVideoExportCapabilities, getSupportedMediaRecorderMimeTypes } from './videoExportCapabilities';

// Mediabunny 动态导入（仅在需要时加载）
type MediabunnyModule = typeof import('mediabunny');

/**
 * 导出服务类
 */
class ExportService {
  /**
   * 导出 JSON 数据
   */
  async exportJson(
    onProgress?: (progress: number) => void
  ): Promise<Blob> {
    const state = useResultsStore.getState();
    const session = state.actions.getActiveSession();
    
    if (!session) {
      throw new Error('没有可导出的会话数据');
    }
    
    const { summary, index } = session;
    
    // 更新导出状态
    state.actions.setExportState({
      json: { state: 'building', progress: 0 },
    });
    
    try {
      // 获取所有帧数据
      const frames = await historyRepository.getFramesBatch(
        index.frameIds,
        (progress) => {
          onProgress?.(progress * 0.8); // 80% 用于读取数据
          state.actions.setExportState({
            json: { state: 'building', progress: progress * 0.8 },
          });
        }
      );
      
      // 构建导出数据
      const exportData: ExportJsonV1 = {
        version: 'emovision-results-v1',
        exportedAt: Date.now(),
        session: summary,
        frames: frames.map((f) => ({
          frameId: f.meta.frameId,
          timestamp: f.meta.timestamp,
          detections: f.meta.detections,
          emotions: f.meta.emotions,
        })),
      };
      
      onProgress?.(0.9);
      state.actions.setExportState({
        json: { state: 'building', progress: 0.9 },
      });
      
      // 序列化为 JSON
      const jsonString = JSON.stringify(exportData, null, 2);
      const blob = new Blob([jsonString], { type: 'application/json' });
      
      onProgress?.(1);
      state.actions.setExportState({
        json: { state: 'done' },
      });
      
      return blob;
    } catch (error) {
      state.actions.setExportState({
        json: { state: 'error', error: String(error) },
      });
      throw error;
    }
  }
  
  /**
   * 下载 JSON 文件
   */
  async downloadJson(): Promise<void> {
    const blob = await this.exportJson();
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `emovision-results-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    URL.revokeObjectURL(url);
  }
  
  /**
   * 导出视频（使用 mediabunny - WebCodecs + MP4）
   * 
   * 首选方案：高质量 H.264 编码的 MP4 文件
   */
  async exportVideoMp4(
    fps: number = 5,
    onProgress?: (progress: number) => void
  ): Promise<Blob> {
    const state = useResultsStore.getState();
    const session = state.actions.getActiveSession();
    
    if (!session) {
      throw new Error('没有可导出的会话数据');
    }
    
    const { index } = session;
    
    if (index.frameIds.length === 0) {
      throw new Error('没有可导出的帧数据');
    }
    
    // 更新导出状态
    state.actions.setExportState({
      video: { state: 'encoding', progress: 0 },
    });
    
    try {
      // 动态导入 mediabunny
      const mediabunny: MediabunnyModule = await import('mediabunny');
      const { Output, Mp4OutputFormat, BufferTarget, VideoSampleSource, VideoSample, QUALITY_HIGH } = mediabunny;
      
      // 验证有帧数据
      const firstFrame = await historyRepository.getFrame(index.frameIds[0]);
      if (!firstFrame) {
        throw new Error('无法获取帧数据');
      }
      
      // 创建输出
      const target = new BufferTarget();
      const output = new Output({
        format: new Mp4OutputFormat(),
        target,
      });
      
      // 创建视频源（使用 H.264 编码）
      const videoSource = new VideoSampleSource({
        codec: 'avc',
        bitrate: QUALITY_HIGH,
      });
      
      output.addVideoTrack(videoSource, { frameRate: fps });
      
      await output.start();
      
      // 帧持续时间（秒）
      const frameDuration = 1 / fps;
      
      // 逐帧编码
      for (let i = 0; i < index.frameIds.length; i++) {
        const frame = await historyRepository.getFrame(index.frameIds[i]);
        if (frame) {
          // 创建 ImageBitmap
          const bitmap = await createImageBitmap(frame.blob);
          
          // 创建 VideoSample
          const timestamp = i * frameDuration;
          const sample = new VideoSample(bitmap, {
            timestamp,
            duration: frameDuration,
          });
          
          await videoSource.add(sample);
          
          sample.close();
          bitmap.close();
        }
        
        // 更新进度
        const progress = (i + 1) / index.frameIds.length;
        onProgress?.(progress * 0.9); // 90% 用于编码
        state.actions.setExportState({
          video: { state: 'encoding', progress: progress * 0.9 },
        });
      }
      
      // 更新状态为 muxing
      state.actions.setExportState({
        video: { state: 'muxing', progress: 0.95 },
      });
      
      // 完成输出
      await output.finalize();
      
      // 获取结果
      const buffer = target.buffer;
      if (!buffer) {
        throw new Error('视频编码失败：输出缓冲区为空');
      }
      const blob = new Blob([buffer], { type: 'video/mp4' });
      
      state.actions.setExportState({
        video: { state: 'done', progress: 1 },
      });
      
      return blob;
    } catch (error) {
      console.error('[ExportService] MP4 导出失败:', error);
      state.actions.setExportState({
        video: { state: 'error', progress: 0, error: String(error) },
      });
      throw error;
    }
  }
  
  /**
   * 导出视频（使用 MediaRecorder - WebM）
   * 
   * 降级方案：兼容性更好但质量较低
   */
  async exportVideoWebm(
    fps: number = 5,
    onProgress?: (progress: number) => void
  ): Promise<Blob> {
    const state = useResultsStore.getState();
    const session = state.actions.getActiveSession();
    
    if (!session) {
      throw new Error('没有可导出的会话数据');
    }
    
    const { index } = session;
    
    if (index.frameIds.length === 0) {
      throw new Error('没有可导出的帧数据');
    }
    
    // 检测能力
    const mimeTypes = getSupportedMediaRecorderMimeTypes();
    if (mimeTypes.length === 0) {
      throw new Error('浏览器不支持视频录制');
    }
    
    const mimeType = mimeTypes[0];
    
    // 更新导出状态
    state.actions.setExportState({
      video: { state: 'encoding', progress: 0 },
    });
    
    try {
      // 获取第一帧以确定尺寸
      const firstFrame = await historyRepository.getFrame(index.frameIds[0]);
      if (!firstFrame) {
        throw new Error('无法获取帧数据');
      }
      
      const width = firstFrame.meta.imageRef.width || 640;
      const height = firstFrame.meta.imageRef.height || 480;
      
      // 创建离屏 Canvas
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d')!;
      
      // 创建 MediaRecorder
      const stream = canvas.captureStream(fps);
      const recorder = new MediaRecorder(stream, { mimeType });
      const chunks: Blob[] = [];
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };
      
      // 开始录制
      recorder.start();
      
      // 逐帧渲染
      const frameInterval = 1000 / fps;
      
      for (let i = 0; i < index.frameIds.length; i++) {
        const frame = await historyRepository.getFrame(index.frameIds[i]);
        if (frame) {
          // 渲染帧到 Canvas
          const bitmap = await createImageBitmap(frame.blob);
          ctx.drawImage(bitmap, 0, 0, width, height);
          bitmap.close();
        }
        
        // 等待帧间隔
        await new Promise((resolve) => setTimeout(resolve, frameInterval));
        
        // 更新进度
        const progress = (i + 1) / index.frameIds.length;
        onProgress?.(progress);
        state.actions.setExportState({
          video: { state: 'encoding', progress },
        });
      }
      
      // 停止录制
      recorder.stop();
      
      // 等待录制完成
      await new Promise<void>((resolve) => {
        recorder.onstop = () => resolve();
      });
      
      // 合并数据
      const blob = new Blob(chunks, { type: mimeType });
      
      state.actions.setExportState({
        video: { state: 'done', progress: 1 },
      });
      
      return blob;
    } catch (error) {
      state.actions.setExportState({
        video: { state: 'error', progress: 0, error: String(error) },
      });
      throw error;
    }
  }
  
  /**
   * 下载视频文件
   * 
   * 自动选择最佳导出方案：
   * 1. 优先使用 mediabunny (MP4) - 需要 WebCodecs 支持
   * 2. 降级到 MediaRecorder (WebM)
   */
  async downloadVideo(preferMp4: boolean = true): Promise<void> {
    const caps = detectVideoExportCapabilities();
    
    let blob: Blob;
    let extension: string;
    
    // 优先尝试 MP4 导出（如果支持 WebCodecs）
    if (preferMp4 && caps.webcodecs) {
      try {
        blob = await this.exportVideoMp4();
        extension = 'mp4';
      } catch (error) {
        console.warn('[ExportService] MP4 导出失败，降级到 WebM:', error);
        // 降级到 WebM
        if (caps.mediaRecorder) {
          blob = await this.exportVideoWebm();
          extension = 'webm';
        } else {
          throw new Error('浏览器不支持视频导出');
        }
      }
    } else if (caps.mediaRecorder) {
      blob = await this.exportVideoWebm();
      extension = 'webm';
    } else {
      throw new Error('浏览器不支持视频导出');
    }
    
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `emovision-video-${Date.now()}.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    URL.revokeObjectURL(url);
  }
  
  /**
   * 下载 MP4 视频（强制使用 mediabunny）
   */
  async downloadVideoMp4(): Promise<void> {
    const caps = detectVideoExportCapabilities();
    
    if (!caps.webcodecs) {
      throw new Error('浏览器不支持 WebCodecs，无法导出 MP4');
    }
    
    const blob = await this.exportVideoMp4();
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `emovision-video-${Date.now()}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    URL.revokeObjectURL(url);
  }
  
  /**
   * 下载 WebM 视频（强制使用 MediaRecorder）
   */
  async downloadVideoWebm(): Promise<void> {
    const caps = detectVideoExportCapabilities();
    
    if (!caps.mediaRecorder) {
      throw new Error('浏览器不支持 MediaRecorder，无法导出 WebM');
    }
    
    const blob = await this.exportVideoWebm();
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `emovision-video-${Date.now()}.webm`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    URL.revokeObjectURL(url);
  }
}

/** 全局导出服务单例 */
export const exportService = new ExportService();
