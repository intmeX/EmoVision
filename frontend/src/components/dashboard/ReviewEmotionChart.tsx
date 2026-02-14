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
  '开心': '#22c55e',
  '悲伤': '#3b82f6',
  '愤怒': '#ef4444',
  '恐惧': '#a855f7',
  '惊讶': '#f59e0b',
  '厌恶': '#84cc16',
  '中性': '#6b7280',
};

function getColor(emotion: string): string {
  return EMOTION_COLORS[emotion] ?? getEmotionColor(emotion);
}

/**
 * 回看模式情绪图表
 */
export function ReviewEmotionChart() {
  const frameEmotions = useFrameEmotions();
  const index = useFrameIndex();
  const selectedFrameId = useSelectedFrameId();
  
  // 计算整体情绪分布（统计所有检测目标，不只是每帧的主情绪）
  const overallDistribution = useMemo(() => {
    const counts: Record<string, number> = {};
    let total = 0;
    
    for (const [, data] of frameEmotions) {
      // 统计该帧所有检测目标的情绪
      for (const e of data.emotions) {
        counts[e.emotion] = (counts[e.emotion] || 0) + 1;
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
  
  // 计算总检测目标数
  const totalDetections = useMemo(() => {
    let total = 0;
    for (const [, data] of frameEmotions) {
      total += data.emotions.length;
    }
    return total;
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
      {currentFrameEmotion && currentFrameEmotion.emotions.length > 0 && (
        <div className="bg-bg-tertiary rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">当前帧情绪</div>
          <div className="flex items-center gap-2">
            {currentFrameEmotion.dominant && (
              <>
                <div 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: getColor(currentFrameEmotion.dominant) }}
                />
                <span className="text-lg font-medium capitalize">
                  {currentFrameEmotion.dominant}
                </span>
              </>
            )}
            <span className="text-gray-500 text-sm">
              ({currentFrameEmotion.emotions.length} 个检测目标)
            </span>
          </div>
          {/* 显示该帧所有检测目标的情绪 */}
          {currentFrameEmotion.emotions.length > 1 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {currentFrameEmotion.emotions.map((e: { emotion: string; confidence: number }, i: number) => (
                <span 
                  key={i}
                  className="text-xs px-1.5 py-0.5 rounded"
                  style={{ 
                    backgroundColor: getColor(e.emotion) + '30',
                    color: getColor(e.emotion)
                  }}
                >
                  {e.emotion} {(e.confidence * 100).toFixed(0)}%
                </span>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* 整体情绪分布 */}
      {overallDistribution.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 mb-2">整体情绪分布（按检测目标数）</div>
          <div className="h-64"> {/* Increased height from h-32 to h-64 */ }
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={overallDistribution} layout="vertical" margin={{ left: 80, right: 20 }}> {/* Increased left margin from 60 to 80 */ }
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
                  formatter={(value: number) => [`${value} 次 (${((value / totalDetections) * 100).toFixed(1)}%)`, '检测数']}
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
          <div className="text-gray-500 text-xs">总检测目标</div>
          <div className="font-medium">{totalDetections}</div>
        </div>
      </div>
    </div>
  );
}
