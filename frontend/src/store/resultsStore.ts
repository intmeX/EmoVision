// 结果展示与导出状态管理
// 支持多会话管理：stop/restart 不清空历史，切换视觉源时才清空

import { create } from 'zustand';
import type {
  SourceInfo,
  ResultsSessionSummary,
  FrameIndex,
  ReviewMode,
  ExportState,
  RecordingPolicy,
  StoredFrameMeta,
} from '../types';

// 生成唯一会话ID
export function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * 单个会话的数据
 */
interface SessionData {
  sessionId: string;
  summary: ResultsSessionSummary;
  index: FrameIndex;
  /** 每帧的情绪数据（用于时间轴可视化和统计） */
  frameEmotions: Map<number, { 
    dominant: string | null;  // 帧中最主要的情绪（用于时间轴染色）
    emotions: Array<{ emotion: string; confidence: number }>;  // 所有检测目标的情绪（用于统计）
  }>;
}

interface ResultsStore {
  // === 多会话管理 ===
  /** 所有会话列表（按时间顺序） */
  sessions: SessionData[];
  /** 当前活跃会话ID（正在录制或查看的） */
  activeSessionId: string | null;

  // === 当前会话状态（快捷访问） ===
  /** 是否正在录制 */
  isRecording: boolean;

  // === 回看状态 ===
  /** 当前选中的帧ID */
  selectedFrameId: number | null;
  /** 回看模式 */
  reviewMode: ReviewMode;

  // === 时间轴状态 ===
  timeline: {
    isDragging: boolean;
    hoverFrameId: number | null;
  };

  // === 导出状态 ===
  exportState: ExportState;

  // === 录制策略 ===
  recordingPolicy: RecordingPolicy;

  // === Actions ===
  actions: {
    /** 开始新会话（返回sessionId供外部使用） */
    startSession: (sourceInfo: SourceInfo | null) => string;
    /** 结束当前会话（不清空，保留历史） */
    endCurrentSession: () => void;
    /** 标记会话结束（EOS） */
    markEnded: () => void;
    /** 暂停进入回看 */
    enterPausedReview: () => void;
    /** 恢复实时模式 */
    resumeLive: () => void;
    /** 选择帧 */
    selectFrame: (frameId: number) => void;
    /** 选择上一帧 */
    prevFrame: () => void;
    /** 选择下一帧 */
    nextFrame: () => void;
    /** 设置回看模式 */
    setReviewMode: (mode: ReviewMode) => void;
    /** 添加帧到索引（带去重） */
    addFrameToIndex: (frameId: number, timestamp: number, emotions?: StoredFrameMeta['emotions']) => void;
    /** 更新录制帧数 */
    incrementRecordedFrames: () => void;
    /** 更新丢弃帧数 */
    incrementDroppedFrames: () => void;
    /** 设置时间轴拖动状态 */
    setTimelineDragging: (isDragging: boolean) => void;
    /** 设置时间轴悬停帧 */
    setTimelineHoverFrame: (frameId: number | null) => void;
    /** 更新导出状态 */
    setExportState: (state: Partial<ExportState>) => void;
    /** 更新录制策略 */
    setRecordingPolicy: (policy: Partial<RecordingPolicy>) => void;
    /** 切换到指定会话（用于查看历史） */
    switchToSession: (sessionId: string) => void;
    /** 清空所有会话（切换视觉源时调用） */
    clearAllSessions: () => void;
    /** 获取当前活跃会话数据 */
    getActiveSession: () => SessionData | null;
    /** 兼容旧API：停止并清空（现在只结束会话，不清空） */
    stopAndClear: () => void;
  };
}

const initialExportState: ExportState = {
  json: { state: 'idle' },
  video: { state: 'idle', progress: 0 },
};

const initialIndex: FrameIndex = {
  frameIds: [],
  timestamps: [],
  keyframeEvery: 30,
};

const defaultRecordingPolicy: RecordingPolicy = {
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
    persistToIndexedDB: true,
    storeFullImage: true,
    storeThumbnail: false,
  },
};

