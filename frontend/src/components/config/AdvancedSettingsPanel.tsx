// 高级设置面板组件
import { useState } from 'react';
import { RotateCcw, Save } from 'lucide-react';
import { useConfig } from '../../hooks';
import { usePipelineStore } from '../../store';

export function AdvancedSettingsPanel() {
  const { config, isLoading } = useConfig();
  const { state } = usePipelineStore();
  const [localConfig, setLocalConfig] = useState(config);

  // 检查流水线是否正在运行，如果是则禁用编辑
  const isPipelineRunning = state === 'running';

  const handleSave = () => {
    // 这里可以保存高级设置
    console.log('保存高级设置:', localConfig);
  };

  const handleReset = () => {
    setLocalConfig(config);
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 模型设置 */}
        <div className="bg-bg-tertiary rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-3">模型设置</h3>
          
          <div className="space-y-4">
            <div>
              <label className="label">模型路径</label>
              <input
                type="text"
                value={localConfig.recognizer.model_path || ''}
                onChange={(e) => setLocalConfig({
                  ...localConfig,
                  recognizer: { 
                    ...localConfig.recognizer, 
                    model_path: e.target.value 
                  }
                })}
                disabled={isPipelineRunning || isLoading}
                className="input w-full"
              />
            </div>
            
            <div>
              <label className="label">批次大小</label>
              <input
                type="number"
                min="1"
                max="64"
                value={localConfig.recognizer.batch_size}
                onChange={(e) => setLocalConfig({
                  ...localConfig,
                  recognizer: { 
                    ...localConfig.recognizer, 
                    batch_size: Number(e.target.value) 
                  }
                })}
                disabled={isPipelineRunning || isLoading}
                className="input w-full"
              />
            </div>
          </div>
        </div>

        {/* 性能设置 */}
        <div className="bg-bg-tertiary rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-3">性能设置</h3>
          
          <div className="space-y-4">
            <div>
              <label className="label">内存限制 (MB)</label>
              <input
                type="number"
                min="100"
                max="8192"
                defaultValue="1024"
                disabled={isPipelineRunning || isLoading}
                className="input w-full"
              />
            </div>
            
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="use_gpu"
                defaultChecked
                disabled={isPipelineRunning || isLoading}
                className="w-4 h-4 rounded bg-bg-tertiary border-border-primary"
              />
              <label htmlFor="use_gpu" className="text-sm text-gray-300">
                使用GPU加速
              </label>
            </div>
            
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enable_caching"
                defaultChecked
                disabled={isPipelineRunning || isLoading}
                className="w-4 h-4 rounded bg-bg-tertiary border-border-primary"
              />
              <label htmlFor="enable_caching" className="text-sm text-gray-300">
                启用缓存
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex justify-end gap-3 pt-4">
        <button
          onClick={handleReset}
          disabled={isLoading}
          className="btn-secondary flex items-center gap-1 px-4 py-2"
        >
          <RotateCcw className="w-4 h-4" />
          重置
        </button>
        <button
          onClick={handleSave}
          disabled={isLoading || isPipelineRunning}
          className="btn-primary flex items-center gap-1 px-4 py-2"
        >
          <Save className="w-4 h-4" />
          保存设置
        </button>
      </div>
    </div>
  );
}