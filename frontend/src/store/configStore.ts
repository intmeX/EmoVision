// 配置状态管理

import { create } from 'zustand';
import type { PipelineConfig } from '../types';
import { DEFAULT_CONFIG } from '../types';

interface ConfigStore {
  config: PipelineConfig;
  isLoading: boolean;
  isDirty: boolean;
  
  setConfig: (config: PipelineConfig) => void;
  updateDetector: (detector: Partial<PipelineConfig['detector']>) => void;
  updateRecognizer: (recognizer: Partial<PipelineConfig['recognizer']>) => void;
  updateVisualizer: (visualizer: Partial<PipelineConfig['visualizer']>) => void;
  updatePerformance: (performance: Partial<PipelineConfig['performance']>) => void;
  setLoading: (loading: boolean) => void;
  setDirty: (dirty: boolean) => void;
  resetConfig: () => void;
}

export const useConfigStore = create<ConfigStore>((set) => ({
  config: DEFAULT_CONFIG,
  isLoading: false,
  isDirty: false,
  
  setConfig: (config) => set({ config, isDirty: false }),
  
  updateDetector: (detector) => set((state) => ({
    config: {
      ...state.config,
      detector: { ...state.config.detector, ...detector },
    },
    isDirty: true,
  })),
  
  updateRecognizer: (recognizer) => set((state) => ({
    config: {
      ...state.config,
      recognizer: { ...state.config.recognizer, ...recognizer },
    },
    isDirty: true,
  })),
  
  updateVisualizer: (visualizer) => set((state) => ({
    config: {
      ...state.config,
      visualizer: { ...state.config.visualizer, ...visualizer },
    },
    isDirty: true,
  })),
  
  updatePerformance: (performance) => set((state) => ({
    config: {
      ...state.config,
      performance: { ...state.config.performance, ...performance },
    },
    isDirty: true,
  })),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  setDirty: (isDirty) => set({ isDirty }),
  
  resetConfig: () => set({ config: DEFAULT_CONFIG, isDirty: false }),
}));
