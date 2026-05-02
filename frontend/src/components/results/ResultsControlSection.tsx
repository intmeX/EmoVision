/**
 * 结果控制区组件
 *
 * 嵌入侧边栏，显示录制状态、会话列表、帧信息和导出按钮
 */

import { useState } from 'react';
import { FileJson, Film, Circle, Clock, ChevronRight, Eye, ChevronDown, ChevronUp } from 'lucide-react';
import {
  useResultsStore,
  usePipelineStore,
  useSessions,
  useActiveSessionId,
  useFrameIndex,
  useConfigStore,
} from '@/store';
import { historyRepository } from '@/services/historyRepository';
import { exportService } from '@/services/exportService';
import type { ResultsSessionSummary } from '@/types';

// ─── 颜色映射 ───────────────────────────────────────────────

const EMOTION_COLORS: Record<string, string> = {
  '开心': '#22c55e',
  '悲伤': '#3b82f6',
  '愤怒': '#ef4444',
  '恐惧': '#a855f7',
  '惊讶': '#f59e0b',
  '厌恶': '#84cc16',
  '中性': '#6b7280',
};

const CONTEXT_COLORS: Record<string, string> = {
  '背景': '#3b82f6',
  '身体': '#f59e0b',
  '人脸': '#ec4899',
  '场景语义': '#10b981',
};

function getEmotionColor(emotion: string): string {
  return EMOTION_COLORS[emotion] ?? '#6b7280';
}

// ─── 工具函数 ─────────────────────────────────────────────────