export const useResultsStore = create<ResultsStore>((set, get) => ({
  // 初始状态
  sessions: [],
  activeSessionId: null,
  isRecording: false,
  selectedFrameId: null,
  reviewMode: 'live',
  timeline: {
    isDragging: false,
    hoverFrameId: null,
  },
  exportState: { ...initialExportState },
  recordingPolicy: { ...defaultRecordingPolicy },

  actions: {
    startSession: (sourceInfo) => {
      const sessionId = generateSessionId();
      const newSession: SessionData = {
        sessionId,
        summary: {
          sessionId,
          startedAt: Date.now(),
          sourceInfo,
          totalFramesRecorded: 0,
          droppedFrames: 0,
        },
        index: { ...initialIndex },
        frameEmotions: new Map(),
      };

      set((state) => ({
        sessions: [...state.sessions, newSession],
        activeSessionId: sessionId,
        isRecording: true,
        reviewMode: 'live',
        selectedFrameId: null,
        exportState: { ...initialExportState },
      }));

      return sessionId;
    },

    endCurrentSession: () => {
      const { activeSessionId, sessions } = get();
      if (!activeSessionId) return;

      // 更新会话结束时间
      const updatedSessions = sessions.map((s) =>
        s.sessionId === activeSessionId
          ? { ...s, summary: { ...s.summary, endedAt: Date.now() } }
          : s
      );

      set({
        sessions: updatedSessions,
        isRecording: false,
        // 保持在当前会话，进入回看模式
        reviewMode: 'ended_review',
      });
    },

    // 兼容旧API
    stopAndClear: () => {
      get().actions.endCurrentSession();
    },

    markEnded: () => {
      const { activeSessionId, sessions } = get();
      if (!activeSessionId) return;

      const session = sessions.find((s) => s.sessionId === activeSessionId);
      if (!session) return;

      // 更新会话结束时间
      const updatedSessions = sessions.map((s) =>
        s.sessionId === activeSessionId
          ? { ...s, summary: { ...s.summary, endedAt: Date.now() } }
          : s
      );

      set({
        sessions: updatedSessions,
        isRecording: false,
        reviewMode: 'ended_review',
        // 自动选中最后一帧
        selectedFrameId:
          session.index.frameIds.length > 0
            ? session.index.frameIds[session.index.frameIds.length - 1]
            : null,
      });
    },

    enterPausedReview: () => {
      const { activeSessionId, sessions, isRecording } = get();
      if (!isRecording || !activeSessionId) return;

      const session = sessions.find((s) => s.sessionId === activeSessionId);
      if (!session) return;

      set({
        reviewMode: 'paused_review',
        // 自动选中最后一帧
        selectedFrameId:
          session.index.frameIds.length > 0
            ? session.index.frameIds[session.index.frameIds.length - 1]
            : null,
      });
    },

    resumeLive: () => {
      set({
        reviewMode: 'live',
        selectedFrameId: null,
      });
    },

    selectFrame: (frameId) => {
      const { activeSessionId, sessions } = get();
      if (!activeSessionId) return;

      const session = sessions.find((s) => s.sessionId === activeSessionId);
      if (session && session.index.frameIds.includes(frameId)) {
        set({ selectedFrameId: frameId });
      }
    },

    prevFrame: () => {
      const { activeSessionId, sessions, selectedFrameId } = get();
      if (!activeSessionId || selectedFrameId === null) return;

      const session = sessions.find((s) => s.sessionId === activeSessionId);
      if (!session || session.index.frameIds.length === 0) return;

      const currentIndex = session.index.frameIds.indexOf(selectedFrameId);
      if (currentIndex > 0) {
        set({ selectedFrameId: session.index.frameIds[currentIndex - 1] });
      }
    },

    nextFrame: () => {
      const { activeSessionId, sessions, selectedFrameId } = get();
      if (!activeSessionId || selectedFrameId === null) return;

      const session = sessions.find((s) => s.sessionId === activeSessionId);
      if (!session || session.index.frameIds.length === 0) return;

      const currentIndex = session.index.frameIds.indexOf(selectedFrameId);
      if (currentIndex < session.index.frameIds.length - 1) {
        set({ selectedFrameId: session.index.frameIds[currentIndex + 1] });
      }
    },

    setReviewMode: (mode) => set({ reviewMode: mode }),

    addFrameToIndex: (frameId, timestamp, emotions) => {
      const { activeSessionId } = get();
      if (!activeSessionId) return;

      set((state) => {
        const sessionIndex = state.sessions.findIndex(
          (s) => s.sessionId === activeSessionId
        );
        if (sessionIndex === -1) return state;

        const session = state.sessions[sessionIndex];

        // 去重检查
        if (session.index.frameIds.includes(frameId)) {
          return state;
        }

        // 计算帧中最主要的情绪（用于时间轴染色）
        // 统计所有检测目标的情绪，选择出现次数最多的
        const emotionCounts: Record<string, number> = {};
        const allEmotions: Array<{ emotion: string; confidence: number }> = [];
        
        if (emotions && emotions.length > 0) {
          for (const e of emotions) {
            const emotion = e.dominant_emotion;
            emotionCounts[emotion] = (emotionCounts[emotion] || 0) + 1;
            allEmotions.push({ emotion, confidence: e.confidence });
          }
        }
        
        // 找出出现次数最多的情绪
        let dominant: string | null = null;
        let maxCount = 0;
        for (const [emotion, count] of Object.entries(emotionCounts)) {
          if (count > maxCount) {
            maxCount = count;
            dominant = emotion;
          }
        }

        // 创建新的 frameEmotions Map
        const newFrameEmotions = new Map(session.frameEmotions);
        newFrameEmotions.set(frameId, { dominant, emotions: allEmotions });

        const updatedSession: SessionData = {
          ...session,
          index: {
            ...session.index,
            frameIds: [...session.index.frameIds, frameId],
            timestamps: [...session.index.timestamps, timestamp],
          },
          frameEmotions: newFrameEmotions,
        };

        const newSessions = [...state.sessions];
        newSessions[sessionIndex] = updatedSession;

        return { sessions: newSessions };
      });
    },

    incrementRecordedFrames: () => {
      const { activeSessionId } = get();
      if (!activeSessionId) return;

      set((state) => {
        const sessionIndex = state.sessions.findIndex(
          (s) => s.sessionId === activeSessionId
        );
        if (sessionIndex === -1) return state;

        const session = state.sessions[sessionIndex];
        const updatedSession: SessionData = {
          ...session,
          summary: {
            ...session.summary,
            totalFramesRecorded: session.summary.totalFramesRecorded + 1,
          },
        };

        const newSessions = [...state.sessions];
        newSessions[sessionIndex] = updatedSession;

        return { sessions: newSessions };
      });
    },

    incrementDroppedFrames: () => {
      const { activeSessionId } = get();
      if (!activeSessionId) return;

      set((state) => {
        const sessionIndex = state.sessions.findIndex(
          (s) => s.sessionId === activeSessionId
        );
        if (sessionIndex === -1) return state;

        const session = state.sessions[sessionIndex];
        const updatedSession: SessionData = {
          ...session,
          summary: {
            ...session.summary,
            droppedFrames: session.summary.droppedFrames + 1,
          },
        };

        const newSessions = [...state.sessions];
        newSessions[sessionIndex] = updatedSession;

        return { sessions: newSessions };
      });
    },

    setTimelineDragging: (isDragging) => {
      set((state) => ({
        timeline: { ...state.timeline, isDragging },
      }));
    },

    setTimelineHoverFrame: (frameId) => {
      set((state) => ({
        timeline: { ...state.timeline, hoverFrameId: frameId },
      }));
    },

    setExportState: (newState) => {
      set((state) => ({
        exportState: {
          json: { ...state.exportState.json, ...newState.json },
          video: { ...state.exportState.video, ...newState.video },
        },
      }));
    },

    setRecordingPolicy: (policy) => {
      set((state) => ({
        recordingPolicy: { ...state.recordingPolicy, ...policy },
      }));
    },

    switchToSession: (sessionId) => {
      const { sessions } = get();
      const session = sessions.find((s) => s.sessionId === sessionId);
      if (!session) return;

      set({
        activeSessionId: sessionId,
        isRecording: false,
        reviewMode: 'ended_review',
        selectedFrameId:
          session.index.frameIds.length > 0
            ? session.index.frameIds[session.index.frameIds.length - 1]
            : null,
        exportState: { ...initialExportState },
      });
    },

    clearAllSessions: () => {
      set({
        sessions: [],
        activeSessionId: null,
        isRecording: false,
        reviewMode: 'live',
        selectedFrameId: null,
        timeline: {
          isDragging: false,
          hoverFrameId: null,
        },
        exportState: { ...initialExportState },
      });
    },

    getActiveSession: () => {
      const { activeSessionId, sessions } = get();
      if (!activeSessionId) return null;
      return sessions.find((s) => s.sessionId === activeSessionId) ?? null;
    },
  },
}));

