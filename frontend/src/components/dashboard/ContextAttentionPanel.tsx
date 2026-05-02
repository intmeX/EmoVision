import { useMemo, useState, useCallback } from 'react';

import { useFrame } from '@/hooks/useFrame';
import type { EmotionResult } from '@/types';

const CONTEXT_COLORS: Record<string, string> = {
  '背景': '#3b82f6',
  '身体': '#f59e0b',
  '人脸': '#ec4899',
  '场景语义': '#10b981',
};

interface AttentionEntry {
  label: string;
  value: number;
  color: string;
}

function buildAttentionData(emotions: EmotionResult[]): AttentionEntry[] {
  const sums: Record<string, number> = {};
  const counts: Record<string, number> = {};

  for (const emotion of emotions) {
    if (!emotion.context_attention) {
      continue;
    }

    for (const [label, value] of Object.entries(emotion.context_attention)) {
      sums[label] = (sums[label] || 0) + value;
      counts[label] = (counts[label] || 0) + 1;
    }
  }

  return Object.entries(sums)
    .map(([label, sum]) => ({
      label,
      value: sum / (counts[label] || 1),
      color: CONTEXT_COLORS[label] || '#6b7280',
    }))
    .sort((a, b) => b.value - a.value);
}

export function ContextAttentionPanel() {
  const [emotions, setEmotions] = useState<EmotionResult[]>([]);

  useFrame(
    useCallback((frame) => {
      setEmotions(frame.emotions);
    }, []),
  );

  const attentionData = useMemo(() => buildAttentionData(emotions), [emotions]);

  if (attentionData.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-sm">
        暂无上下文注意力数据
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {attentionData.map((entry) => (
        <div key={entry.label} className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-300">{entry.label}</span>
            <span className="text-gray-400">{(entry.value * 100).toFixed(1)}%</span>
          </div>
          <div className="h-2 rounded-full bg-bg-tertiary overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${entry.value * 100}%`,
                backgroundColor: entry.color,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
