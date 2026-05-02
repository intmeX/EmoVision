// 可视化配置组件

import { useCallback } from 'react';
import { useConfigStore } from '../../store';
import { api } from '../../services/api';

export function VisualizerConfig() {
  const { config, updateVisualizer, updateDetector } = useConfigStore();
  const visualizer = config.visualizer;
  const detector = config.detector;

  // 实时同步 visualizer 配置到后端
  const applyVisualizer = useCallback(
    (patch: Partial<typeof visualizer>) => {
      updateVisualizer(patch);
      const next = { ...visualizer, ...patch };
      api.updateVisualizerConfig(next).catch(() => {});
    },
    [visualizer, updateVisualizer],
  );

  // 实时同步 detector 配置到后端（用于 show_person_box 联动）
  const applyDetector = useCallback(
    (patch: Partial<typeof detector>) => {
      updateDetector(patch);
      const next = { ...detector, ...patch };
      api.updateDetectorConfig(next).catch(() => {});
    },
    [detector, updateDetector],
  );

  return (
    <div className="space-y-4">
      {/* 显示选项 */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.show_bounding_box}
            onChange={(e) => applyVisualizer({ show_bounding_box: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">面部边界框</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.show_person_box}
            onChange={(e) => {
              applyVisualizer({ show_person_box: e.target.checked });
              applyDetector({ detect_person: e.target.checked });
            }}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">身体边界框</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.show_emotion_label}
            onChange={(e) => applyVisualizer({ show_emotion_label: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">情绪标签</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.show_confidence}
            onChange={(e) => applyVisualizer({ show_confidence: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">置信度</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.show_emotion_bar}
            onChange={(e) => applyVisualizer({ show_emotion_bar: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">概率条</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.box_color_by_emotion}
            onChange={(e) => applyVisualizer({ box_color_by_emotion: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">情绪着色</span>
        </label>
      </div>

      {/* 情绪显示数量 */}
      <div>
        <label className="label">
          情绪显示数量：{visualizer.emotion_display_count}
        </label>
        <select
          value={visualizer.emotion_display_count}
          onChange={(e) => applyVisualizer({ emotion_display_count: Number(e.target.value) })}
          className="select"
        >
          {[1, 2, 3, 4, 5, 6, 7].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </div>

      {/* 尺寸配置 */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="label">字体大小：{visualizer.font_scale.toFixed(1)}</label>
          <input
            type="range"
            min="0.1"
            max="3"
            step="0.1"
            value={visualizer.font_scale}
            onChange={(e) => applyVisualizer({ font_scale: Number(e.target.value) })}
            className="w-full"
          />
        </div>
        <div>
          <label className="label">边框粗细：{visualizer.box_thickness}</label>
          <input
            type="range"
            min="1"
            max="10"
            step="1"
            value={visualizer.box_thickness}
            onChange={(e) => applyVisualizer({ box_thickness: Number(e.target.value) })}
            className="w-full"
          />
        </div>
      </div>

      {/* 颜色配置 */}
      <div>
        <label className="label">情绪颜色配置</label>
        <div className="flex flex-wrap gap-3">
          {Object.entries(visualizer.emotion_colors).map(([emotion, color]) => (
            <div key={emotion} className="flex items-center gap-2">
              <input
                type="color"
                value={color}
                onChange={(e) =>
                  applyVisualizer({
                    emotion_colors: {
                      ...visualizer.emotion_colors,
                      [emotion]: e.target.value,
                    },
                  })
                }
                className="w-8 h-8 rounded cursor-pointer border border-border-primary"
              />
              <span className="text-sm text-gray-400">{emotion}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
