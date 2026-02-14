// 检测器配置组件

import { useConfigStore } from '../../store';
import type { ModelSize } from '../../types';

export function DetectorConfig() {
  const { config, updateDetector } = useConfigStore();
  const detector = config.detector;
  
  const modelSizes: { value: ModelSize; label: string }[] = [
    { value: 'n', label: 'Nano (最快)' },
    { value: 's', label: 'Small' },
    { value: 'm', label: 'Medium' },
    { value: 'l', label: 'Large' },
    { value: 'x', label: 'XLarge (最准)' },
  ];
  
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* 模型尺寸 */}
        <div>
          <label className="label">模型尺寸</label>
          <select
            value={detector.model_size}
            onChange={(e) => updateDetector({ model_size: e.target.value as ModelSize })}
            className="input"
          >
            {modelSizes.map((size) => (
              <option key={size.value} value={size.value}>
                {size.label}
              </option>
            ))}
          </select>
        </div>
        
        {/* 人脸置信度阈值 */}
        <div>
          <label className="label">人脸置信度</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={detector.face_confidence_threshold}
              onChange={(e) => updateDetector({ face_confidence_threshold: Number(e.target.value) })}
              className="flex-1"
            />
            <span className="text-sm text-gray-400 w-12">
              {detector.face_confidence_threshold.toFixed(2)}
            </span>
          </div>
        </div>
        
        {/* 人体置信度阈值 */}
        <div>
          <label className="label">人体置信度</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={detector.person_confidence_threshold}
              onChange={(e) => updateDetector({ person_confidence_threshold: Number(e.target.value) })}
              className="flex-1"
            />
            <span className="text-sm text-gray-400 w-12">
              {detector.person_confidence_threshold.toFixed(2)}
            </span>
          </div>
        </div>
        
        {/* IoU阈值 */}
        <div>
          <label className="label">IoU阈值</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={detector.iou_threshold}
              onChange={(e) => updateDetector({ iou_threshold: Number(e.target.value) })}
              className="flex-1"
            />
            <span className="text-sm text-gray-400 w-12">
              {detector.iou_threshold.toFixed(2)}
            </span>
          </div>
        </div>
        
        {/* 最大检测数 */}
        <div>
          <label className="label">最大检测数</label>
          <input
            type="number"
            min="1"
            max="300"
            value={detector.max_detections}
            onChange={(e) => updateDetector({ max_detections: Number(e.target.value) })}
            className="input"
          />
        </div>
      </div>
      
      {/* 开关选项 */}
      <div className="flex items-center gap-6">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={detector.detect_face}
            onChange={(e) => updateDetector({ detect_face: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">检测人脸</span>
        </label>
        
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={detector.detect_person}
            onChange={(e) => updateDetector({ detect_person: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">检测人体</span>
        </label>
      </div>
    </div>
  );
}
