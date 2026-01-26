// 视觉源选择器组件

import { useState, useRef } from 'react';
import { Upload, Camera, FolderOpen, X } from 'lucide-react';
import { usePipeline } from '../../hooks';
import clsx from 'clsx';

interface SourceSelectorProps {
  onClose?: () => void;
}

export function SourceSelector({ onClose }: SourceSelectorProps) {
  const { uploadFile, setCamera, isLoading } = usePipeline();
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };
  
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const file = e.dataTransfer.files[0];
    if (file) {
      await uploadFile(file);
      onClose?.();
    }
  };
  
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await uploadFile(file);
      onClose?.();
    }
  };
  
  const handleCameraClick = async () => {
    await setCamera(0);
    onClose?.();
  };
  
  return (
    <div className="bg-bg-secondary rounded-lg p-6 w-full max-w-md">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">选择视觉源</h2>
        {onClose && (
          <button onClick={onClose} className="btn-icon text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>
      
      {/* 拖拽上传区域 */}
      <div
        className={clsx(
          'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
          dragActive
            ? 'border-accent-primary bg-accent-primary/10'
            : 'border-border-secondary hover:border-border-primary'
        )}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <Upload className="w-12 h-12 mx-auto mb-4 text-gray-500" />
        <p className="text-gray-300 mb-2">拖拽文件到此处</p>
        <p className="text-sm text-gray-500 mb-4">或者</p>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading}
          className="btn-primary"
        >
          <FolderOpen className="w-4 h-4 mr-2 inline" />
          选择文件
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,video/*"
          onChange={handleFileSelect}
          className="hidden"
        />
        <p className="text-xs text-gray-500 mt-4">
          支持: JPG, PNG, MP4, AVI, MOV
        </p>
      </div>
      
      {/* 分隔线 */}
      <div className="flex items-center gap-4 my-6">
        <div className="flex-1 h-px bg-border-primary" />
        <span className="text-sm text-gray-500">或者使用</span>
        <div className="flex-1 h-px bg-border-primary" />
      </div>
      
      {/* 摄像头选项 */}
      <button
        onClick={handleCameraClick}
        disabled={isLoading}
        className="w-full flex items-center gap-4 p-4 bg-bg-tertiary rounded-lg hover:bg-bg-elevated transition-colors"
      >
        <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
          <Camera className="w-6 h-6 text-purple-400" />
        </div>
        <div className="text-left">
          <p className="text-gray-200 font-medium">摄像头</p>
          <p className="text-sm text-gray-500">使用设备摄像头实时识别</p>
        </div>
      </button>
    </div>
  );
}
