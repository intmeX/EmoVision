/**
 * 帧历史存储库
 *
 * 管理帧历史的内存存储和IndexedDB持久化
 * 使用环形缓冲区限制内存使用，超出限制时溢出到IndexedDB冷存储
 */

import Dexie, { type Table } from 'dexie';

import type {
  StoredFrameMeta,
  HistoryFrameWithImage,
  RecordingPolicy,
  ResultsSessionSummary,
  SourceInfo,
} from '@/types';

// ============================================================================
// IndexedDB Schema Types
// ============================================================================

/**
 * 帧元数据记录（IndexedDB存储格式）
 */
interface FrameMetaRecord {
  /** 复合键: `${sessionId}:${frameId}` */
  key: string;
  /** 帧元数据 */
  meta: StoredFrameMeta;
}

/**
 * 帧图像记录（IndexedDB存储格式）
 */
interface FrameImageRecord {
  /** 复合键: `${sessionId}:${frameId}` */
  key: string;
  /** 图像Blob */
  blob: Blob;
}

/**
 * 会话记录（IndexedDB存储格式）
 */
interface SessionRecord {
  /** 会话ID */
  sessionId: string;
  /** 会话摘要 */
  summary: ResultsSessionSummary;
  /** 冷存储帧ID列表（按时间顺序） */
  coldFrameIds: number[];
}

// ============================================================================
// Dexie Database
// ============================================================================

/**
 * EmoVision历史数据库
 */
class HistoryDatabase extends Dexie {
  framesMeta!: Table<FrameMetaRecord, string>;
  framesImage!: Table<FrameImageRecord, string>;
  sessions!: Table<SessionRecord, string>;

  constructor() {
    super('EmoVisionHistory');
    this.version(1).stores({
      framesMeta: 'key',
      framesImage: 'key',
      sessions: 'sessionId',
    });
  }
}

// ============================================================================
// Memory Frame Type
// ============================================================================

/**
 * 内存中的帧数据
 */
interface MemoryFrame {
  meta: StoredFrameMeta;
  blob: Blob;
}

// ============================================================================
// History Repository
// ============================================================================

/**
 * 帧历史存储库类
 *
 * 提供帧数据的存储、检索和清理功能
 * 热数据存储在内存中，冷数据溢出到IndexedDB
 */
class HistoryRepository {
  /** IndexedDB数据库实例 */
  private db: HistoryDatabase;

  /** 内存存储（环形缓冲区） */
  private memoryFrames: Map<number, MemoryFrame> = new Map();

  /** 帧ID顺序列表（用于LRU淘汰） */
  private frameOrder: number[] = [];

  /** 冷存储帧ID集合（已溢出到IndexedDB的帧） */
  private coldFrameIds: Set<number> = new Set();

  /** 当前会话ID */
  private sessionId: string | null = null;

  /** 当前会话源信息 */
  private sourceInfo: SourceInfo | null = null;

  /** 会话开始时间 */
  private sessionStartedAt: number = 0;

  /** 最大内存帧数 */
  private maxHotFrames: number = 500;

  /** 当前内存使用量（字节） */
  private memoryUsage: number = 0;

  /** 最大内存使用量（字节） */
  private maxMemoryBytes: number = 300 * 1024 * 1024; // 300MB

  /** 是否启用IndexedDB持久化 */
  private persistToIndexedDB: boolean = true;

  /** 待处理的IndexedDB写入队列 */
  private pendingWrites: Promise<void> = Promise.resolve();

  /** 已丢弃帧数（无法存储到IndexedDB时） */
  private droppedFrames: number = 0;

  constructor() {
    this.db = new HistoryDatabase();
  }

  /**
   * 生成IndexedDB复合键
   */
  private makeKey(sessionId: string, frameId: number): string {
    return `${sessionId}:${frameId}`;
  }

  /**
   * 初始化新会话
   */
  startSession(
    sessionId: string,
    policy?: Partial<RecordingPolicy>,
    sourceInfo?: SourceInfo | null
  ): void {
    this.clear();
    this.sessionId = sessionId;
    this.sourceInfo = sourceInfo ?? null;
    this.sessionStartedAt = Date.now();
    this.droppedFrames = 0;

    if (policy?.limits?.maxHotFrames) {
      this.maxHotFrames = policy.limits.maxHotFrames;
    }
    if (policy?.limits?.maxStorageMB) {
      this.maxMemoryBytes = policy.limits.maxStorageMB * 1024 * 1024;
    }
    if (policy?.store?.persistToIndexedDB !== undefined) {
      this.persistToIndexedDB = policy.store.persistToIndexedDB;
    }

    console.log(
      `[HistoryRepository] 开始会话: ${sessionId}, maxHotFrames=${this.maxHotFrames}, persistToIndexedDB=${this.persistToIndexedDB}`
    );
  }

