// API服务封装

import type { ApiResponse, PipelineConfig, SourceInfo } from '../types';

const API_BASE = '/api';

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${API_BASE}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || `请求失败: ${response.status}`);
    }
    
    return response.json();
  }
  
  // 流水线控制
  async getPipelineStatus() {
    return this.request<{ state: string; source_info: SourceInfo | null }>(
      '/pipeline/status'
    );
  }
  
  async startPipeline() {
    return this.request('/pipeline/start', { method: 'POST' });
  }
  
  async stopPipeline() {
    return this.request('/pipeline/stop', { method: 'POST' });
  }
  
  async pausePipeline() {
    return this.request('/pipeline/pause', { method: 'POST' });
  }
  
  async resumePipeline() {
    return this.request('/pipeline/resume', { method: 'POST' });
  }
  
  // 视觉源管理
  async uploadFile(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE}/source/upload`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || '上传失败');
    }
    
    return response.json() as Promise<ApiResponse<SourceInfo>>;
  }
  
  async setCamera(cameraId: number) {
    return this.request<SourceInfo>('/source/camera', {
      method: 'POST',
      body: JSON.stringify({ camera_id: cameraId }),
    });
  }
  
  async listCameras() {
    return this.request<{ id: number; available: boolean }[]>('/source/list');
  }
  
  async getCurrentSource() {
    return this.request<SourceInfo | null>('/source/current');
  }
  
  async closeSource() {
    return this.request('/source/close', { method: 'DELETE' });
  }
  
  // 配置管理
  async getConfig() {
    return this.request<PipelineConfig>('/config');
  }
  
  async updateConfig(config: PipelineConfig) {
    return this.request<PipelineConfig>('/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }
  
  async updateDetectorConfig(config: PipelineConfig['detector']) {
    return this.request<PipelineConfig['detector']>('/config/detector', {
      method: 'PATCH',
      body: JSON.stringify(config),
    });
  }
  
  async updateRecognizerConfig(config: PipelineConfig['recognizer']) {
    return this.request<PipelineConfig['recognizer']>('/config/recognizer', {
      method: 'PATCH',
      body: JSON.stringify(config),
    });
  }
  
  async updateVisualizerConfig(config: PipelineConfig['visualizer']) {
    return this.request<PipelineConfig['visualizer']>('/config/visualizer', {
      method: 'PATCH',
      body: JSON.stringify(config),
    });
  }
  
  async updatePerformanceConfig(config: PipelineConfig['performance']) {
    return this.request<PipelineConfig['performance']>('/config/performance', {
      method: 'PATCH',
      body: JSON.stringify(config),
    });
  }
  
  async resetConfig() {
    return this.request<PipelineConfig>('/config/reset', { method: 'POST' });
  }
  
  async getEmotionLabels() {
    return this.request<string[]>('/config/emotions/labels');
  }
  
  async updateEmotionLabels(labels: string[]) {
    return this.request<string[]>('/config/emotions/labels', {
      method: 'PUT',
      body: JSON.stringify({ labels }),
    });
  }
}

export const api = new ApiService();
