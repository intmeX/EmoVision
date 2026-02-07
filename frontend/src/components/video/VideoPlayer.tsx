/**
 * 视频播放器组件
 * 
 * 使用Canvas渲染帧数据，避免React重渲染
 * 支持实时模式和回看模式
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { usePipelineStore, useResultsStore } from '@/store';
import { useFrame } from '@/hooks/useFrame';
import { frameBuffer } from '@/services/frameBuffer';
import { historyRepository } from '@/services/historyRepository';
import { Video } from 'lucide-react';
import { getSourceTypeLabel } from '@/utils/helpers';
import type { HistoryFrameWithImage } from '@/types';

export function VideoPlayer() {
  const { sourceInfo, state } = usePipelineStore();
  const { reviewMode, selectedFrameId } = useResultsStore();
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ctxRef = useRef<CanvasRenderingContext2D | null>(null);
  const rafIdRef = useRef<number>(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [dimensions, setDimensions] = useState({ width: 640, height: 480 });
  
  // 用于非运行状态显示的静态帧
  const [staticFrame, setStaticFrame] = useState<string | null>(null);
  
  // 回看帧数据
  const [reviewFrame, setReviewFrame] = useState<HistoryFrameWithImage | null>(null);

  // 判断是否处于回看模式
  const isReviewMode = reviewMode === 'paused_review' || reviewMode === 'ended_review';

  // 更新尺寸
  useEffect(() => {
    if (sourceInfo) {
      setDimensions({ width: sourceInfo.width, height: sourceInfo.height });
    }
  }, [sourceInfo]);

  // 接收帧数据到缓冲区
  useFrame(useCallback((frame) => {
    frameBuffer.push(frame);
    // 保存最新帧用于非运行状态显示
    setStaticFrame(frame.image);
  }, []));

  // 回看模式：加载选中的历史帧
  useEffect(() => {
    if (!isReviewMode || selectedFrameId === null) {
      setReviewFrame(null);
      return;
    }
    
    // 异步加载帧数据
    historyRepository.getFrame(selectedFrameId).then((frame) => {
      setReviewFrame(frame);
      
      // 更新尺寸
      if (frame?.meta.imageRef) {
        setDimensions({
          width: frame.meta.imageRef.width || 640,
          height: frame.meta.imageRef.height || 480,
        });
      }
    });
  }, [isReviewMode, selectedFrameId]);

  // 回看模式：渲染历史帧到Canvas
  useEffect(() => {
    if (!isReviewMode || !reviewFrame || !canvasRef.current) {
      return;
    }
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;
    
    // 使用createImageBitmap高效解码
    createImageBitmap(reviewFrame.blob).then((bitmap) => {
      ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close();
    }).catch((e) => {
      console.error('回看帧解码错误:', e);
    });
  }, [isReviewMode, reviewFrame]);

  // 初始化Canvas上下文 - 当Canvas挂载或尺寸变化时
  useEffect(() => {
    if (canvasRef.current) {
      ctxRef.current = canvasRef.current.getContext('2d', {
        alpha: false,           // 禁用透明度，提升性能
        desynchronized: true,   // 允许异步渲染
      });
    }
  }, [dimensions]); // 当尺寸变化时重新获取上下文

  // 渲染循环（仅实时模式）
  useEffect(() => {
    // 回看模式不启动渲染循环
    if (isReviewMode) {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = 0;
      }
      return;
    }
    
    if (state !== 'running') {
      // 非运行状态，停止渲染循环
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = 0;
      }
      return;
    }

    // 确保Canvas上下文已初始化
    if (canvasRef.current && !ctxRef.current) {
      ctxRef.current = canvasRef.current.getContext('2d', {
        alpha: false,
        desynchronized: true,
      });
    }

    const render = async () => {
      const frame = frameBuffer.getPlayableFrame();
      if (frame && ctxRef.current && canvasRef.current) {
        try {
          // 检查是否为Object URL
          const isObjectUrl = frame.image.startsWith('blob:');
          
          if (isObjectUrl) {
            // Object URL：使用fetch + createImageBitmap确保同步渲染
            const response = await fetch(frame.image);
            const blob = await response.blob();
            const bitmap = await createImageBitmap(blob);
            
            if (ctxRef.current && canvasRef.current) {
              ctxRef.current.drawImage(bitmap, 0, 0, canvasRef.current.width, canvasRef.current.height);
            }
            bitmap.close();
            // 释放Object URL
            URL.revokeObjectURL(frame.image);
          } else {
            // Base64：使用createImageBitmap高效解码
            const binary = atob(frame.image);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
              bytes[i] = binary.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: 'image/jpeg' });
            const bitmap = await createImageBitmap(blob);
            
            if (ctxRef.current && canvasRef.current) {
              ctxRef.current.drawImage(bitmap, 0, 0, canvasRef.current.width, canvasRef.current.height);
            }
            bitmap.close();
          }
        } catch (e) {
          console.error('Frame decode error:', e);
        }
      }
      rafIdRef.current = requestAnimationFrame(render);
    };

    rafIdRef.current = requestAnimationFrame(render);
    
    return () => {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = 0;
      }
      frameBuffer.clear();
    };
  }, [state, isReviewMode]);

  // 对摄像头源处理实时视频流
  useEffect(() => {
    if (!videoRef.current || !sourceInfo || sourceInfo.source_type !== 'camera') {
      return;
    }

    const video = videoRef.current;
    
    // 获取摄像头流
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        video.srcObject = stream;
      })
      .catch(err => {
        console.error('无法访问摄像头:', err);
      });

    // 返回清理函数
    return () => {
      // 清理摄像头流
      if (video.srcObject) {
        const tracks = (video.srcObject as MediaStream).getTracks();
        tracks.forEach(track => track.stop());
      }
    };
  }, [sourceInfo]);

  // 无视觉源时的占位界面
  if (!sourceInfo) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-bg-tertiary rounded-lg">
        <div className="w-20 h-20 bg-bg-elevated rounded-full flex items-center justify-center mb-4">
          <Video className="w-10 h-10 text-gray-600" />
        </div>
        <p className="text-gray-400 text-lg">请选择视觉源</p>
        <p className="text-gray-500 text-sm mt-2">支持图像、视频文件或摄像头</p>
      </div>
    );
  }

  // 摄像头源：始终显示实时画面
  if (sourceInfo.source_type === 'camera') {
    return (
      <div className="w-full h-full flex items-center justify-center bg-black rounded-lg overflow-hidden">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="max-w-full max-h-full object-contain"
        />
      </div>
    );
  }

  // 图片/视频源：Canvas始终存在，根据状态显示不同内容
  const isRunning = state === 'running';
  const showCanvas = isRunning || isReviewMode;
  const showStaticFrame = !isRunning && !isReviewMode && staticFrame;
  const showPlaceholder = !isRunning && !isReviewMode && !staticFrame;

  return (
    <div className="w-full h-full flex items-center justify-center bg-black rounded-lg overflow-hidden relative">
      {/* Canvas：运行时或回看时显示 */}
      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        className={`max-w-full max-h-full object-contain ${showCanvas ? '' : 'hidden'}`}
      />
      
      {/* 非运行状态且非回看：显示静态帧 */}
      {showStaticFrame && (
        <img
          src={staticFrame.startsWith('blob:') ? staticFrame : `data:image/jpeg;base64,${staticFrame}`}
          alt="预览帧"
          className="max-w-full max-h-full object-contain"
        />
      )}
      
      {/* 等待帧数据的占位符 */}
      {showPlaceholder && (
        <div className="flex flex-col items-center justify-center bg-bg-tertiary rounded-lg absolute inset-0">
          <div className="w-20 h-20 bg-bg-elevated rounded-full flex items-center justify-center mb-4">
            <Video className={`w-10 h-10 ${sourceInfo.source_type === 'image' ? 'text-blue-500' : 'text-green-500'}`} />
          </div>
          <p className="text-gray-300 text-lg">
            {getSourceTypeLabel(sourceInfo.source_type)}已就绪
          </p>
          <p className="text-gray-500 text-sm mt-2">点击启动开始处理</p>
        </div>
      )}
      
      {/* 回看模式指示器 */}
      {isReviewMode && (
        <div className="absolute top-2 left-2 px-2 py-1 bg-blue-600/80 rounded text-xs text-white">
          回看模式
        </div>
      )}
    </div>
  );
}
