// 情绪分布图表组件
// 通过 frameManager 订阅实时帧数据，避免高频 store 更新

import { useState, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import { useFrame } from '@/hooks/useFrame';
import { getEmotionColor } from '@/types';
import type { EmotionResult } from '@/types';

interface ChartEntry {
  name: string;
  value: number;
  color: string;
}

function buildChartData(emotions: EmotionResult[]): ChartEntry[] {
  if (emotions.length === 0) return [];

  const emotionSums: Record<string, number> = {};
  const counts: Record<string, number> = {};

  for (const emotion of emotions) {
    for (const [label, prob] of Object.entries(emotion.probabilities)) {
      emotionSums[label] = (emotionSums[label] || 0) + prob;
      counts[label] = (counts[label] || 0) + 1;
    }
  }

  return Object.entries(emotionSums)
    .map(([label, sum]) => ({
      name: label,
      value: sum / (counts[label] || 1),
      color: getEmotionColor(label),
    }))
    .sort((a, b) => b.value - a.value);
}

export function EmotionChart() {
  const [chartData, setChartData] = useState<ChartEntry[]>([]);

  useFrame(
    useCallback((frame) => {
      setChartData(buildChartData(frame.emotions));
    }, []),
  );

  if (chartData.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-sm">
        暂无情绪数据
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} layout="vertical" margin={{ left: 80, right: 20 }}>
        <XAxis type="number" domain={[0, 1]} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
        <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
