// 检测相关类型

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type DetectionType = 'face' | 'person';

export interface Detection {
  id: number;
  type: DetectionType;
  bbox: BoundingBox;
  confidence: number;
  paired_id?: number | null;
}
