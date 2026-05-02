// 识别器配置组件

import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { useConfigStore } from '../../store';
import type { RecognizerType } from '../../types';

const RECOGNIZER_OPTIONS: { value: RecognizerType; label: string; description: string }[] = [
  { value: 'dden', label: 'DDEN', description: '单流人脸识别，速度最快' },
  { value: 'caer', label: 'CAER', description: '多流融合（背景+人脸+语义）' },
  { value: 'emotic', label: 'EMOTIC', description: '四流融合（背景+身体+人脸+语义）' },
];

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
      {/* 识别器类型 */}
      <div>
        <label className="label">识别算法</label>
        <select
          value={recognizer.recognizer_type}
          onChange={(e) => updateRecognizer({ recognizer_type: e.target.value as RecognizerType })}
          className="input w-full"
        >
          {RECOGNIZER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label} — {opt.description}
            </option>
          ))}
        </select>
      </div>

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

      {/* 批处理大小 */}
      <div className="grid grid-cols-2 gap-4">
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
      </div>
    </div>
  );
}