  /**
   * 将帧溢出到IndexedDB冷存储
   */
  private async spillToColdStorage(frameId: number, frame: MemoryFrame): Promise<void> {
    if (!this.sessionId || !this.persistToIndexedDB) {
      return;
    }

    const key = this.makeKey(this.sessionId, frameId);

    try {
      // 更新元数据中的存储位置
      const coldMeta: StoredFrameMeta = {
        ...frame.meta,
        imageRef: {
          ...frame.meta.imageRef,
          kind: 'indexeddb',
          key,
        },
      };

      // 批量写入元数据和图像
      await this.db.transaction('rw', [this.db.framesMeta, this.db.framesImage], async () => {
        await this.db.framesMeta.put({ key, meta: coldMeta });
        await this.db.framesImage.put({ key, blob: frame.blob });
      });

      this.coldFrameIds.add(frameId);
    } catch (error) {
      console.error(`[HistoryRepository] 写入IndexedDB失败: frameId=${frameId}`, error);
      this.droppedFrames++;
    }
  }

  /**
   * 存储帧数据
   */
  async storeFrame(meta: StoredFrameMeta, blob: Blob): Promise<boolean> {
    if (!this.sessionId || this.sessionId !== meta.sessionId) {
      console.warn('[HistoryRepository] 会话ID不匹配，忽略帧');
      return false;
    }

    // 检查内存限制
    const frameSize = blob.size;

    // 如果单帧超过限制，跳过
    if (frameSize > this.maxMemoryBytes * 0.1) {
      console.warn(`[HistoryRepository] 帧太大 (${frameSize} bytes)，跳过`);
      return false;
    }

    // 淘汰旧帧以腾出空间
    while (
      (this.frameOrder.length >= this.maxHotFrames ||
        this.memoryUsage + frameSize > this.maxMemoryBytes) &&
      this.frameOrder.length > 0
    ) {
      const oldestFrameId = this.frameOrder.shift()!;
      const oldFrame = this.memoryFrames.get(oldestFrameId);
      if (oldFrame) {
        this.memoryUsage -= oldFrame.blob.size;
        this.memoryFrames.delete(oldestFrameId);

        // 溢出到IndexedDB冷存储（异步，不阻塞主流程）
        if (this.persistToIndexedDB) {
          this.pendingWrites = this.pendingWrites
            .then(() => this.spillToColdStorage(oldestFrameId, oldFrame))
            .catch((err) => {
              console.error('[HistoryRepository] 冷存储写入失败:', err);
            });
        }
      }
    }

    // 存储新帧到内存
    this.memoryFrames.set(meta.frameId, { meta, blob });
    this.frameOrder.push(meta.frameId);
    this.memoryUsage += frameSize;

    return true;
  }

  /**
   * 从IndexedDB获取帧数据
   */
  private async getFrameFromColdStorage(frameId: number): Promise<HistoryFrameWithImage | null> {
    if (!this.sessionId) {
      return null;
    }

    const key = this.makeKey(this.sessionId, frameId);

    try {
      const [metaRecord, imageRecord] = await Promise.all([
        this.db.framesMeta.get(key),
        this.db.framesImage.get(key),
      ]);

      if (metaRecord && imageRecord) {
        return {
          meta: metaRecord.meta,
          blob: imageRecord.blob,
        };
      }
    } catch (error) {
      console.error(`[HistoryRepository] 从IndexedDB读取失败: frameId=${frameId}`, error);
    }

    return null;
  }

  /**
   * 获取帧数据
   */
  async getFrame(frameId: number): Promise<HistoryFrameWithImage | null> {
    // 先检查内存（热存储）
    const frame = this.memoryFrames.get(frameId);
    if (frame) {
      return {
        meta: frame.meta,
        blob: frame.blob,
      };
    }

    // 再检查IndexedDB（冷存储）
    if (this.coldFrameIds.has(frameId) || this.persistToIndexedDB) {
      return this.getFrameFromColdStorage(frameId);
    }

    return null;
  }

  /**
   * 获取帧元数据（不含图像）- 仅内存，同步
   */
  getFrameMeta(frameId: number): StoredFrameMeta | null {
    const frame = this.memoryFrames.get(frameId);
    return frame?.meta ?? null;
  }

