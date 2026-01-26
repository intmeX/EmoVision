// 视频播放器组件

import { usePipelineStore } from '../../store';
import { Image as ImageIcon, Video, Camera } from 'lucide-react';

export function VideoPlayer() {
  const { currentFrame, sourceInfo, state } = usePipelineStore();
  
  // 无视觉源时的占位界面
  if (!sourceInfo) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-bg-tertiary rounded-lg">
        <div className="w-20 h-20 bg-bg-elevated rounded-full flex items-center justify-center mb-4">
          <Video className="w-10 h-10 text-gray-600" />
        </div>
        <p className="text-gray-400 text-lg">请选择视觉源</p>
        <p className="text-gray-500 text-sm mt-2">支持图像、视频文件或摄像头</p>
      </div>
    );
  }
  
  // 有视觉源但未运行
  if (!currentFrame && state === 'idle') {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-bg-tertiary rounded-lg">
        <div className="w-20 h-20 bg-bg-elevated rounded-full flex items-center justify-center mb-4">
          {sourceInfo.source_type === 'image' && <ImageIcon className="w-10 h-10 text-blue-500" />}
          {sourceInfo.source_type === 'video' && <Video className="w-10 h-10 text-green-500" />}
          {sourceInfo.source_type === 'camera' && <Camera className="w-10 h-10 text-purple-500" />}
        </div>
        <p className="text-gray-300 text-lg">
          {getSourceTypeLabel(sourceInfo.source_type)}已就绪
        </p>
        <p className="text-gray-500 text-sm mt-2">点击"启动"按钮开始识别</p>
        <div className="mt-4 text-xs text-gray-600">
          {sourceInfo.width} x {sourceInfo.height}
          {sourceInfo.fps > 0 && ` @ ${sourceInfo.fps.toFixed(1)} FPS`}
        </div>
      </div>
    );
  }
  
  // 显示实时帧
  return (
    <div className="w-full h-full flex items-center justify-center bg-black rounded-lg overflow-hidden">
      {currentFrame ? (
        <img
          src={`data:image/jpeg;base64,${currentFrame}`}
          alt="实时帧"
          className="max-w-full max-h-full object-contain"
        />
      ) : (
        <div className="text-gray-500">等待帧数据...</div>
      )}
    </div>
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
