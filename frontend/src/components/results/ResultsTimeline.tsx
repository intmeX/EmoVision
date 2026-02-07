/**
 * 结果时间轴组件
 * 
 * 显示在视频区下方，用于回看时的帧导航
 * 支持情绪颜色可视化
 */

import { useCallback, useRef, useState, useEffect, useMemo } from 'react';
import { 
  SkipBack, 
  SkipForward, 
  ChevronLeft, 
  ChevronRight,
  Play,
  Pause,
} from 'lucide-react';
import { useResultsStore, useFrameIndex, useFrameEmotions } from '@/store';

/**
 * 情绪颜色映射
 */
const EMOTION_COLORS: Record<string, string> = {
  happy: '#22c55e',      // green-500
  sad: '#3b82f6',        // blue-500
  angry: '#ef4444',      // red-500
  fear: '#a855f7',       // purple-500
  surprise: '#f59e0b',   // amber-500
  disgust: '#84cc16',    // lime-500
  neutral: '#6b7280',    // gray-500
  contempt: '#f97316',   // orange-500
};

/**
 * 获取情绪颜色
 */
function getEmotionColor(emotion: string | null): string {
  if (!emotion) return '#374151'; // gray-700
  return EMOTION_COLORS[emotion.toLowerCase()] ?? '#374151';
}

/**
 * 格式化时间戳为 mm:ss.ms 格式
 */
function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const milliseconds = Math.floor((ms % 1000) / 10);
  return `${minutes}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(2, '0')}`;
}

/**
 * 结果时间轴组件
 */