  /**
   * 获取帧元数据（不含图像）- 包括IndexedDB，异步
   */
  async getFrameMetaAsync(frameId: number): Promise<StoredFrameMeta | null> {
    // 先检查内存
    const frame = this.memoryFrames.get(frameId);
    if (frame) {
      return frame.meta;
    }

    // 再检查IndexedDB
    if (!this.sessionId) {
      return null;
    }

    const key = this.makeKey(this.sessionId, frameId);
    try {
      const record = await this.db.framesMeta.get(key);
      return record?.meta ?? null;
    } catch {
      return null;
    }
  }

  /**
   * 获取所有帧ID列表（包括冷存储）
   */
  getAllFrameIds(): number[] {
    // 合并内存帧和冷存储帧，按ID排序
    const allIds = new Set([...this.frameOrder, ...this.coldFrameIds]);
    return Array.from(allIds).sort((a, b) => a - b);
  }

  /**
   * 获取帧数量（包括冷存储）
   */
  getFrameCount(): number {
    return this.memoryFrames.size + this.coldFrameIds.size;
  }

  /**
   * 获取内存使用量
   */
  getMemoryUsage(): {
    bytes: number;
    frames: number;
    maxBytes: number;
    maxFrames: number;
    coldFrames: number;
    droppedFrames: number;
  } {
    return {
      bytes: this.memoryUsage,
      frames: this.memoryFrames.size,
      maxBytes: this.maxMemoryBytes,
      maxFrames: this.maxHotFrames,
      coldFrames: this.coldFrameIds.size,
      droppedFrames: this.droppedFrames,
    };
  }

  /**
   * 批量获取帧数据（用于导出）
   * 优化：批量从IndexedDB读取，减少事务开销
   */
  async getFramesBatch(
    frameIds: number[],
    onProgress?: (progress: number) => void
  ): Promise<HistoryFrameWithImage[]> {
    const results: HistoryFrameWithImage[] = [];
    const memoryHits: HistoryFrameWithImage[] = [];
    const coldFrameIds: number[] = [];

    // 第一遍：收集内存命中和需要从IndexedDB读取的帧ID
    for (const frameId of frameIds) {
      const frame = this.memoryFrames.get(frameId);
      if (frame) {
        memoryHits.push({ meta: frame.meta, blob: frame.blob });
      } else if (this.coldFrameIds.has(frameId)) {
        coldFrameIds.push(frameId);
      }
    }

    // 添加内存命中的帧
    results.push(...memoryHits);

    if (onProgress) {
      onProgress(memoryHits.length / frameIds.length);
    }

    // 批量从IndexedDB读取冷存储帧
    if (coldFrameIds.length > 0 && this.sessionId) {
      const keys = coldFrameIds.map((id) => this.makeKey(this.sessionId!, id));

      try {
        // 批量读取元数据和图像
        const [metaRecords, imageRecords] = await Promise.all([
          this.db.framesMeta.bulkGet(keys),
          this.db.framesImage.bulkGet(keys),
        ]);

        for (let i = 0; i < coldFrameIds.length; i++) {
          const metaRecord = metaRecords[i];
          const imageRecord = imageRecords[i];

          if (metaRecord && imageRecord) {
            results.push({
              meta: metaRecord.meta,
              blob: imageRecord.blob,
            });
          }

          if (onProgress && i % 10 === 0) {
            onProgress((memoryHits.length + i + 1) / frameIds.length);
          }
        }
      } catch (error) {
        console.error('[HistoryRepository] 批量读取IndexedDB失败:', error);
      }
    }

    if (onProgress) {
      onProgress(1);
    }

    // 按原始frameId顺序排序结果
    const frameIdOrder = new Map(frameIds.map((id, idx) => [id, idx]));
    results.sort((a, b) => {
      const orderA = frameIdOrder.get(a.meta.frameId) ?? Infinity;
      const orderB = frameIdOrder.get(b.meta.frameId) ?? Infinity;
      return orderA - orderB;
    });

    return results;
  }

  /**
   * 保存会话元数据到IndexedDB
   */
  private async saveSessionMetadata(): Promise<void> {
    if (!this.sessionId || !this.persistToIndexedDB) {
      return;
    }

    const summary: ResultsSessionSummary = {
      sessionId: this.sessionId,
      startedAt: this.sessionStartedAt,
      endedAt: Date.now(),
      sourceInfo: this.sourceInfo,
      totalFramesRecorded: this.getFrameCount(),
      droppedFrames: this.droppedFrames,
    };

    try {
      await this.db.sessions.put({
        sessionId: this.sessionId,
        summary,
        coldFrameIds: Array.from(this.coldFrameIds),
      });
    } catch (error) {
      console.error('[HistoryRepository] 保存会话元数据失败:', error);
    }
  }

