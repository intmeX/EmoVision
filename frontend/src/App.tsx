// 主应用组件

import { MainLayout } from './components/layout';
import { VideoPlayer } from './components/video';
import { ConfigPanel } from './components/config';
import { EmotionChart, StatsPanel } from './components/dashboard';
import { useWebSocket } from './hooks';
import { usePipelineStore } from './store';

export default function App() {
  // 初始化WebSocket连接
  useWebSocket();
  
  const { state } = usePipelineStore();
  const isRunning = state === 'running' || state === 'paused';
  
  return (
    <MainLayout>
      <div className="h-full flex flex-col">
        {/* 主内容区域 */}
        <div className="flex-1 p-4 flex flex-col gap-4 overflow-hidden">
          {/* 视频区域 */}
          <div className="flex-1 min-h-0">
            <VideoPlayer />
          </div>
          
          {/* 统计和图表区域 */}
          {isRunning && (
            <div className="flex-shrink-0 space-y-4 animate-fade-in">
              {/* 统计面板 */}
              <StatsPanel />
              
              {/* 情绪图表 */}
              <div className="bg-bg-secondary rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-400 mb-3">情绪分布</h3>
                <div className="h-40">
                  <EmotionChart />
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* 配置面板 */}
        <ConfigPanel />
      </div>
    </MainLayout>
  );
}