// === 便捷选择器 ===

export const useResultsActions = () => useResultsStore((state) => state.actions);
export const useReviewMode = () => useResultsStore((state) => state.reviewMode);
export const useSelectedFrameId = () => useResultsStore((state) => state.selectedFrameId);
export const useIsRecording = () => useResultsStore((state) => state.isRecording);
export const useExportState = () => useResultsStore((state) => state.exportState);
export const useSessions = () => useResultsStore((state) => state.sessions);
export const useActiveSessionId = () => useResultsStore((state) => state.activeSessionId);

// 获取当前活跃会话的帧索引
export const useFrameIndex = () =>
  useResultsStore((state) => {
    const session = state.sessions.find((s) => s.sessionId === state.activeSessionId);
    return session?.index ?? { frameIds: [], timestamps: [], keyframeEvery: 30 };
  });

// 获取当前活跃会话的摘要
export const useResultsSummary = () =>
  useResultsStore((state) => {
    const session = state.sessions.find((s) => s.sessionId === state.activeSessionId);
    return session?.summary ?? null;
  });

// 获取当前活跃会话的帧情绪数据
export const useFrameEmotions = () =>
  useResultsStore((state) => {
    const session = state.sessions.find((s) => s.sessionId === state.activeSessionId);
    return session?.frameEmotions ?? new Map();
  });

// 兼容旧API：sessionId
export const useSessionId = () => useResultsStore((state) => state.activeSessionId);