  /**
   * 清空当前会话的IndexedDB数据
   */
  private async clearColdStorage(): Promise<void> {
    if (!this.sessionId) {
      return;
    }

    const sessionId = this.sessionId;
    const coldIds = Array.from(this.coldFrameIds);

    if (coldIds.length === 0) {
      // 仅删除会话记录
      try {
        await this.db.sessions.delete(sessionId);
      } catch {
        // 忽略错误
      }
      return;
    }

    const keys = coldIds.map((id) => this.makeKey(sessionId, id));

    try {
      await this.db.transaction('rw', [this.db.framesMeta, this.db.framesImage, this.db.sessions], async () => {
        await this.db.framesMeta.bulkDelete(keys);
        await this.db.framesImage.bulkDelete(keys);
        await this.db.sessions.delete(sessionId);
      });
      console.log(`[HistoryRepository] 已清除IndexedDB冷存储: ${coldIds.length}帧`);
    } catch (error) {
      console.error('[HistoryRepository] 清除IndexedDB失败:', error);
    }
  }

  /**
   * 等待所有待处理的写入完成
   */
  async flush(): Promise<void> {
    await this.pendingWrites;
    await this.saveSessionMetadata();
  }

  /**
   * 清空所有数据
   */
  clear(): void {
    // 先清除IndexedDB（异步）
    this.clearColdStorage().catch((err) => {
      console.error('[HistoryRepository] 清除冷存储失败:', err);
    });

    // 清除内存数据
    this.memoryFrames.clear();
    this.frameOrder = [];
    this.coldFrameIds.clear();
    this.memoryUsage = 0;
    this.sessionId = null;
    this.sourceInfo = null;
    this.sessionStartedAt = 0;
    this.droppedFrames = 0;
    this.pendingWrites = Promise.resolve();

    console.log('[HistoryRepository] 已清空');
  }

  /**
   * 获取当前会话ID
   */
  getSessionId(): string | null {
    return this.sessionId;
  }

  /**
   * 获取数据库实例（用于高级操作）
   */
  getDatabase(): HistoryDatabase {
    return this.db;
  }

  /**
   * 列出所有已保存的会话
   */
  async listSessions(): Promise<ResultsSessionSummary[]> {
    try {
      const records = await this.db.sessions.toArray();
      return records.map((r) => r.summary);
    } catch {
      return [];
    }
  }

  /**
   * 加载历史会话
   */
  async loadSession(sessionId: string): Promise<boolean> {
    try {
      const record = await this.db.sessions.get(sessionId);
      if (!record) {
        return false;
      }

      // 清除当前数据（不清除IndexedDB）
      this.memoryFrames.clear();
      this.frameOrder = [];
      this.memoryUsage = 0;

      // 设置会话信息
      this.sessionId = sessionId;
      this.sourceInfo = record.summary.sourceInfo;
      this.sessionStartedAt = record.summary.startedAt;
      this.droppedFrames = record.summary.droppedFrames;
      this.coldFrameIds = new Set(record.coldFrameIds);

      console.log(`[HistoryRepository] 已加载会话: ${sessionId}, 冷存储帧数: ${this.coldFrameIds.size}`);
      return true;
    } catch (error) {
      console.error('[HistoryRepository] 加载会话失败:', error);
      return false;
    }
  }

  /**
   * 删除指定会话的所有数据
   */
  async deleteSession(sessionId: string): Promise<void> {
    try {
      const record = await this.db.sessions.get(sessionId);
      if (!record) {
        return;
      }

      const keys = record.coldFrameIds.map((id) => this.makeKey(sessionId, id));

      await this.db.transaction('rw', [this.db.framesMeta, this.db.framesImage, this.db.sessions], async () => {
        await this.db.framesMeta.bulkDelete(keys);
        await this.db.framesImage.bulkDelete(keys);
        await this.db.sessions.delete(sessionId);
      });

      console.log(`[HistoryRepository] 已删除会话: ${sessionId}`);
    } catch (error) {
      console.error('[HistoryRepository] 删除会话失败:', error);
    }
  }
}

/** 全局历史存储库单例 */
export const historyRepository = new HistoryRepository();
