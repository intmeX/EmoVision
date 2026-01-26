"""
视觉源管理器

管理图像、视频、摄像头等视觉源的读取和控制
"""

import asyncio
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator, Optional, Tuple, Union

import cv2
import numpy as np

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SourceType(str, Enum):
    """视觉源类型"""
    IMAGE = "image"
    VIDEO = "video"
    CAMERA = "camera"


class SourceInfo:
    """视觉源信息"""
    
    def __init__(
        self,
        source_type: SourceType,
        path: Optional[str] = None,
        camera_id: Optional[int] = None,
        width: int = 0,
        height: int = 0,
        fps: float = 0.0,
        total_frames: int = 0
    ):
        self.source_type = source_type
        self.path = path
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.total_frames = total_frames
        self.current_frame = 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "source_type": self.source_type.value,
            "path": self.path,
            "camera_id": self.camera_id,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "total_frames": self.total_frames,
            "current_frame": self.current_frame
        }


class SourceManager:
    """
    视觉源管理器
    
    统一管理图像、视频文件和摄像头的读取
    """
    
    def __init__(self):
        self._capture: Optional[cv2.VideoCapture] = None
        self._source_info: Optional[SourceInfo] = None
        self._is_running = False
        self._is_paused = False
        self._current_frame: Optional[np.ndarray] = None
        self._lock = asyncio.Lock()
    
    @property
    def source_info(self) -> Optional[SourceInfo]:
        """获取当前源信息"""
        return self._source_info
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running
    
    @property
    def is_paused(self) -> bool:
        """是否已暂停"""
        return self._is_paused
    
    def open_image(self, path: Union[str, Path]) -> bool:
        """
        打开图像文件
        
        Args:
            path: 图像文件路径
            
        Returns:
            是否成功打开
        """
        self.close()
        
        path = Path(path)
        if not path.exists():
            logger.error(f"图像文件不存在: {path}")
            return False
        
        image = cv2.imread(str(path))
        if image is None:
            logger.error(f"无法读取图像: {path}")
            return False
        
        self._current_frame = image
        h, w = image.shape[:2]
        
        self._source_info = SourceInfo(
            source_type=SourceType.IMAGE,
            path=str(path),
            width=w,
            height=h,
            total_frames=1
        )
        
        logger.info(f"已打开图像: {path} ({w}x{h})")
        return True
    
    def open_video(self, path: Union[str, Path]) -> bool:
        """
        打开视频文件
        
        Args:
            path: 视频文件路径
            
        Returns:
            是否成功打开
        """
        self.close()
        
        path = Path(path)
        if not path.exists():
            logger.error(f"视频文件不存在: {path}")
            return False
        
        self._capture = cv2.VideoCapture(str(path))
        if not self._capture.isOpened():
            logger.error(f"无法打开视频: {path}")
            return False
        
        w = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._capture.get(cv2.CAP_PROP_FPS)
        total = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self._source_info = SourceInfo(
            source_type=SourceType.VIDEO,
            path=str(path),
            width=w,
            height=h,
            fps=fps,
            total_frames=total
        )
        
        logger.info(f"已打开视频: {path} ({w}x{h}, {fps:.1f}fps, {total}帧)")
        return True
    
    def open_camera(self, camera_id: int = 0) -> bool:
        """
        打开摄像头
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            是否成功打开
        """
        self.close()
        
        self._capture = cv2.VideoCapture(camera_id)
        if not self._capture.isOpened():
            logger.error(f"无法打开摄像头: {camera_id}")
            return False
        
        w = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._capture.get(cv2.CAP_PROP_FPS) or 30.0
        
        self._source_info = SourceInfo(
            source_type=SourceType.CAMERA,
            camera_id=camera_id,
            width=w,
            height=h,
            fps=fps
        )
        
        logger.info(f"已打开摄像头: {camera_id} ({w}x{h}, {fps:.1f}fps)")
        return True
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        读取一帧
        
        Returns:
            (是否成功, 帧数据)
        """
        if self._source_info is None:
            return False, None
        
        if self._source_info.source_type == SourceType.IMAGE:
            # 图像源总是返回同一帧
            return True, self._current_frame.copy() if self._current_frame is not None else None
        
        if self._capture is None or not self._capture.isOpened():
            return False, None
        
        ret, frame = self._capture.read()
        if ret:
            self._current_frame = frame
            if self._source_info:
                self._source_info.current_frame = int(
                    self._capture.get(cv2.CAP_PROP_POS_FRAMES)
                )
        
        return ret, frame
    
    async def frame_generator(
        self,
        target_fps: float = 30.0,
        skip_frames: int = 0
    ) -> AsyncGenerator[Tuple[int, np.ndarray], None]:
        """
        异步帧生成器
        
        Args:
            target_fps: 目标帧率
            skip_frames: 跳帧数
            
        Yields:
            (帧ID, 帧数据)
        """
        if self._source_info is None:
            logger.error("未打开任何视觉源")
            return
        
        self._is_running = True
        self._is_paused = False
        frame_id = 0
        frame_interval = 1.0 / target_fps if target_fps > 0 else 0
        skip_counter = 0
        
        try:
            while self._is_running:
                if self._is_paused:
                    await asyncio.sleep(0.1)
                    continue
                
                async with self._lock:
                    ret, frame = self.read_frame()
                
                if not ret or frame is None:
                    if self._source_info.source_type == SourceType.VIDEO:
                        # 视频结束
                        logger.info("视频播放完毕")
                        break
                    else:
                        # 摄像头读取失败，稍后重试
                        await asyncio.sleep(0.1)
                        continue
                
                # 跳帧处理
                if skip_frames > 0:
                    skip_counter += 1
                    if skip_counter <= skip_frames:
                        continue
                    skip_counter = 0
                
                frame_id += 1
                yield frame_id, frame
                
                # 图像源只返回一帧
                if self._source_info.source_type == SourceType.IMAGE:
                    break
                
                # 控制帧率
                if frame_interval > 0:
                    await asyncio.sleep(frame_interval)
        
        finally:
            self._is_running = False
    
    def pause(self) -> None:
        """暂停读取"""
        self._is_paused = True
        logger.info("视觉源已暂停")
    
    def resume(self) -> None:
        """恢复读取"""
        self._is_paused = False
        logger.info("视觉源已恢复")
    
    def stop(self) -> None:
        """停止读取"""
        self._is_running = False
        logger.info("视觉源已停止")
    
    def seek(self, frame_number: int) -> bool:
        """
        跳转到指定帧 (仅视频)
        
        Args:
            frame_number: 目标帧号
            
        Returns:
            是否成功
        """
        if self._capture is None or self._source_info is None:
            return False
        
        if self._source_info.source_type != SourceType.VIDEO:
            return False
        
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self._source_info.current_frame = frame_number
        return True
    
    def close(self) -> None:
        """关闭视觉源"""
        self.stop()
        
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        
        self._current_frame = None
        self._source_info = None
        logger.info("视觉源已关闭")
    
    @staticmethod
    def list_cameras(max_cameras: int = 10) -> list[int]:
        """
        列出可用的摄像头
        
        Args:
            max_cameras: 最大检测数量
            
        Returns:
            可用摄像头ID列表
        """
        available = []
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available
