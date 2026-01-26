// 情绪分布图表组件

import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import { usePipelineStore } from '../../store';
import { getEmotionColor } from '../../types';

export function EmotionChart() {
  const { emotions } = usePipelineStore();
  
  // 聚合所有检测结果的情绪概率
  const chartData = useMemo(() => {
    if (emotions.length === 0) return [];
    
    // 计算所有目标的情绪概率平均值
    const emotionSums: Record<string, number> = {};
    const counts: Record<string, number> = {};
    
    emotions.forEach((emotion) => {
      Object.entries(emotion.probabilities).forEach(([label, prob]) => {
        emotionSums[label] = (emotionSums[label] || 0) + prob;
        counts[label] = (counts[label] || 0) + 1;
      });
    });
    
    return Object.entries(emotionSums)
      .map(([label, sum]) => ({
        name: label,
        value: sum / (counts[label] || 1),
        color: getEmotionColor(label),
      }))
      .sort((a, b) => b.value - a.value);
  }, [emotions]);
  
  if (chartData.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-sm">
        暂无情绪数据
      </div>
    );
  }
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} layout="vertical" margin={{ left: 60, right: 20 }}>
        <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
        <YAxis type="category" dataKey="name" width={60} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
