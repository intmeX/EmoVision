// 页面头部组件

import { Wifi, WifiOff, Activity } from 'lucide-react';
import { usePipelineStore } from '../../store';

export function Header() {
  const { connected, state, fps, latency } = usePipelineStore();
  
  return (
    <header className="h-14 bg-bg-secondary border-b border-border-primary flex items-center justify-between px-4">
      {/* Logo区域 */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">E</span>
        </div>
        <h1 className="text-lg font-semibold text-white">EmoVision</h1>
        <span className="text-xs text-gray-500 bg-bg-tertiary px-2 py-0.5 rounded">v0.1.0</span>
      </div>
      
      {/* 状态区域 */}
      <div className="flex items-center gap-6">
        {/* 性能指标 */}
        {state === 'running' && (
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-accent-success" />
              <span className="text-gray-300">{fps.toFixed(1)} FPS</span>
            </div>
            <div className="text-gray-500">|</div>
            <div className="text-gray-300">
              延迟: <span className="text-accent-warning">{latency.toFixed(0)}ms</span>
            </div>
          </div>
        )}
        
        {/* 流水线状态 */}
        <div className="flex items-center gap-2">
          <StatusIndicator state={state} />
          <span className="text-sm text-gray-300 capitalize">{getStateLabel(state)}</span>
        </div>
        
        {/* 连接状态 */}
        <div className="flex items-center gap-2">
          {connected ? (
            <>
              <Wifi className="w-4 h-4 text-accent-success" />
              <span className="text-sm text-gray-400">已连接</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-accent-danger" />
              <span className="text-sm text-gray-400">未连接</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

function StatusIndicator({ state }: { state: string }) {
  const colorClass = {
    idle: 'bg-gray-500',
    running: 'bg-accent-success animate-pulse',
    paused: 'bg-accent-warning',
    error: 'bg-accent-danger',
  }[state] || 'bg-gray-500';
  
  return <div className={`w-2 h-2 rounded-full ${colorClass}`} />;
}

function getStateLabel(state: string): string {
  const labels: Record<string, string> = {
    idle: '空闲',
    running: '运行中',
    paused: '已暂停',
    error: '错误',
  };
  return labels[state] || state;
}
