"""
流水线编排器

协调检测器、识别器和可视化器的工作流程
"""

import asyncio
import time
from enum import Enum
from typing import List, Optional

import numpy as np

from ..modules.detector import BaseDetector, Detection, YOLODetector
from ..modules.recognizer import BaseEmotionRecognizer, EmotionResult, MockEmotionRecognizer
from ..modules.visualizer import FrameRenderer
from ..schemas.pipeline import PipelineConfig
from ..schemas.websocket import (
    DetectionPayload,
    EmotionPayload,
    FrameMessage,
    StatsMessage,
    StatusMessage,
)
from ..utils.logger import get_logger
from .source_manager import SourceManager

logger = get_logger(__name__)


class PipelineState(str, Enum):
    """流水线状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class Pipeline:
    """
    流水线编排器
    
    协调视觉源、检测器、识别器和可视化器的完整工作流程
    """
    
    def __init__(self, config: PipelineConfig):
        """
        初始化流水线
        
        Args:
            config: 流水线配置
        """
        self._config = config
        self._state = PipelineState.IDLE
        
        # 组件
        self._source_manager = SourceManager()
        self._detector: Optional[BaseDetector] = None
        self._recognizer: Optional[BaseEmotionRecognizer] = None
        self._renderer: Optional[FrameRenderer] = None
        
        # 统计信息
        self._frame_count = 0
        self._start_time = 0.0
        self._last_frame_time = 0.0
        self._latency_ms = 0.0
        
        # 回调
        self._on_frame_callback = None
        self._on_stats_callback = None
        self._on_status_callback = None
    
    @property
    def state(self) -> PipelineState:
        """获取流水线状态"""
        return self._state
    
    @property
    def source_manager(self) -> SourceManager:
        """获取视觉源管理器"""
        return self._source_manager
    
    @property
    def config(self) -> PipelineConfig:
        """获取当前配置"""
        return self._config
    
    def initialize(self) -> None:
        """初始化流水线组件"""
        logger.info("初始化流水线...")
        
        # 初始化检测器
        self._detector = YOLODetector(self._config.detector)
        self._detector.initialize()
        
        # 初始化识别器 (使用模拟识别器)
        self._recognizer = MockEmotionRecognizer(self._config.recognizer)
        self._recognizer.initialize()
        
        # 初始化渲染器
        self._renderer = FrameRenderer(self._config.visualizer)
        
        logger.info("流水线初始化完成")
    
    def cleanup(self) -> None:
        """清理流水线资源"""
        logger.info("清理流水线...")
        
        self._source_manager.close()
        
        if self._detector:
            self._detector.cleanup()
        
        if self._recognizer:
            self._recognizer.cleanup()
        
        self._state = PipelineState.IDLE
        logger.info("流水线已清理")
    
    def update_config(self, config: PipelineConfig) -> None:
        """
        更新流水线配置
        
        Args:
            config: 新配置
        """
        self._config = config
        
        if self._detector:
            self._detector.update_config(config.detector)
        
        if self._recognizer:
            self._recognizer.update_config(config.recognizer)
        
        if self._renderer:
            self._renderer.update_config(config.visualizer)
        
        logger.info("流水线配置已更新")
    
    async def run(self) -> None:
        """运行流水线主循环"""
        if self._state == PipelineState.RUNNING:
            logger.warning("流水线已在运行中")
            return
        
        if not self._detector or not self._recognizer:
            raise RuntimeError("流水线未初始化")
        
        self._state = PipelineState.RUNNING
        self._frame_count = 0
        self._start_time = time.time()
        self._detector.reset_counter()
        
        await self._notify_status()
        
        logger.info("流水线开始运行")
        
        try:
            async for frame_id, frame in self._source_manager.frame_generator(
                target_fps=self._config.performance.target_fps,
                skip_frames=self._config.performance.skip_frames
            ):
                if self._state != PipelineState.RUNNING:
                    break
                
                await self._process_frame(frame_id, frame)
        
        except Exception as e:
            logger.error(f"流水线运行错误: {e}")
            self._state = PipelineState.ERROR
            await self._notify_status()
            raise
        
        finally:
            if self._state == PipelineState.RUNNING:
                self._state = PipelineState.IDLE
            await self._notify_status()
            logger.info("流水线已停止")
    
    async def _process_frame(self, frame_id: int, frame: np.ndarray) -> None:
        """
        处理单帧
        
        Args:
            frame_id: 帧ID
            frame: 图像帧
        """
        start_time = time.perf_counter()
        
        # 1. 目标检测
        if self._detector is None:
            logger.error("检测器未初始化")
            return
            
        detections = self._detector.detect(frame)
        
        # 2. 情绪识别
        if self._recognizer is None:
            logger.error("识别器未初始化")
            return
            
        emotions = self._recognizer.predict(frame, detections)
        
        # 3. 可视化渲染
        if self._renderer is None:
            logger.error("渲染器未初始化")
            return
            
        rendered_frame = self._renderer.render(frame, detections, emotions)
        
        # 4. 编码
        image_base64 = self._renderer.encode_frame(
            rendered_frame,
            quality=self._config.performance.output_quality
        )
        
        # 更新统计
        elapsed = (time.perf_counter() - start_time) * 1000
        self._latency_ms = elapsed
        self._frame_count += 1
        self._last_frame_time = time.time()
        
        # 构建消息
        frame_msg = FrameMessage(
            timestamp=time.time(),
            frame_id=frame_id,
            image=image_base64,
            detections=[self._to_detection_payload(d) for d in detections],
            emotions=[self._to_emotion_payload(e) for e in emotions]
        )

        # logger.info(f"处理帧 {frame_id}，耗时 {elapsed:.2f} ms")
        # 发送帧消息
        if self._on_frame_callback:
            # logger.debug("发送帧消息")
            await self._on_frame_callback(frame_msg)
        
        # 定期发送统计信息
        if self._frame_count % 30 == 0:
            # logger.debug("发送统计消息")
            await self._notify_stats()
    
    def _to_detection_payload(self, detection: Detection) -> DetectionPayload:
        """转换检测结果为载荷格式"""
        return DetectionPayload(
            id=detection.id,
            type=detection.type,
            bbox=detection.bbox,
            confidence=detection.confidence,
            paired_id=detection.paired_id
        )
    
    def _to_emotion_payload(self, emotion: EmotionResult) -> EmotionPayload:
        """转换情绪结果为载荷格式"""
        return EmotionPayload(
            detection_id=emotion.detection_id,
            probabilities=emotion.probabilities,
            dominant_emotion=emotion.dominant_emotion,
            confidence=emotion.confidence
        )
    
    async def _notify_status(self) -> None:
        """发送状态通知"""
        if self._on_status_callback:
            status_msg = StatusMessage(
                timestamp=time.time(),
                pipeline_state=self._state.value,
                source_info=self._source_manager.source_info.to_dict()
                if self._source_manager.source_info else None
            )
            await self._on_status_callback(status_msg)
    
    async def _notify_stats(self) -> None:
        """发送统计信息"""
        if self._on_stats_callback:
            elapsed_time = time.time() - self._start_time
            fps = self._frame_count / elapsed_time if elapsed_time > 0 else 0
            
            stats_msg = StatsMessage(
                timestamp=time.time(),
                fps=round(fps, 1),
                latency_ms=round(self._latency_ms, 1),
                detection_count=self._frame_count
            )
            await self._on_stats_callback(stats_msg)
    
    def pause(self) -> None:
        """暂停流水线"""
        if self._state == PipelineState.RUNNING:
            self._state = PipelineState.PAUSED
            self._source_manager.pause()
            logger.info("流水线已暂停")
    
    def resume(self) -> None:
        """恢复流水线"""
        if self._state == PipelineState.PAUSED:
            self._state = PipelineState.RUNNING
            self._source_manager.resume()
            logger.info("流水线已恢复")
    
    def stop(self) -> None:
        """停止流水线"""
        self._state = PipelineState.IDLE
        self._source_manager.stop()
        logger.info("流水线已停止")
    
    def set_callbacks(
        self,
        on_frame=None,
        on_stats=None,
        on_status=None
    ) -> None:
        """
        设置回调函数
        
        Args:
            on_frame: 帧数据回调
            on_stats: 统计信息回调
            on_status: 状态变更回调
        """
        self._on_frame_callback = on_frame
        self._on_stats_callback = on_stats
        self._on_status_callback = on_status
