/**
 * 结果控制区组件
 * 
 * 嵌入侧边栏，显示录制状态、会话列表、帧信息和导出按钮
 */

import { FileJson, Film, Circle, Clock, ChevronRight } from 'lucide-react';
import { useResultsStore, usePipelineStore, useSessions, useActiveSessionId, useFrameIndex } from '@/store';
import { historyRepository } from '@/services/historyRepository';
import { exportService } from '@/services/exportService';
import type { ResultsSessionSummary } from '@/types';

/**
 * 格式化时间戳
 */
function formatTime(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  const remainingMs = Math.floor(ms % 1000);
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}.${remainingMs.toString().padStart(3, '0')}`;
}

/**
 * 格式化日期时间
 */
function formatDateTime(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

/**
 * 帧信息显示组件
 */
function FrameInfoDisplay({ frameId }: { frameId: number | null }) {
  if (frameId === null) {
    return (
      <div className="text-sm text-gray-500">
        未选择帧
      </div>
    );
  }
  
  const meta = historyRepository.getFrameMeta(frameId);
  
  if (!meta) {
    return (
      <div className="text-sm text-gray-500">
        帧数据不可用
      </div>
    );
  }
  
  // 获取主情绪
  const dominantEmotion = meta.emotions.length > 0
    ? meta.emotions.reduce((max, e) => e.confidence > max.confidence ? e : max, meta.emotions[0])
    : null;
  
  return (
    <div className="space-y-1 text-sm">
      <div className="flex justify-between">
        <span className="text-gray-500">帧 ID</span>
        <span className="text-gray-300">#{meta.frameId}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-500">时间</span>
        <span className="text-gray-300">{formatTime(meta.timestamp)}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-500">检测</span>
        <span className="text-gray-300">{meta.detections.length} 个目标</span>
      </div>
      {dominantEmotion && (
        <div className="flex justify-between">
          <span className="text-gray-500">主情绪</span>
          <span className="text-gray-300">
            {dominantEmotion.dominant_emotion} ({(dominantEmotion.confidence * 100).toFixed(0)}%)
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * 会话列表项
 */
function SessionListItem({ 
  sessionId: _sessionId,
  summary, 
  frameCount,
  isActive,
  onClick 
}: { 
  sessionId: string;
  summary: ResultsSessionSummary;
  frameCount: number;
  isActive: boolean;
  onClick: () => void;
}) {
  // sessionId is used as key in parent, kept in props for consistency
  void _sessionId;
  const sourceName = summary.sourceInfo?.path?.split(/[/\\]/).pop() ?? '未知源';
  
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-2 rounded transition-colors ${
        isActive 
          ? 'bg-blue-600/20 border border-blue-500/50' 
          : 'bg-bg-elevated hover:bg-bg-secondary'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <Clock className="w-3 h-3 text-gray-500 flex-shrink-0" />
          <span className="text-xs text-gray-400 truncate">
            {formatDateTime(summary.startedAt)}
          </span>
        </div>
        <ChevronRight className={`w-3 h-3 flex-shrink-0 ${isActive ? 'text-blue-400' : 'text-gray-600'}`} />
      </div>
      <div className="mt-1 flex items-center justify-between">
        <span className="text-sm text-gray-300 truncate" title={sourceName}>
          {sourceName}
        </span>
        <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
          {frameCount} 帧
        </span>
      </div>
    </button>
  );
}

/**
 * 结果控制区主组件
 */
export function ResultsControlSection() {
  const { reviewMode, selectedFrameId, exportState, actions } = useResultsStore();
  const sessions = useSessions();
  const activeSessionId = useActiveSessionId();
  const index = useFrameIndex();
  const pipelineState = usePipelineStore((state) => state.state);
  
  // 获取当前会话摘要
  const activeSession = sessions.find(s => s.sessionId === activeSessionId);
  const summary = activeSession?.summary;
  
  // 运行时：显示录制状态
  if (pipelineState === 'running' && reviewMode === 'live') {
    return (
      <div className="space-y-3">
        {/* 录制状态 */}
        <div className="p-3 bg-bg-tertiary rounded-lg">
          <div className="flex items-center gap-2">
            <Circle className="w-2 h-2 fill-red-500 text-red-500 animate-pulse" />
            <span className="text-sm text-gray-300">
              录制中
            </span>
            <span className="text-sm text-gray-500 ml-auto">
              {summary?.totalFramesRecorded ?? 0} 帧
            </span>
          </div>
          {summary && summary.droppedFrames > 0 && (
            <div className="mt-1 text-xs text-yellow-500">
              已跳过 {summary.droppedFrames} 帧
            </div>
          )}
        </div>
        
        {/* 历史会话列表（如果有） */}
        {sessions.length > 1 && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500">历史记录</div>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {sessions
                .filter(s => s.sessionId !== activeSessionId)
                .slice(-3)
                .reverse()
                .map(session => (
                  <SessionListItem
                    key={session.sessionId}
                    sessionId={session.sessionId}
                    summary={session.summary}
                    frameCount={session.index.frameIds.length}
                    isActive={false}
                    onClick={() => actions.switchToSession(session.sessionId)}
                  />
                ))}
            </div>
          </div>
        )}
      </div>
    );
  }
  
  // 回看时：显示帧信息和导出按钮
  if (reviewMode === 'paused_review' || reviewMode === 'ended_review') {
    const isExporting = exportState.json.state === 'building' || exportState.video.state === 'encoding';
    
    return (
      <div className="space-y-3">
        {/* 会话列表 */}
        {sessions.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500">会话记录</div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {sessions.slice().reverse().map(session => (
                <SessionListItem
                  key={session.sessionId}
                  sessionId={session.sessionId}
                  summary={session.summary}
                  frameCount={session.index.frameIds.length}
                  isActive={session.sessionId === activeSessionId}
                  onClick={() => actions.switchToSession(session.sessionId)}
                />
              ))}
            </div>
          </div>
        )}
        
        {/* 当前帧信息 */}
        <div className="p-3 bg-bg-tertiary rounded-lg space-y-3">
          <FrameInfoDisplay frameId={selectedFrameId} />
          
          {/* 分隔线 */}
          <div className="border-t border-border-primary" />
          
          {/* 统计信息 */}
          <div className="text-xs text-gray-500">
            共 {index.frameIds.length} 帧已录制
          </div>
          
          {/* 导出按钮 */}
          <div className="flex gap-2">
            <button
              onClick={() => {
                exportService.downloadJson().catch((e) => {
                  console.error('JSON导出失败:', e);
                });
              }}
              disabled={isExporting || index.frameIds.length === 0}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
            >
              <FileJson className="w-4 h-4" />
              <span>JSON</span>
            </button>
            <button
              onClick={() => {
                exportService.downloadVideo().catch((e) => {
                  console.error('视频导出失败:', e);
                });
              }}
              disabled={isExporting || index.frameIds.length === 0}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
            >
              <Film className="w-4 h-4" />
              <span>视频</span>
            </button>
          </div>
          
          {/* 导出进度 */}
          {exportState.video.state === 'encoding' && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">导出进度</span>
                <span className="text-gray-300">{Math.round(exportState.video.progress * 100)}%</span>
              </div>
              <div className="h-1 bg-gray-700 rounded overflow-hidden">
                <div 
                  className="h-full bg-green-500 transition-all duration-300"
                  style={{ width: `${exportState.video.progress * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }
  
  // idle 状态
  if (sessions.length === 0) {
    return (
      <div className="p-3 bg-bg-tertiary rounded-lg text-center text-gray-500 text-sm">
        暂无记录
      </div>
    );
  }
  
  // idle 但有历史记录（可以回看）
  return (
    <div className="space-y-3">
      {/* 会话列表 */}
      <div className="space-y-2">
        <div className="text-xs text-gray-500">历史记录</div>
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {sessions.slice().reverse().map(session => (
            <SessionListItem
              key={session.sessionId}
              sessionId={session.sessionId}
              summary={session.summary}
              frameCount={session.index.frameIds.length}
              isActive={session.sessionId === activeSessionId}
              onClick={() => actions.switchToSession(session.sessionId)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