function formatDateTime(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// ─── SessionListItem ─────────────────────────────────────────

function SessionListItem({
  sessionId,
  summary,
  frameCount,
  isActive,
  onClick,
}: {
  sessionId: string;
  summary: ResultsSessionSummary | undefined;
  frameCount: number;
  isActive: boolean;
  onClick: () => void;
}) {
  const startTime = summary?.startedAt ? formatDateTime(summary.startedAt) : sessionId.slice(0, 8);
  const sourceName = summary?.sourceInfo?.path?.split(/[\/\\]/).pop() ?? '未知源';

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-2 rounded-lg transition-colors ${
        isActive ? 'bg-accent-primary/20 border border-accent-primary/40' : 'hover:bg-bg-tertiary border border-transparent'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3 h-3 text-gray-500" />
          <span className="text-xs text-gray-400">{startTime}</span>
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

// ─── FrameEmotionContent ──────────────────────────────────

function FrameEmotionContent({
  frameId,
  displayCount,
}: {
  frameId: number;
  displayCount: number;
}) {
  const meta = historyRepository.getFrameMeta(frameId);
  const faceDetections = meta ? meta.detections.filter((d) => d.type === 'face') : [];

  if (!meta || faceDetections.length === 0) {
    return (
      <div className="px-3 pb-3 text-sm text-gray-500 text-center">无人脸检测数据</div>
    );
  }

  return (
    <div className="px-3 pb-3 space-y-3">
      {faceDetections.map((det, idx) => {
        const emotion = meta.emotions.find((e) => e.detection_id === det.id);
        const topEmotions = emotion
          ? Object.entries(emotion.probabilities)
              .sort((a, b) => b[1] - a[1])
              .slice(0, displayCount)
          : [];
        const attention = emotion?.context_attention
          ? Object.entries(emotion.context_attention).sort((a, b) => b[1] - a[1])
          : [];
        return (
          <div key={det.id} className="bg-bg-secondary rounded-lg p-2.5">
            {/* 人脸序号 */}
            <div className="flex items-center gap-2 mb-2">
              <span
                className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-black"
                style={{ backgroundColor: '#e5e7eb' }}
              >
                {idx + 1}
              </span>
              {emotion ? (
                <span className="text-xs text-gray-300">
                  {emotion.dominant_emotion}
                  <span className="text-gray-500 ml-1">
                    ({(emotion.confidence * 100).toFixed(0)}%)
                  </span>
                </span>
              ) : (
                <span className="text-xs text-gray-500">无情绪数据</span>
              )}
            </div>
            {/* 情绪进度条 */}
            {topEmotions.length > 0 && (
              <div className="space-y-1">
                {topEmotions.map(([label, prob]) => (
                  <div key={label} className="space-y-0.5">
                    <div className="flex items-center justify-between text-xs">
                      <span style={{ color: getEmotionColor(label) }}>{label}</span>
                      <span className="text-gray-400">{(prob * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1.5 bg-gray-700 rounded overflow-hidden">
                      <div
                        className="h-full rounded"
                        style={{ width: `${prob * 100}%`, backgroundColor: getEmotionColor(label) }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
            {/* 注意力分数 */}
            {attention.length > 0 && (
              <div className="mt-2 pt-2 border-t border-border-primary space-y-1">
                <div className="text-xs text-gray-500 mb-1">上下文注意力</div>
                {attention.map(([label, value]) => (
                  <div key={label} className="space-y-0.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">{label}</span>
                      <span className="text-gray-300">{(value * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1.5 bg-gray-700 rounded overflow-hidden">
                      <div
                        className="h-full rounded transition-all"
                        style={{ width: `${value * 100}%`, backgroundColor: CONTEXT_COLORS[label] ?? '#6b7280' }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── ResultsControlSection (主组件) ──────────────────────────

export function ResultsControlSection() {
  const { reviewMode, selectedFrameId, exportState, actions } = useResultsStore();
  const sessions = useSessions();
  const activeSessionId = useActiveSessionId();
  const index = useFrameIndex();
  const pipelineState = usePipelineStore((state) => state.state);
  const displayCount = useConfigStore((s) => s.config.visualizer.emotion_display_count);
  const [showEmotionModal, setShowEmotionModal] = useState(false);

  // 获取当前会话摘要
  const activeSession = sessions.find((s) => s.sessionId === activeSessionId);
  const summary = activeSession?.summary;

  // ── 运行时：显示录制状态 ──
  if (pipelineState === 'running' && reviewMode === 'live') {
    return (
      <div className="space-y-3">
        <div className="p-3 bg-bg-tertiary rounded-lg">
          <div className="flex items-center gap-2">
            <Circle className="w-2 h-2 fill-red-500 text-red-500 animate-pulse" />
            <span className="text-sm text-gray-300">录制中</span>
            <span className="text-sm text-gray-500 ml-auto">
              {summary?.totalFramesRecorded ?? 0} 帧
            </span>
          </div>
        </div>

        {sessions.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500">历史记录</div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {sessions
                .slice()
                .reverse()
                .map((session) => (
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

  // ── 回看时：显示帧信息和导出按钮 ──
  if (reviewMode === 'paused_review' || reviewMode === 'ended_review') {
    const isExporting =
      exportState.json.state === 'building' || exportState.video.state === 'encoding';

    return (
      <div className="space-y-3">
        {/* 会话列表 */}
        {sessions.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500">历史记录</div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {sessions
                .slice()
                .reverse()
                .map((session) => (
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

        {/* 查看当前帧情绪按钮（展开/收起） */}
        <div className="bg-bg-tertiary rounded-lg space-y-0">
          <button
            onClick={() => setShowEmotionModal((v) => !v)}
            disabled={selectedFrameId === null}
            className="w-full flex items-center justify-between gap-2 px-3 py-2 text-sm hover:bg-bg-secondary disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors text-gray-300"
          >
            <div className="flex items-center gap-2">
              <Eye className="w-4 h-4" />
              <span>查看当前帧情绪</span>
            </div>
            {showEmotionModal ? (
              <ChevronUp className="w-3 h-3 text-gray-500" />
            ) : (
              <ChevronDown className="w-3 h-3 text-gray-500" />
            )}
          </button>

          {/* 内联展开的情绪内容 */}
          {showEmotionModal && selectedFrameId !== null && (
            <FrameEmotionContent
              frameId={selectedFrameId}
              displayCount={displayCount}
            />
          )}
        </div>

        <div className="p-3 bg-bg-tertiary rounded-lg space-y-3">
          <div className="border-t border-border-primary" />

          <div className="text-xs text-gray-500">共 {index.frameIds.length} 帧已录制</div>

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
                <span className="text-gray-300">
                  {Math.round(exportState.video.progress * 100)}%
                </span>
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

  // ── idle 状态 ──
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
      <div className="space-y-2">
        <div className="text-xs text-gray-500">历史记录</div>
        <div className="space-y-1 max-h-60 overflow-y-auto">
          {sessions
            .slice()
            .reverse()
            .map((session) => (
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
