// 情绪相关类型

export type EmotionLabel = 
  | 'happy' 
  | 'sad' 
  | 'angry' 
  | 'fear' 
  | 'surprise' 
  | 'disgust' 
  | 'neutral'
  | string;

export interface EmotionResult {
  detection_id: number;
  probabilities: Record<string, number>;
  dominant_emotion: string;
  confidence: number;
}

// 情绪颜色映射
export const EMOTION_COLORS: Record<string, string> = {
  happy: '#22c55e',
  sad: '#3b82f6',
  angry: '#ef4444',
  fear: '#a855f7',
  surprise: '#f59e0b',
  disgust: '#84cc16',
  neutral: '#6b7280',
};

export function getEmotionColor(emotion: string): string {
  return EMOTION_COLORS[emotion] || '#6b7280';
}
