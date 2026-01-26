// 可视化配置组件

import { useConfigStore } from '../../store';

export function VisualizerConfig() {
  const { config, updateVisualizer } = useConfigStore();
  const visualizer = config.visualizer;
  
  return (
    <div className="space-y-4">
      {/* 显示选项 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.show_bounding_box}
            onChange={(e) => updateVisualizer({ show_bounding_box: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">边界框</span>
        </label>
        
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.show_emotion_label}
            onChange={(e) => updateVisualizer({ show_emotion_label: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">情绪标签</span>
        </label>
        
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.show_confidence}
            onChange={(e) => updateVisualizer({ show_confidence: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">置信度</span>
        </label>
        
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.show_emotion_bar}
            onChange={(e) => updateVisualizer({ show_emotion_bar: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">概率条</span>
        </label>
        
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={visualizer.box_color_by_emotion}
            onChange={(e) => updateVisualizer({ box_color_by_emotion: e.target.checked })}
            className="w-4 h-4 rounded bg-bg-tertiary border-border-primary text-accent-primary"
          />
          <span className="text-sm text-gray-300">情绪配色</span>
        </label>
      </div>
      
      {/* 样式参数 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <label className="label">字体大小</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="0.1"
              max="3"
              step="0.1"
              value={visualizer.font_scale}
              onChange={(e) => updateVisualizer({ font_scale: Number(e.target.value) })}
              className="flex-1"
            />
            <span className="text-sm text-gray-400 w-8">
              {visualizer.font_scale.toFixed(1)}
            </span>
          </div>
        </div>
        
        <div>
          <label className="label">边框粗细</label>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="1"
              max="10"
              step="1"
              value={visualizer.box_thickness}
              onChange={(e) => updateVisualizer({ box_thickness: Number(e.target.value) })}
              className="flex-1"
            />
            <span className="text-sm text-gray-400 w-8">
              {visualizer.box_thickness}
            </span>
          </div>
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
                  updateVisualizer({
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
