// 配置相关类型

export type ModelSize = 'n' | 's' | 'm' | 'l' | 'x';

export interface DetectorConfig {
  model_size: ModelSize;
  face_confidence_threshold: number;
  person_confidence_threshold: number;
  iou_threshold: number;
  detect_face: boolean;
  detect_person: boolean;
  max_detections: number;
}

export interface RecognizerConfig {
  model_path: string | null;
  emotion_labels: string[];
  batch_size: number;
  use_face: boolean;
  use_body: boolean;
}

export interface VisualizerConfig {
  show_bounding_box: boolean;
  show_person_box: boolean;
  show_emotion_label: boolean;
  show_confidence: boolean;
  show_emotion_bar: boolean;
  box_color_by_emotion: boolean;
  font_scale: number;
  box_thickness: number;
  emotion_colors: Record<string, string>;
}

export interface PerformanceConfig {
  target_fps: number;
  skip_frames: number;
  async_inference: boolean;
  output_quality: number;
  // 新增性能参数
  use_binary_ws?: boolean;
  inference_threads?: number;
  frame_buffer_size?: number;
  adaptive_skip?: boolean;
}

export interface PipelineConfig {
  detector: DetectorConfig;
  recognizer: RecognizerConfig;
  visualizer: VisualizerConfig;
  performance: PerformanceConfig;
}

// 默认配置
export const DEFAULT_CONFIG: PipelineConfig = {
  detector: {
    model_size: 'n',
    face_confidence_threshold: 0.75,
    person_confidence_threshold: 0.5,
    iou_threshold: 0.45,
    detect_face: true,
    detect_person: true,
    max_detections: 100,
  },
  recognizer: {
    model_path: null,
    emotion_labels: ['开心', '悲伤', '愤怒', '恐惧', '惊讶', '厌恶', '中性'],
    batch_size: 8,
    use_face: true,
    use_body: true,
  },
  visualizer: {
    show_bounding_box: true,
    show_person_box: false,
    show_emotion_label: true,
    show_confidence: true,
    show_emotion_bar: true,
    box_color_by_emotion: true,
    font_scale: 0.8,
    box_thickness: 2,
    emotion_colors: {
      '开心': '#22c55e',
      '悲伤': '#3b82f6',
      '愤怒': '#ef4444',
      '恐惧': '#a855f7',
      '惊讶': '#f59e0b',
      '厌恶': '#84cc16',
      '中性': '#6b7280',
    },
  },
  performance: {
    target_fps: 30,
    skip_frames: 0,
    async_inference: true,
    output_quality: 80,
    use_binary_ws: true,
    inference_threads: 2,
    frame_buffer_size: 2,
    adaptive_skip: true,
  },
};