export function ResultsTimeline() {
  const { selectedFrameId, timeline, actions } = useResultsStore();
  const index = useFrameIndex();
  const frameEmotions = useFrameEmotions();
  const trackRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const playIntervalRef = useRef<number | null>(null);
  
  // 计算当前进度
  const currentIndex = selectedFrameId !== null 
    ? index.frameIds.indexOf(selectedFrameId) 
    : -1;
  const progress = index.frameIds.length > 1 
    ? Math.max(0, currentIndex) / (index.frameIds.length - 1) 
    : 0;
  
  // 获取当前时间戳（相对于第一帧）
  const firstTimestamp = index.timestamps.length > 0 ? index.timestamps[0] : 0;
  const currentTimestamp = currentIndex >= 0 && currentIndex < index.timestamps.length
    ? index.timestamps[currentIndex] - firstTimestamp
    : 0;
  
  // 获取总时长
  const totalDuration = index.timestamps.length > 0
    ? index.timestamps[index.timestamps.length - 1] - firstTimestamp
    : 0;
  
  // 生成情绪颜色段
  const emotionSegments = useMemo(() => {
    if (index.frameIds.length === 0) return [];
    
    const segments: Array<{ start: number; end: number; color: string }> = [];
    const totalFrames = index.frameIds.length;
    
    for (let i = 0; i < totalFrames; i++) {
      const frameId = index.frameIds[i];
      const emotionData = frameEmotions.get(frameId);
      const color = getEmotionColor(emotionData?.dominant ?? null);
      
      const start = i / totalFrames;
      const end = (i + 1) / totalFrames;
      
      // 合并相邻相同颜色的段
      if (segments.length > 0 && segments[segments.length - 1].color === color) {
        segments[segments.length - 1].end = end;
      } else {
        segments.push({ start, end, color });
      }
    }
    
    return segments;
  }, [index.frameIds, frameEmotions]);
  
  // 处理拖动
  const handleScrub = useCallback((clientX: number) => {
    if (!trackRef.current || index.frameIds.length === 0) return;
    
    const rect = trackRef.current.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const frameIndex = Math.round(ratio * (index.frameIds.length - 1));
    
    if (frameIndex >= 0 && frameIndex < index.frameIds.length) {
      actions.selectFrame(index.frameIds[frameIndex]);
    }
  }, [index, actions]);
  
  // RAF 节流
  const rafRef = useRef<number | null>(null);
  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!timeline.isDragging) return;
    
    if (rafRef.current !== null) return;
    
    rafRef.current = requestAnimationFrame(() => {
      handleScrub(e.clientX);
      rafRef.current = null;
    });
  }, [timeline.isDragging, handleScrub]);
  
  // 播放控制
  const togglePlay = useCallback(() => {
    if (isPlaying) {
      // 停止播放
      if (playIntervalRef.current !== null) {
        clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
      }
      setIsPlaying(false);
    } else {
      // 如果没有选中帧，先选中第一帧
      const state = useResultsStore.getState();
      const session = state.actions.getActiveSession();
      if (!session || session.index.frameIds.length === 0) return;
      
      if (state.selectedFrameId === null) {
        state.actions.selectFrame(session.index.frameIds[0]);
      }
      
      // 开始播放
      setIsPlaying(true);
      playIntervalRef.current = window.setInterval(() => {
        const currentState = useResultsStore.getState();
        const currentSession = currentState.actions.getActiveSession();
        
        if (!currentSession || currentSession.index.frameIds.length === 0) {
          return;
        }
        
        const idx = currentSession.index;
        const selected = currentState.selectedFrameId;
        
        if (selected === null) {
          // 从头开始
          currentState.actions.selectFrame(idx.frameIds[0]);
          return;
        }
        
        const currentIdx = idx.frameIds.indexOf(selected);
        if (currentIdx < idx.frameIds.length - 1) {
          currentState.actions.selectFrame(idx.frameIds[currentIdx + 1]);
        } else {
          // 播放结束，停止
          if (playIntervalRef.current !== null) {
            clearInterval(playIntervalRef.current);
            playIntervalRef.current = null;
          }
          setIsPlaying(false);
        }
      }, 200); // 5fps 播放速度
    }
  }, [isPlaying]);
  
  // 清理播放定时器
  useEffect(() => {
    return () => {
      if (playIntervalRef.current !== null) {
        clearInterval(playIntervalRef.current);
      }
    };
  }, []);
  
  // 如果没有帧，不显示
  if (index.frameIds.length === 0) {
    return null;
  }
  
  const isAtStart = currentIndex <= 0;
  const isAtEnd = currentIndex >= index.frameIds.length - 1;
  
  return (
    <div className="bg-bg-secondary rounded-lg p-3 space-y-2">
      {/* 时间轴轨道 */}
      <div 
        ref={trackRef}
        className="relative h-4 bg-gray-700 rounded cursor-pointer group overflow-hidden"
        onPointerDown={(e) => {
          actions.setTimelineDragging(true);
          e.currentTarget.setPointerCapture(e.pointerId);
          handleScrub(e.clientX);
        }}
        onPointerMove={handlePointerMove}
        onPointerUp={() => actions.setTimelineDragging(false)}
        onPointerCancel={() => actions.setTimelineDragging(false)}
      >
        {/* 情绪颜色段 */}
        {emotionSegments.map((segment, i) => (
          <div
            key={i}
            className="absolute h-full opacity-60"
            style={{
              left: `${segment.start * 100}%`,
              width: `${(segment.end - segment.start) * 100}%`,
              backgroundColor: segment.color,
            }}
          />
        ))}
        
        {/* 播放进度指示器 */}
        <div 
          className="absolute h-full bg-white/20 rounded-l"
          style={{ width: `${progress * 100}%` }}
        />
        
        {/* 当前位置指示线 */}
        <div 
          className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg"
          style={{ left: `${progress * 100}%` }}
        />
        
        {/* 拖动手柄 */}
        <div 
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10"
          style={{ left: `calc(${progress * 100}% - 8px)` }}
        />
      </div>
      
      {/* 控制栏 */}
      <div className="flex items-center justify-between">
        {/* 播放控制按钮 */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => {
              if (index.frameIds.length > 0) {
                actions.selectFrame(index.frameIds[0]);
              }
            }}
            disabled={isAtStart}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-bg-tertiary rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="跳到开头"
          >
            <SkipBack className="w-4 h-4" />
          </button>
          
          <button
            onClick={() => actions.prevFrame()}
            disabled={isAtStart}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-bg-tertiary rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="上一帧"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          
          <button
            onClick={togglePlay}
            disabled={index.frameIds.length === 0}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-bg-tertiary rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title={isPlaying ? '暂停' : '播放'}
          >
            {isPlaying ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>
          
          <button
            onClick={() => actions.nextFrame()}
            disabled={isAtEnd}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-bg-tertiary rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="下一帧"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          
          <button
            onClick={() => {
              if (index.frameIds.length > 0) {
                actions.selectFrame(index.frameIds[index.frameIds.length - 1]);
              }
            }}
            disabled={isAtEnd}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-bg-tertiary rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="跳到结尾"
          >
            <SkipForward className="w-4 h-4" />
          </button>
        </div>
        
        {/* 时间和帧信息 */}
        <div className="flex items-center gap-4 text-sm text-gray-400">
          <span>
            {formatTime(currentTimestamp)} / {formatTime(totalDuration)}
          </span>
          <span>
            帧 {Math.max(0, currentIndex) + 1} / {index.frameIds.length}
          </span>
        </div>
      </div>
      
      {/* 情绪图例 */}
      <div className="flex flex-wrap gap-2 pt-1">
        {Object.entries(EMOTION_COLORS).map(([emotion, color]) => (
          <div key={emotion} className="flex items-center gap-1 text-xs text-gray-500">
            <div 
              className="w-2 h-2 rounded-full" 
              style={{ backgroundColor: color }}
            />
            <span className="capitalize">{emotion}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
