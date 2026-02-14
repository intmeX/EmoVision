// 情绪相关类型

export type EmotionLabel = 
  | '开心' 
  | '悲伤' 
  | '愤怒' 
  | '恐惧' 
  | '惊讶' 
  | '厌恶' 
  | '中性'
  | string;

export interface EmotionResult {
  detection_id: number;
  probabilities: Record<string, number>;
  dominant_emotion: string;
  confidence: number;
}

// 情绪颜色映射
export const EMOTION_COLORS: Record<string, string> = {
  '开心': '#22c55e',
  '悲伤': '#3b82f6',
  '愤怒': '#ef4444',
  '恐惧': '#a855f7',
  '惊讶': '#f59e0b',
  '厌恶': '#84cc16',
  '中性': '#6b7280',
};

export function getEmotionColor(emotion: string): string {
  return EMOTION_COLORS[emotion] || '#6b7280';
}
