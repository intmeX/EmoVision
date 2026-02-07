/**
 * 回看模式情绪统计组件
 * 
 * 显示当前选中帧的情绪数据和整体会话统计
 */

import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip } from 'recharts';
import { useFrameIndex, useFrameEmotions, useSelectedFrameId } from '@/store';
import { getEmotionColor } from '@/types';

/**
 * 情绪颜色映射（与 ResultsTimeline 保持一致）
 */
const EMOTION_COLORS: Record<string, string> = {
  happy: '#22c55e',
  sad: '#3b82f6',
  angry: '#ef4444',
  fear: '#a855f7',
  surprise: '#f59e0b',
  disgust: '#84cc16',
  neutral: '#6b7280',
  contempt: '#f97316',
};

function getColor(emotion: string): string {
  return EMOTION_COLORS[emotion.toLowerCase()] ?? getEmotionColor(emotion);
}

/**
 * 回看模式情绪图表
 */
export function ReviewEmotionChart() {
  const frameEmotions = useFrameEmotions();
  const index = useFrameIndex();
  const selectedFrameId = useSelectedFrameId();
  
  // 计算整体情绪分布
  const overallDistribution = useMemo(() => {
    const counts: Record<string, number> = {};
    let total = 0;
    
    for (const [, data] of frameEmotions) {
      if (data.dominant) {
        counts[data.dominant] = (counts[data.dominant] || 0) + 1;
        total++;
      }
    }
    
    if (total === 0) return [];
    
    return Object.entries(counts)
      .map(([emotion, count]) => ({
        name: emotion,
        value: count,
        percentage: (count / total) * 100,
        color: getColor(emotion),
      }))
      .sort((a, b) => b.value - a.value);
  }, [frameEmotions]);
  
  // 获取当前帧的情绪数据
  const currentFrameEmotion = useMemo(() => {
    if (selectedFrameId === null) return null;
    return frameEmotions.get(selectedFrameId) ?? null;
  }, [selectedFrameId, frameEmotions]);
  
  if (index.frameIds.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-sm">
        暂无情绪数据
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* 当前帧情绪 */}
      {currentFrameEmotion && currentFrameEmotion.dominant && (
        <div className="bg-bg-tertiary rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">当前帧情绪</div>
          <div className="flex items-center gap-2">
            <div 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: getColor(currentFrameEmotion.dominant) }}
            />
            <span className="text-lg font-medium capitalize">
              {currentFrameEmotion.dominant}
            </span>
            <span className="text-gray-500 text-sm">
              ({currentFrameEmotion.count} 个检测目标)
            </span>
          </div>
        </div>
      )}
      
      {/* 整体情绪分布 */}
      {overallDistribution.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 mb-2">整体情绪分布</div>
          <div className="h-32">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={overallDistribution} layout="vertical" margin={{ left: 60, right: 20 }}>
                <XAxis 
                  type="number" 
                  tickFormatter={(v) => `${v}`}
                />
                <YAxis 
                  type="category" 
                  dataKey="name" 
                  width={60}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip 
                  formatter={(value: number, name: string) => [`${value} 帧 (${((value / index.frameIds.length) * 100).toFixed(1)}%)`, name]}
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
      )}
      
      {/* 统计摘要 */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="bg-bg-tertiary rounded p-2">
          <div className="text-gray-500 text-xs">总帧数</div>
          <div className="font-medium">{index.frameIds.length}</div>
        </div>
        <div className="bg-bg-tertiary rounded p-2">
          <div className="text-gray-500 text-xs">有检测结果</div>
          <div className="font-medium">
            {Array.from(frameEmotions.values()).filter(e => e.count > 0).length}
          </div>
        </div>
      </div>
    </div>
  );
}
