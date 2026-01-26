// 流水线控制Hook

import { useCallback, useState } from 'react';
import { api } from '../services/api';
import { usePipelineStore } from '../store';
import type { SourceInfo } from '../types';

export function usePipeline() {
  const { state, sourceInfo, setSourceInfo, setState } = usePipelineStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const start = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      await api.startPipeline();
    } catch (err) {
      setError(err instanceof Error ? err.message : '启动失败');
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  const stop = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      await api.stopPipeline();
      setState('idle');
    } catch (err) {
      setError(err instanceof Error ? err.message : '停止失败');
    } finally {
      setIsLoading(false);
    }
  }, [setState]);
  
  const pause = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      await api.pausePipeline();
      setState('paused');
    } catch (err) {
      setError(err instanceof Error ? err.message : '暂停失败');
    } finally {
      setIsLoading(false);
    }
  }, [setState]);
  
  const resume = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      await api.resumePipeline();
      setState('running');
    } catch (err) {
      setError(err instanceof Error ? err.message : '恢复失败');
    } finally {
      setIsLoading(false);
    }
  }, [setState]);
  
  const uploadFile = useCallback(async (file: File): Promise<SourceInfo | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await api.uploadFile(file);
      setSourceInfo(response.data);
      return response.data;
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传失败');
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [setSourceInfo]);
  
  const setCamera = useCallback(async (cameraId: number): Promise<SourceInfo | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await api.setCamera(cameraId);
      setSourceInfo(response.data);
      return response.data;
    } catch (err) {
      setError(err instanceof Error ? err.message : '设置摄像头失败');
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [setSourceInfo]);
  
  const closeSource = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      await api.closeSource();
      setSourceInfo(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '关闭源失败');
    } finally {
      setIsLoading(false);
    }
  }, [setSourceInfo]);
  
  return {
    state,
    sourceInfo,
    isLoading,
    error,
    start,
    stop,
    pause,
    resume,
    uploadFile,
    setCamera,
    closeSource,
  };
}
