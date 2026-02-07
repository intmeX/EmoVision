/**
 * 视频导出能力检测
 * 
 * 检测浏览器支持的视频编码和导出能力
 */

import type { VideoExportCapabilities } from '@/types';

/**
 * 检测视频导出能力
 */
export function detectVideoExportCapabilities(): VideoExportCapabilities {
  const webcodecs = typeof VideoEncoder !== 'undefined';
  const mediaRecorder = typeof MediaRecorder !== 'undefined';
  const sharedArrayBuffer = typeof SharedArrayBuffer !== 'undefined';
  const secureContext = window.isSecureContext;
  
  // 优先使用 WebCodecs (MP4)，降级到 MediaRecorder (WebM)
  const preferredContainer = webcodecs ? 'mp4' : 'webm';
  
  return {
    webcodecs,
    mediaRecorder,
    sharedArrayBuffer,
    secureContext,
    preferredContainer,
  };
}

/**
 * 检测是否支持特定视频编码器
 */
export async function canEncodeVideo(
  codec: 'avc' | 'vp8' | 'vp9' | 'av1',
  config: { width: number; height: number; bitrate?: number }
): Promise<boolean> {
  if (typeof VideoEncoder === 'undefined') {
    return false;
  }
  
  const codecMap: Record<string, string> = {
    avc: 'avc1.42001E', // H.264 Baseline Level 3.0
    vp8: 'vp8',
    vp9: 'vp09.00.10.08',
    av1: 'av01.0.04M.08',
  };
  
  try {
    const support = await VideoEncoder.isConfigSupported({
      codec: codecMap[codec],
      width: config.width,
      height: config.height,
      bitrate: config.bitrate ?? 2_000_000,
    });
    
    return support.supported ?? false;
  } catch {
    return false;
  }
}

/**
 * 获取推荐的视频编码器
 */
export async function getRecommendedVideoCodec(
  width: number,
  height: number
): Promise<'avc' | 'vp9' | 'vp8' | null> {
  // 优先级：H.264 > VP9 > VP8
  const codecs: Array<'avc' | 'vp9' | 'vp8'> = ['avc', 'vp9', 'vp8'];
  
  for (const codec of codecs) {
    if (await canEncodeVideo(codec, { width, height })) {
      return codec;
    }
  }
  
  return null;
}

/**
 * 检测 MediaRecorder 支持的 MIME 类型
 */
export function getSupportedMediaRecorderMimeTypes(): string[] {
  if (typeof MediaRecorder === 'undefined') {
    return [];
  }
  
  const mimeTypes = [
    'video/webm;codecs=vp9',
    'video/webm;codecs=vp8',
    'video/webm',
    'video/mp4',
  ];
  
  return mimeTypes.filter((type) => MediaRecorder.isTypeSupported(type));
}

/**
 * 获取导出能力摘要（用于UI显示）
 */
export function getExportCapabilitySummary(): {
  canExportMp4: boolean;
  canExportWebm: boolean;
  recommendedFormat: 'mp4' | 'webm' | null;
  warnings: string[];
} {
  const caps = detectVideoExportCapabilities();
  const warnings: string[] = [];
  
  const canExportMp4 = caps.webcodecs;
  const canExportWebm = caps.mediaRecorder;
  
  if (!caps.secureContext) {
    warnings.push('非安全上下文，部分功能可能受限');
  }
  
  if (!canExportMp4 && !canExportWebm) {
    warnings.push('浏览器不支持视频导出');
  }
  
  let recommendedFormat: 'mp4' | 'webm' | null = null;
  if (canExportMp4) {
    recommendedFormat = 'mp4';
  } else if (canExportWebm) {
    recommendedFormat = 'webm';
  }
  
  return {
    canExportMp4,
    canExportWebm,
    recommendedFormat,
    warnings,
  };
}
