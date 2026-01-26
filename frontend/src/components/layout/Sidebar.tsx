// 侧边栏组件

import { useState } from 'react';
import {
  Play,
  Pause,
  Square,
  Upload,
  Camera,
  Image,
  Video,
  Settings,
  ChevronDown,
  ChevronUp,
  Folder,
} from 'lucide-react';
import { usePipeline } from '../../hooks';
import { usePipelineStore } from '../../store';
import clsx from 'clsx';

export function Sidebar() {
  const { state, sourceInfo } = usePipelineStore();
  const { start, stop, pause, resume, uploadFile, setCamera, isLoading } = usePipeline();
  const [showSourcePanel, setShowSourcePanel] = useState(true);
  
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      await uploadFile(file);
    }
  };
  
  const handleCameraSelect = async () => {
    await setCamera(0);
  };
  
  return (
    <aside className="w-64 bg-bg-secondary border-r border-border-primary flex flex-col">
      {/* 流水线控制 */}
      <div className="p-4 border-b border-border-primary">
        <h3 className="text-sm font-medium text-gray-400 mb-3">流水线控制</h3>
        <div className="flex gap-2">
          {state === 'idle' && (
            <button
              onClick={start}
              disabled={isLoading || !sourceInfo}
              className={clsx(
                'btn-primary flex-1 flex items-center justify-center gap-2',
                (!sourceInfo || isLoading) && 'opacity-50 cursor-not-allowed'
              )}
            >
              <Play className="w-4 h-4" />
              启动
            </button>
          )}
          
          {state === 'running' && (
            <>
              <button
                onClick={pause}
                disabled={isLoading}
                className="btn-secondary flex-1 flex items-center justify-center gap-2"
              >
                <Pause className="w-4 h-4" />
                暂停
              </button>
              <button
                onClick={stop}
                disabled={isLoading}
                className="btn-danger flex items-center justify-center px-3"
              >
                <Square className="w-4 h-4" />
              </button>
            </>
          )}
          
          {state === 'paused' && (
            <>
              <button
                onClick={resume}
                disabled={isLoading}
                className="btn-success flex-1 flex items-center justify-center gap-2"
              >
                <Play className="w-4 h-4" />
                继续
              </button>
              <button
                onClick={stop}
                disabled={isLoading}
                className="btn-danger flex items-center justify-center px-3"
              >
                <Square className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
      
      {/* 视觉源选择 */}
      <div className="border-b border-border-primary">
        <button
          onClick={() => setShowSourcePanel(!showSourcePanel)}
          className="w-full p-4 flex items-center justify-between hover:bg-bg-tertiary transition-colors"
        >
          <span className="text-sm font-medium text-gray-400">视觉源</span>
          {showSourcePanel ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </button>
        
        {showSourcePanel && (
          <div className="px-4 pb-4 space-y-2">
            {/* 上传文件 */}
            <label className="flex items-center gap-3 p-3 bg-bg-tertiary rounded-lg cursor-pointer hover:bg-bg-elevated transition-colors">
              <Upload className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-300">上传图像/视频</span>
              <input
                type="file"
                accept="image/*,video/*"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
            
            {/* 摄像头 */}
            <button
              onClick={handleCameraSelect}
              className="w-full flex items-center gap-3 p-3 bg-bg-tertiary rounded-lg hover:bg-bg-elevated transition-colors"
            >
              <Camera className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-300">使用摄像头</span>
            </button>
          </div>
        )}
      </div>
      
      {/* 当前源信息 */}
      {sourceInfo && (
        <div className="p-4 border-b border-border-primary">
          <h3 className="text-sm font-medium text-gray-400 mb-2">当前视觉源</h3>
          <div className="bg-bg-tertiary rounded-lg p-3 space-y-1">
            <div className="flex items-center gap-2">
              {sourceInfo.source_type === 'image' && <Image className="w-4 h-4 text-blue-400" />}
              {sourceInfo.source_type === 'video' && <Video className="w-4 h-4 text-green-400" />}
              {sourceInfo.source_type === 'camera' && <Camera className="w-4 h-4 text-purple-400" />}
              <span className="text-sm text-gray-300 capitalize">
                {getSourceTypeLabel(sourceInfo.source_type)}
              </span>
            </div>
            <div className="text-xs text-gray-500">
              {sourceInfo.width} x {sourceInfo.height}
              {sourceInfo.fps > 0 && ` @ ${sourceInfo.fps.toFixed(1)} FPS`}
            </div>
            {sourceInfo.path && (
              <div className="flex items-center gap-1 text-xs text-gray-500 truncate">
                <Folder className="w-3 h-3 flex-shrink-0" />
                <span className="truncate">{sourceInfo.path.split(/[/\\]/).pop()}</span>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* 底部填充 */}
      <div className="flex-1" />
      
      {/* 设置入口 */}
      <div className="p-4 border-t border-border-primary">
        <button className="w-full flex items-center gap-3 p-3 text-gray-400 hover:text-gray-200 hover:bg-bg-tertiary rounded-lg transition-colors">
          <Settings className="w-5 h-5" />
          <span className="text-sm">高级设置</span>
        </button>
      </div>
    </aside>
  );
}

function getSourceTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    image: '图像',
    video: '视频',
    camera: '摄像头',
  };
  return labels[type] || type;
}
