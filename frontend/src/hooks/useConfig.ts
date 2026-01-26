// 配置管理Hook

import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import { useConfigStore } from '../store';
import type { PipelineConfig } from '../types';

export function useConfig() {
  const { config, setConfig, isLoading, setLoading, isDirty, setDirty } = useConfigStore();
  const [error, setError] = useState<string | null>(null);
  
  // 加载配置
  const loadConfig = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.getConfig();
      setConfig(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载配置失败');
    } finally {
      setLoading(false);
    }
  }, [setConfig, setLoading]);
  
  // 保存完整配置
  const saveConfig = useCallback(async (newConfig?: PipelineConfig) => {
    try {
      setLoading(true);
      setError(null);
      const configToSave = newConfig || config;
      const response = await api.updateConfig(configToSave);
      setConfig(response.data);
      setDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存配置失败');
    } finally {
      setLoading(false);
    }
  }, [config, setConfig, setLoading, setDirty]);
  
  // 重置配置
  const resetConfig = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.resetConfig();
      setConfig(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '重置配置失败');
    } finally {
      setLoading(false);
    }
  }, [setConfig, setLoading]);
  
  // 初始加载
  useEffect(() => {
    loadConfig();
  }, [loadConfig]);
  
  return {
    config,
    isLoading,
    isDirty,
    error,
    loadConfig,
    saveConfig,
    resetConfig,
  };
}
