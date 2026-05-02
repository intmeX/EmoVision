/**
 * 回看模式情绪统计组件
 * 
 * 显示当前选中帧的情绪数据和整体会话统计
 */

import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip } from 'recharts';
import { useFrameIndex, useFrameEmotions } from '@/store';

/**
 * 情绪颜色映射（与 ResultsTimeline 保持一致）
 */
const EMOTION_COLORS: Record<string, string> = {
  '开心': '#22c55e',
  '悲伤': '#3b82f6',
  '愤怒': '#ef4444',
  '恐惧': '#a855f7',
  '惊讶': '#f59e0b',
  '厌恶': '#84cc16',
  '中性': '#6b7280',
};

/**
 * 回看模式情绪图表
 */
export function ReviewEmotionChart() {
  const frameEmotions = useFrameEmotions();
  const index = useFrameIndex();
  
  // 计算整体情绪分布（统计所有检测目标，不只是每帧的主情绪）
  // 固定显示7类情绪，即使某类count为0
  const overallDistribution = useMemo(() => {
    const counts: Record<string, number> = {};
    let total = 0;
    
    for (const [, data] of frameEmotions) {
      for (const e of data.emotions) {
        counts[e.emotion] = (counts[e.emotion] || 0) + 1;
        total++;
      }
    }
    
    // 固定7类情绪全部显示，count为0的也包含
    return Object.entries(EMOTION_COLORS).map(([emotion, color]) => ({
      name: emotion,
      value: counts[emotion] ?? 0,
      percentage: total > 0 ? ((counts[emotion] ?? 0) / total) * 100 : 0,
      color,
      total,
    }));
  }, [frameEmotions]);
  
  // 计算总检测目标数
  const totalDetections = useMemo(() => {
    let total = 0;
    for (const [, data] of frameEmotions) {
      total += data.emotions.length;
    }
    return total;
  }, [frameEmotions]);

  if (index.frameIds.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-sm">
        暂无情绪数据
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* 整体情绪分布 - 固定显示7类 */}
      <div>
        <div className="text-xs text-gray-500 mb-2">整体情绪分布（按检测目标数）</div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={overallDistribution} layout="vertical" margin={{ left: 80, right: 20 }}>
              <XAxis 
                type="number" 
                tickFormatter={(v) => `${v}`}
              />
              <YAxis 
                type="category" 
                dataKey="name" 
                width={80}
                tick={{ fontSize: 12 }}
              />
              <Tooltip 
                formatter={(value: number, _name: string, props: { payload?: { total?: number } }) => {
                  const t = props?.payload?.total ?? 0;
                  return [`${value} 次 (${t > 0 ? ((value / t) * 100).toFixed(1) : '0.0'}%)`, '检测数'];
                }}
                contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {overallDistribution.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* 统计摘要 */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="bg-bg-tertiary rounded p-2">
          <div className="text-gray-500 text-xs">总帧数</div>
          <div className="font-medium">{index.frameIds.length}</div>
        </div>
        <div className="bg-bg-tertiary rounded p-2">
          <div className="text-gray-500 text-xs">总检测目标</div>
          <div className="font-medium">{totalDetections}</div>
        </div>
      </div>
    </div>
  );
}
