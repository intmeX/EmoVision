"""
视觉源管理器

管理图像、视频、摄像头等视觉源的读取和控制
"""

import asyncio
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
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
        total_frames: int = 0,
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
            "current_frame": self.current_frame,
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

        # 帧队列（用于自适应帧生成器）
        self._frame_queue: deque = deque(maxlen=2)  # 最多缓存2帧
        self._queue_lock = asyncio.Lock()

        # 帧读取线程池（避免阻塞事件循环）
        self._read_executor: Optional[ThreadPoolExecutor] = None

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
            total_frames=1,
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

        # 读取第一帧
        ret, first_frame = self._capture.read()
        if ret:
            self._current_frame = first_frame

        w = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._capture.get(cv2.CAP_PROP_FPS)
        total = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))

        # 重置到开头，以便后续处理
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self._source_info = SourceInfo(
            source_type=SourceType.VIDEO,
            path=str(path),
            width=w,
            height=h,
            fps=fps,
            total_frames=total,
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
            fps=fps,
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
            return (
                True,
                self._current_frame.copy() if self._current_frame is not None else None,
            )

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
        self, target_fps: float = 30.0, skip_frames: int = 0
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
                        # 视频结束，停止流水线
                        logger.info("视频播放完毕，停止流水线")
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

    async def frame_generator_adaptive(
        self, target_fps: float = 30.0
    ) -> AsyncGenerator[Tuple[int, np.ndarray], None]:
        """
        自适应帧生成器 - 最新帧优先策略

        当推理速度跟不上视频帧率时，自动丢弃旧帧，只处理最新帧。
        这样可以保证实时性，避免延迟累积。

        Args:
            target_fps: 目标帧率

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
        last_frame_time = time.perf_counter()

        # 启动后台帧读取任务
        read_task = asyncio.create_task(self._frame_reader_loop())

        try:
            while self._is_running:
                if self._is_paused:
                    await asyncio.sleep(0.1)
                    continue

                # 从队列获取最新帧
                frame = None
                async with self._queue_lock:
                    if self._frame_queue:
                        # 取最新帧，丢弃旧帧
                        frame = self._frame_queue[-1]
                        self._frame_queue.clear()

                if frame is None:
                    # 队列空，等待新帧
                    await asyncio.sleep(0.01)
                    continue

                frame_id += 1
                yield frame_id, frame

                # 图像源只返回一帧
                if self._source_info.source_type == SourceType.IMAGE:
                    break

                # 精确帧率控制
                elapsed = time.perf_counter() - last_frame_time
                if elapsed < frame_interval:
                    await asyncio.sleep(frame_interval - elapsed)
                last_frame_time = time.perf_counter()

        finally:
            read_task.cancel()
            try:
                await read_task
            except asyncio.CancelledError:
                pass
            self._is_running = False

    async def _frame_reader_loop(self) -> None:
        """
        后台帧读取循环

        持续从视频源读取帧并放入队列。
        使用线程池执行同步的OpenCV读取，避免阻塞事件循环。

        对于视频文件：按原始帧率读取，确保时间同步
        对于摄像头：尽快读取（摄像头本身会阻塞等待下一帧）
        """
        # 创建线程池用于帧读取
        self._read_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="frame_reader"
        )
        loop = asyncio.get_event_loop()

        # 视频文件需要按原始帧率读取
        is_video_file = (
            self._source_info is not None
            and self._source_info.source_type == SourceType.VIDEO
        )

        # 获取视频原始帧率，计算帧间隔
        if is_video_file and self._source_info:
            source_fps = self._source_info.fps
            # 确保帧率有效（某些视频可能返回0或异常值）
            if source_fps <= 0 or source_fps > 240:
                source_fps = 30.0
                logger.warning(f"视频帧率无效，使用默认值: {source_fps} FPS")
            frame_interval = 1.0 / source_fps
            logger.info(
                f"视频帧读取器启动: 源帧率={source_fps:.1f} FPS, 帧间隔={frame_interval * 1000:.1f}ms"
            )
        else:
            frame_interval = 0  # 摄像头不需要帧率控制

        last_read_time = time.perf_counter()
        frames_read = 0

        try:
            while self._is_running:
                if self._is_paused:
                    await asyncio.sleep(0.1)
                    last_read_time = time.perf_counter()  # 重置时间基准
                    continue

                # 视频文件：按原始帧率控制读取速度
                if is_video_file and frame_interval > 0:
                    current_time = time.perf_counter()
                    elapsed = current_time - last_read_time
                    if elapsed < frame_interval:
                        await asyncio.sleep(frame_interval - elapsed)
                    last_read_time = time.perf_counter()

                # 在线程池中执行同步的帧读取，避免阻塞事件循环
                ret, frame = await loop.run_in_executor(
                    self._read_executor, self.read_frame
                )

                if ret and frame is not None:
                    async with self._queue_lock:
                        self._frame_queue.append(frame)
                    frames_read += 1
                else:
                    if (
                        self._source_info
                        and self._source_info.source_type == SourceType.VIDEO
                    ):
                        # 视频结束
                        logger.info(f"视频帧读取完毕，共读取 {frames_read} 帧")
                        self._is_running = False
                        break
                    await asyncio.sleep(0.01)

                # 让出控制权，确保其他协程有机会执行
                await asyncio.sleep(0)
        finally:
            # 关闭线程池
            if self._read_executor:
                self._read_executor.shutdown(wait=False)
                self._read_executor = None

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

    def get_first_frame(self) -> Optional[np.ndarray]:
        """
        获取第一帧（用于预览）

        对于图像源，返回图像本身
        对于视频源，seek到第一帧并读取

        Returns:
            第一帧图像，失败返回None
        """
        if self._source_info is None:
            return None

        if self._source_info.source_type == SourceType.IMAGE:
            return (
                self._current_frame.copy() if self._current_frame is not None else None
            )

        if self._source_info.source_type == SourceType.VIDEO:
            if self._capture is None or not self._capture.isOpened():
                return None

            # 保存当前位置
            current_pos = int(self._capture.get(cv2.CAP_PROP_POS_FRAMES))

            # 跳转到第一帧
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self._capture.read()

            # 恢复位置
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

            if ret:
                return frame

        return None

    def close(self) -> None:
        """关闭视觉源"""
        self.stop()

        # 关闭帧读取线程池
        if self._read_executor is not None:
            self._read_executor.shutdown(wait=False)
            self._read_executor = None

        if self._capture is not None:
            self._capture.release()
            self._capture = None

        self._current_frame = None
        self._source_info = None

        # 清除帧队列，防止旧帧残留
        self._frame_queue.clear()

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
