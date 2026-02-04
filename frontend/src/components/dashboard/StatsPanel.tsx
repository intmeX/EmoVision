// 统计面板组件

import { Users, Smile, Clock, Zap } from 'lucide-react';
import { usePipelineStore } from '../../store';

export function StatsPanel() {
  const { fps, latency, detections, emotions } = usePipelineStore();
  
  const stats = [
    {
      icon: Users,
      label: '检测目标',
      value: detections.length,
      color: 'text-blue-400',
    },
    {
      icon: Smile,
      label: '情绪识别',
      value: emotions.length,
      color: 'text-green-400',
    },
    {
      icon: Zap,
      label: '帧率',
      value: `${fps.toFixed(1)} FPS`,
      color: 'text-yellow-400',
    },
    {
      icon: Clock,
      label: '延迟',
      value: `${latency.toFixed(0)} ms`,
      color: 'text-purple-400',
    },
  ];
  
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-bg-tertiary rounded-lg p-3 flex items-center gap-3"
        >
          <div className={`p-2 rounded-lg bg-bg-elevated ${stat.color}`}>
            <stat.icon className="w-4 h-4" />
          </div>
          <div>
            <p className="text-xs text-gray-500">{stat.label}</p>
            <p className="text-lg font-semibold text-white">{stat.value}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
