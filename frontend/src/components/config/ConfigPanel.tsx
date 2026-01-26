// 配置面板组件

import { useState } from 'react';
import { Settings, ChevronDown, ChevronUp, Save, RotateCcw } from 'lucide-react';
import { DetectorConfig } from './DetectorConfig';
import { RecognizerConfig } from './RecognizerConfig';
import { VisualizerConfig } from './VisualizerConfig';
import { useConfig } from '../../hooks';
import clsx from 'clsx';

type ConfigTab = 'detector' | 'recognizer' | 'visualizer' | 'performance';

export function ConfigPanel() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<ConfigTab>('detector');
  const { config, isDirty, isLoading, saveConfig, resetConfig } = useConfig();
  
  const tabs: { id: ConfigTab; label: string }[] = [
    { id: 'detector', label: '目标检测' },
    { id: 'recognizer', label: '情绪识别' },
    { id: 'visualizer', label: '可视化' },
    { id: 'performance', label: '性能' },
  ];
  
  return (
    <div className="bg-bg-secondary border-t border-border-primary">
      {/* 折叠头部 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-bg-tertiary transition-colors"
      >
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-300">参数配置</span>
          {isDirty && (
            <span className="text-xs px-2 py-0.5 bg-accent-warning/20 text-accent-warning rounded">
              未保存
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronUp className="w-4 h-4 text-gray-500" />
        )}
      </button>
      
      {/* 展开内容 */}
      {isExpanded && (
        <div className="animate-slide-up">
          {/* 标签页 */}
          <div className="flex border-b border-border-primary px-4">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
                  activeTab === tab.id
                    ? 'text-accent-primary border-accent-primary'
                    : 'text-gray-400 border-transparent hover:text-gray-200'
                )}
              >
                {tab.label}
              </button>
            ))}
            
            {/* 操作按钮 */}
            <div className="flex-1" />
            <div className="flex items-center gap-2 py-2">
              <button
                onClick={resetConfig}
                disabled={isLoading}
                className="btn-icon text-gray-400 hover:text-white"
                title="重置为默认"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                onClick={() => saveConfig()}
                disabled={isLoading || !isDirty}
                className={clsx(
                  'btn-primary text-sm px-3 py-1.5 flex items-center gap-1',
                  !isDirty && 'opacity-50 cursor-not-allowed'
                )}
              >
                <Save className="w-4 h-4" />
                保存
              </button>
            </div>
          </div>
          
          {/* 配置内容 */}
          <div className="p-4 max-h-64 overflow-y-auto">
            {activeTab === 'detector' && <DetectorConfig />}
            {activeTab === 'recognizer' && <RecognizerConfig />}
            {activeTab === 'visualizer' && <VisualizerConfig />}
            {activeTab === 'performance' && <PerformanceConfigPanel />}
          </div>
        </div>
      )}
    </div>
  );
}

// 性能配置面板
function PerformanceConfigPanel() {
  const { config, isLoading } = useConfig();
  const { updatePerformance } = require('../../store').useConfigStore();
  
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div>
        <label className="label">目标帧率</label>
        <input
          type="number"
          min="1"
          max="120"
          value={config.performance.target_fps}
          onChange={(e) => updatePerformance({ target_fps: Number(e.target.value) })}
          disabled={isLoading}
          className="input"
        />
      </div>
      
      <div>
        <label className="label">跳帧数</label>
        <input
          type="number"
          min="0"
          max="10"
          value={config.performance.skip_frames}
          onChange={(e) => updatePerformance({ skip_frames: Number(e.target.value) })}
          disabled={isLoading}
          className="input"
        />
      </div>
      
      <div>
        <label className="label">输出质量</label>
        <input
          type="number"
          min="10"
          max="100"
          value={config.performance.output_quality}
          onChange={(e) => updatePerformance({ output_quality: Number(e.target.value) })}
          disabled={isLoading}
          className="input"
        />
      </div>
      
      <div className="flex items-center gap-2 pt-6">
        <input
          type="checkbox"
          id="async_inference"
          checked={config.performance.async_inference}
          onChange={(e) => updatePerformance({ async_inference: e.target.checked })}
          disabled={isLoading}
          className="w-4 h-4 rounded bg-bg-tertiary border-border-primary"
        />
        <label htmlFor="async_inference" className="text-sm text-gray-300">
          异步推理
        </label>
      </div>
    </div>
  );
}
