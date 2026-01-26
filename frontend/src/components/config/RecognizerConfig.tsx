// 识别器配置组件

import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { useConfigStore } from '../../store';

export function RecognizerConfig() {
  const { config, updateRecognizer } = useConfigStore();
  const recognizer = config.recognizer;
  const [newLabel, setNewLabel] = useState('');
  
  const addLabel = () => {
    if (newLabel.trim() && !recognizer.emotion_labels.includes(newLabel.trim())) {
      updateRecognizer({
        emotion_labels: [...recognizer.emotion_labels, newLabel.trim()],
      });
      setNewLabel('');
    }
  };
  
  const removeLabel = (label: string) => {
    updateRecognizer({
      emotion_labels: recognizer.emotion_labels.filter((l) => l !== label),
    });
  };
  
  return (
    <div className="space-y-4">
      {/* 情绪标签管理 */}
      <div>
        <label className="label">情绪类别标签</label>
        <div className="flex flex-wrap gap-2 mb-2">
          {recognizer.emotion_labels.map((label) => (
            <span
              key={label}
              className="inline-flex items-center gap-1 px-2 py-1 bg-bg-tertiary rounded text-sm text-gray-300"
            >
              {label}
              <button
                onClick={() => removeLabel(label)}
                className="text-gray-500 hover:text-red-400"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addLabel()}
            placeholder="添加新标签"
            className="input flex-1"
          />
          <button onClick={addLabel} className="btn-secondary px-3">
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* 其他配置 */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <label className="label">批处理大小</label>
          <input
            type="number"
            min="1"
            max="64"
            value={recognizer.batch_size}
            onChange={(e) => updateRecognizer({ batch_size: Number(e.target.value) })}
            className="input"
          />
        </div>
        
        <div className="flex items-center gap-2 pt-6">
          <input
            type="checkbox"
            id="use_face"
            checked={recognizer.use_face}
            onChange={(e) => updateRecognizer({ use_face: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary"
          />
          <label htmlFor="use_face" className="text-sm text-gray-300">
            使用人脸特征
          </label>
        </div>
        
        <div className="flex items-center gap-2 pt-6">
          <input
            type="checkbox"
            id="use_body"
            checked={recognizer.use_body}
            onChange={(e) => updateRecognizer({ use_body: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary"
          />
          <label htmlFor="use_body" className="text-sm text-gray-300">
            使用身体特征
          </label>
        </div>
      </div>
    </div>
  );
}
