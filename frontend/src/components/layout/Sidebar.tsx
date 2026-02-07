// 侧边栏组件

import { useState, useCallback } from 'react';
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
  X,
} from 'lucide-react';
import { usePipeline, useWebSocket } from '../../hooks';
import { usePipelineStore, useResultsStore } from '../../store';
import clsx from 'clsx';
import { getSourceTypeLabel } from '../../utils/helpers';
import { AdvancedSettingsPanel } from '../config/AdvancedSettingsPanel';
import { ResultsControlSection } from '../results';
import { frameHistoryRecorder } from '../../services/frameHistoryRecorder';

export function Sidebar() {
  const { state, sourceInfo, connected } = usePipelineStore();
  const resultsActions = useResultsStore((s) => s.actions);
  const { uploadFile, setCamera, closeSource, isLoading } = usePipeline();
  const { sendControl } = useWebSocket();
  const [showSourcePanel, setShowSourcePanel] = useState(true);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  
  const start = useCallback(() => {
    // 开始录制会话 - 使用统一的 sessionId
    const sessionId = resultsActions.startSession(sourceInfo);
    frameHistoryRecorder.startSession(sessionId, sourceInfo);
    sendControl('start');
  }, [sendControl, sourceInfo, resultsActions]);
  
  const stop = useCallback(() => {
    // 停止录制（不清空历史，保留会话数据）
    sendControl('stop');
    frameHistoryRecorder.stopSession();
    resultsActions.endCurrentSession();
  }, [sendControl, resultsActions]);
  
  const pause = useCallback(() => {
    sendControl('pause');
    // 暂停时保持当前状态，不自动进入回看模式
    // 用户可以手动点击历史记录进入回看
  }, [sendControl]);
  
  const resume = useCallback(() => {
    sendControl('resume');
    // 恢复实时模式
    resultsActions.resumeLive();
  }, [sendControl, resultsActions]);
  
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
               disabled={isLoading || !sourceInfo || !connected}
               className={clsx(
                 'btn-primary flex-1 flex items-center justify-center gap-2',
                 (!sourceInfo || isLoading || !connected) && 'opacity-50 cursor-not-allowed'
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
                 disabled={isLoading || !connected}
                 className="btn-secondary flex-1 flex items-center justify-center gap-2"
               >
                 <Pause className="w-4 h-4" />
                 暂停
               </button>
               <button
                 onClick={stop}
                 disabled={isLoading || !connected}
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
                 disabled={isLoading || !connected}
                 className="btn-success flex-1 flex items-center justify-center gap-2"
               >
                 <Play className="w-4 h-4" />
                 继续
               </button>
               <button
                 onClick={stop}
                 disabled={isLoading || !connected}
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
           <div className="flex items-center justify-between mb-2">
             <h3 className="text-sm font-medium text-gray-400">当前视觉源</h3>
             <button 
               onClick={closeSource}
               className="btn-icon text-gray-500 hover:text-red-400"
               title="关闭视觉源"
             >
               <X className="w-4 h-4" />
             </button>
           </div>
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
       
       {/* 结果记录控制区 */}
       <div className="p-4 border-b border-border-primary">
         <h3 className="text-xs font-medium text-gray-500 uppercase mb-2">
           结果记录
         </h3>
         <ResultsControlSection />
       </div>
      
       {/* 底部填充 */}
       <div className="flex-1" />
      
       {/* 设置入口 */}
       <div className="p-4 border-t border-border-primary">
         <button 
           className="w-full flex items-center gap-3 p-3 text-gray-400 hover:text-gray-200 hover:bg-bg-tertiary rounded-lg transition-colors"
           onClick={() => setShowAdvancedSettings(true)}
         >
           <Settings className="w-5 h-5" />
           <span className="text-sm">高级设置</span>
         </button>
       </div>
       
       {/* 高级设置弹窗 */}
       {showAdvancedSettings && (
         <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
           <div className="bg-bg-primary rounded-lg max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
             <div className="p-4 border-b border-border-primary flex justify-between items-center">
               <h2 className="text-lg font-medium">高级设置</h2>
               <button
                 onClick={() => setShowAdvancedSettings(false)}
                 className="btn-icon text-gray-400 hover:text-white"
               >
                 <X className="w-5 h-5" />
               </button>
             </div>
             <div className="p-6">
               <AdvancedSettingsPanel />
             </div>
           </div>
         </div>
       )}
    </aside>
  );
}
