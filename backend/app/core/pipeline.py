"""
流水线编排器

协调检测器、识别器和可视化器的工作流程
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Callable, List, Optional, Tuple

import numpy as np

from ..modules.detector import BaseDetector, Detection, YOLODetector
from ..modules.recognizer import (
    BaseEmotionRecognizer,
    CaerRecognizer,
    DDENRecognizer,
    EmoticRecognizer,
    EmotionResult,
    MockEmotionRecognizer,
)
from ..modules.visualizer import FrameRenderer
from ..schemas.pipeline import PipelineConfig, RecognizerType
from ..schemas.websocket import (
    BinaryFrameHeader,
    DetectionPayload,
    EmotionPayload,
    EventMessage,
    FrameMessage,
    StatsMessage,
    StatusMessage,
)
from ..utils.frame_utils import encode_frame_bytes, encode_frame_to_jpeg
from ..utils.logger import get_logger
from .source_manager import SourceManager

logger = get_logger(__name__)

# 回调类型定义
FrameCallback = Callable[[FrameMessage], "asyncio.Future[None]"]
BinaryFrameCallback = Callable[[BinaryFrameHeader, bytes], "asyncio.Future[None]"]
StatsCallback = Callable[[StatsMessage], "asyncio.Future[None]"]
StatusCallback = Callable[[StatusMessage], "asyncio.Future[None]"]
EventCallback = Callable[[EventMessage], "asyncio.Future[None]"]


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

        # 推理线程池（用于将CPU密集任务移出事件循环）
        self._inference_executor: Optional[ThreadPoolExecutor] = None

        # 统计信息
        self._frame_count = 0
        self._start_time = 0.0
        self._last_frame_time = 0.0
        self._latency_ms = 0.0

        # 回调
        self._on_frame_callback = None
        self._on_binary_frame_callback = None  # 二进制帧回调
        self._on_stats_callback = None
        self._on_status_callback = None
        self._on_event_callback = None  # 事件回调（EOS等）

        # 是否使用二进制传输
        self._use_binary_ws = True

        # 是否使用异步推理
        self._use_async_inference = config.performance.async_inference

        # 流水线并行处理状态
        self._pending_encode: Optional[asyncio.Task] = None
        self._use_pipelined_processing = True  # 启用流水线并行处理

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

        # 初始化识别器（根据配置选择类型）
        self._recognizer = self._create_recognizer()
        self._recognizer.initialize()

        # 初始化渲染器
        self._renderer = FrameRenderer(self._config.visualizer)

        # 初始化推理线程池
        if self._use_async_inference:
            self._inference_executor = ThreadPoolExecutor(
                max_workers=2,  # 检测+识别各一个线程
                thread_name_prefix="inference",
            )
            logger.info("异步推理已启用，线程池大小: 2")

        logger.info("流水线初始化完成")

    def _create_recognizer(self) -> BaseEmotionRecognizer:
        """
        根据配置创建对应类型的情绪识别器

        Returns:
            识别器实例
        """
        recognizer_type = self._config.recognizer.recognizer_type
        config = self._config.recognizer

        recognizer_map = {
            RecognizerType.MOCK: MockEmotionRecognizer,
            RecognizerType.DDEN: DDENRecognizer,
            RecognizerType.EMOTIC: EmoticRecognizer,
            RecognizerType.CAER: CaerRecognizer,
        }

        recognizer_cls = recognizer_map.get(recognizer_type)
        if recognizer_cls is None:
            logger.warning(f"未知识别器类型: {recognizer_type}，回退到 Mock")
            recognizer_cls = MockEmotionRecognizer

        logger.info(f"创建识别器: {recognizer_type.value} ({recognizer_cls.__name__})")
        return recognizer_cls(config)

    def cleanup(self) -> None:
        """清理流水线资源"""
        logger.info("清理流水线...")

        self._source_manager.close()

        if self._detector:
            self._detector.cleanup()

        if self._recognizer:
            self._recognizer.cleanup()

        # 取消待处理的编码任务
        if self._pending_encode is not None:
            self._pending_encode.cancel()
            self._pending_encode = None

        # 关闭推理线程池
        if self._inference_executor:
            self._inference_executor.shutdown(wait=False)
            self._inference_executor = None

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

        # 如果是视频源，在启动前重置到开头
        if (
            self._source_manager.source_info
            and self._source_manager.source_info.source_type == "video"
        ):
            self._source_manager.seek(0)

        self._state = PipelineState.RUNNING
        self._frame_count = 0
        self._start_time = time.time()
        self._detector.reset_counter()

        await self._notify_status()

        logger.info("流水线开始运行")

        # 精确帧率控制变量
        target_fps = self._config.performance.target_fps
        frame_interval = 1.0 / target_fps if target_fps > 0 else 0
        logger.info(f"目标帧率: {target_fps} FPS, 帧间隔: {frame_interval:.3f} s")
        next_frame_time = time.perf_counter()

        try:
            # 根据配置选择帧生成器
            if self._config.performance.adaptive_skip:
                # 使用自适应帧生成器（最新帧优先）
                frame_gen = self._source_manager.frame_generator_adaptive(
                    target_fps=target_fps
                )
            else:
                # 使用传统帧生成器
                frame_gen = self._source_manager.frame_generator(
                    target_fps=target_fps,
                    skip_frames=self._config.performance.skip_frames,
                )

            async for frame_id, frame in frame_gen:
                if self._state != PipelineState.RUNNING:
                    break

                # 根据配置选择处理模式
                if self._use_pipelined_processing and self._use_async_inference:
                    await self._process_frame_pipelined(frame_id, frame)
                else:
                    await self._process_frame(frame_id, frame)

                # 精确帧率控制（补偿处理时间）
                next_frame_time += frame_interval
                sleep_time = next_frame_time - time.perf_counter()
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    # 处理时间超过帧间隔，重置时间基准
                    next_frame_time = time.perf_counter()

        except Exception as e:
            logger.error(f"流水线运行错误: {e}")
            self._state = PipelineState.ERROR
            await self._notify_status()
            raise

        finally:
            # 等待最后一帧的编码任务完成
            if self._pending_encode is not None:
                try:
                    await self._pending_encode
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"最后一帧编码任务错误: {e}")
                finally:
                    self._pending_encode = None

            # 流水线正常结束时（图片/视频处理完成），不发送原始预览帧
            # 前端会保留最后一帧渲染结果显示
            # 只有在用户手动停止时（stop方法）才发送预览帧

            if self._state == PipelineState.RUNNING:
                # 视频/图像正常播放完毕，发送EOS事件
                self._state = PipelineState.IDLE
                await self._notify_event("eos", "source_eof", self._frame_count)
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

        # 检查组件是否初始化
        if self._detector is None:
            logger.error("检测器未初始化")
            return
        if self._recognizer is None:
            logger.error("识别器未初始化")
            return
        if self._renderer is None:
            logger.error("渲染器未初始化")
            return

        # 根据配置选择同步或异步推理
        if self._use_async_inference and self._inference_executor:
            # 异步推理：将CPU密集任务移到线程池
            loop = asyncio.get_event_loop()

            # 1. 异步执行检测
            detections = await loop.run_in_executor(
                self._inference_executor, self._detector.detect, frame
            )

            # 2. 异步执行识别
            emotions = await loop.run_in_executor(
                self._inference_executor, self._recognizer.predict, frame, detections
            )

            # 3. 异步执行渲染和编码
            rendered_frame, image_data = await loop.run_in_executor(
                self._inference_executor,
                self._render_and_encode,
                frame,
                detections,
                emotions,
            )
        else:
            # 同步推理（原有逻辑）
            detections = self._detector.detect(frame)
            emotions = self._recognizer.predict(frame, detections)
            rendered_frame = self._renderer.render(frame, detections, emotions)
            image_data = None  # 稍后编码

        # 更新统计
        elapsed = (time.perf_counter() - start_time) * 1000
        self._latency_ms = elapsed
        self._frame_count += 1
        self._last_frame_time = time.time()

        # 构建检测和情绪载荷
        detection_payloads = [self._to_detection_payload(d) for d in detections]
        emotion_payloads = [self._to_emotion_payload(e) for e in emotions]

        # 根据配置选择传输方式
        if self._use_binary_ws and self._on_binary_frame_callback:
            # 二进制传输
            if image_data is None:
                # 同步模式下需要编码
                image_bytes = encode_frame_bytes(
                    rendered_frame, quality=self._config.performance.output_quality
                )
            else:
                # 异步模式下已经编码
                image_bytes = image_data

            # 构建二进制帧头部
            header = BinaryFrameHeader(
                timestamp=time.time(),
                frame_id=frame_id,
                image_size=len(image_bytes),
                detections=detection_payloads,
                emotions=emotion_payloads,
            )

            # 发送二进制帧
            await self._on_binary_frame_callback(header, image_bytes)

        elif self._on_frame_callback:
            # Base64传输（兼容模式）
            if image_data is None:
                image_base64 = self._renderer.encode_frame(
                    rendered_frame, quality=self._config.performance.output_quality
                )
            else:
                # 异步模式下image_data是bytes，需要转换为base64
                import base64

                image_base64 = base64.b64encode(image_data).decode("utf-8")

            # 构建消息
            frame_msg = FrameMessage(
                timestamp=time.time(),
                frame_id=frame_id,
                image=image_base64,
                detections=detection_payloads,
                emotions=emotion_payloads,
            )

            # 发送帧消息
            await self._on_frame_callback(frame_msg)

        # 定期发送统计信息
        if self._frame_count % 30 == 0:
            await self._notify_stats()

    async def _process_frame_pipelined(self, frame_id: int, frame: np.ndarray) -> None:
        """
        流水线并行处理单帧

        在推理当前帧的同时，编码并发送上一帧的结果。
        这样可以隐藏编码延迟，提高整体吞吐量。

        Args:
            frame_id: 帧ID
            frame: 图像帧
        """
        start_time = time.perf_counter()

        # 检查组件是否初始化
        if self._detector is None:
            logger.error("检测器未初始化")
            return
        if self._recognizer is None:
            logger.error("识别器未初始化")
            return
        if self._renderer is None:
            logger.error("渲染器未初始化")
            return
        if self._inference_executor is None:
            logger.error("推理线程池未初始化")
            return

        # 等待上一帧的编码任务完成
        if self._pending_encode is not None:
            try:
                await self._pending_encode
            except Exception as e:
                logger.error(f"编码任务错误: {e}")
            finally:
                self._pending_encode = None

        loop = asyncio.get_event_loop()

        # 1. 异步执行检测
        detections = await loop.run_in_executor(
            self._inference_executor, self._detector.detect, frame
        )

        # 2. 异步执行识别
        emotions = await loop.run_in_executor(
            self._inference_executor, self._recognizer.predict, frame, detections
        )

        # 更新统计
        elapsed = (time.perf_counter() - start_time) * 1000
        self._latency_ms = elapsed
        self._frame_count += 1
        self._last_frame_time = time.time()

        # 3. 启动编码和发送任务（不等待，与下一帧推理并行）
        self._pending_encode = asyncio.create_task(
            self._encode_and_send(frame_id, frame, detections, emotions)
        )

        # 定期发送统计信息
        if self._frame_count % 30 == 0:
            await self._notify_stats()

    async def _encode_and_send(
        self,
        frame_id: int,
        frame: np.ndarray,
        detections: List[Detection],
        emotions: List[EmotionResult],
    ) -> None:
        """
        编码并发送帧（在流水线模式下与推理并行执行）

        Args:
            frame_id: 帧ID
            frame: 原始帧
            detections: 检测结果
            emotions: 情绪结果
        """
        if self._renderer is None or self._inference_executor is None:
            return

        loop = asyncio.get_event_loop()

        # 异步执行渲染和编码
        rendered_frame, image_bytes = await loop.run_in_executor(
            self._inference_executor,
            self._render_and_encode,
            frame,
            detections,
            emotions,
        )

        # 构建检测和情绪载荷
        detection_payloads = [self._to_detection_payload(d) for d in detections]
        emotion_payloads = [self._to_emotion_payload(e) for e in emotions]

        # 根据配置选择传输方式
        if self._use_binary_ws and self._on_binary_frame_callback:
            # 二进制传输
            header = BinaryFrameHeader(
                timestamp=time.time(),
                frame_id=frame_id,
                image_size=len(image_bytes),
                detections=detection_payloads,
                emotions=emotion_payloads,
            )
            await self._on_binary_frame_callback(header, image_bytes)

        elif self._on_frame_callback:
            # Base64传输（兼容模式）
            import base64

            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            frame_msg = FrameMessage(
                timestamp=time.time(),
                frame_id=frame_id,
                image=image_base64,
                detections=detection_payloads,
                emotions=emotion_payloads,
            )
            await self._on_frame_callback(frame_msg)

    def _render_and_encode(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        emotions: List[EmotionResult],
    ) -> Tuple[np.ndarray, bytes]:
        """
        渲染和编码帧（在线程池中执行）

        Args:
            frame: 原始帧
            detections: 检测结果
            emotions: 情绪结果

        Returns:
            (渲染后的帧, JPEG字节数据)
        """
        if self._renderer is None:
            raise RuntimeError("渲染器未初始化")

        rendered = self._renderer.render(frame, detections, emotions)
        image_bytes = encode_frame_bytes(
            rendered, quality=self._config.performance.output_quality
        )
        return rendered, image_bytes

    def _to_detection_payload(self, detection: Detection) -> DetectionPayload:
        """转换检测结果为载荷格式"""
        return DetectionPayload(
            id=detection.id,
            type=detection.type,
            bbox=detection.bbox,
            confidence=detection.confidence,
            paired_id=detection.paired_id,
        )

    def _to_emotion_payload(self, emotion: EmotionResult) -> EmotionPayload:
        """转换情绪结果为载荷格式"""
        return EmotionPayload(
            detection_id=emotion.detection_id,
            probabilities=emotion.probabilities,
            dominant_emotion=emotion.dominant_emotion,
            confidence=emotion.confidence,
        )

    async def _notify_status(self) -> None:
        """发送状态通知"""
        if self._on_status_callback:
            status_msg = StatusMessage(
                timestamp=time.time(),
                pipeline_state=self._state.value,
                source_info=self._source_manager.source_info.to_dict()
                if self._source_manager.source_info
                else None,
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
                detection_count=self._frame_count,
            )
            await self._on_stats_callback(stats_msg)

    async def _notify_event(
        self, name: str, reason: str | None = None, frame_id: int | None = None
    ) -> None:
        """发送事件通知（EOS等生命周期事件）"""
        if self._on_event_callback:
            event_msg = EventMessage(
                timestamp=time.time(),
                name=name,  # type: ignore
                reason=reason,  # type: ignore
                frame_id=frame_id,
            )
            await self._on_event_callback(event_msg)
            logger.info(f"发送事件: {name}, reason={reason}, frame_id={frame_id}")

    async def pause(self) -> None:
        """暂停流水线"""
        if self._state == PipelineState.RUNNING:
            self._state = PipelineState.PAUSED
            self._source_manager.pause()
            logger.info("流水线已暂停")
            # 通知状态改变
            if self._on_status_callback:
                await self._notify_status()

    async def resume(self) -> None:
        """恢复流水线"""
        if self._state == PipelineState.PAUSED:
            self._state = PipelineState.RUNNING
            self._source_manager.resume()
            logger.info("流水线已恢复")
            # 通知状态改变
            if self._on_status_callback:
                await self._notify_status()

    async def stop(self) -> None:
        """停止流水线"""
        self._state = PipelineState.IDLE
        self._source_manager.stop()

        # 取消待处理的编码任务，防止旧帧在停止后被发送
        if self._pending_encode is not None:
            self._pending_encode.cancel()
            try:
                await self._pending_encode
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"取消编码任务时出错: {e}")
            finally:
                self._pending_encode = None

        logger.info("流水线已停止")
        # 通知状态改变
        if self._on_status_callback:
            await self._notify_status()

        # 如果有当前源的信息（视频或图像），获取第一帧并发送预览
        if self._source_manager.source_info and self._on_frame_callback:
            source_info = self._source_manager.source_info
            if source_info.source_type in ["image", "video"]:
                # 获取第一帧作为预览
                first_frame = self._source_manager.get_first_frame()
                if first_frame is not None:
                    # 编码第一帧
                    image_base64 = encode_frame_to_jpeg(first_frame, quality=80)

                    # 构建预览帧消息
                    preview_message = FrameMessage(
                        timestamp=time.time(),
                        frame_id=0,  # 预览帧ID为0
                        image=image_base64,
                        detections=[],  # 空检测列表
                        emotions=[],  # 空情绪列表
                    )

                    # 发送预览帧
                    asyncio.create_task(self._on_frame_callback(preview_message))

    def set_callbacks(
        self,
        on_frame=None,
        on_binary_frame=None,
        on_stats=None,
        on_status=None,
        on_event=None,
    ) -> None:
        """
        设置回调函数

        Args:
            on_frame: 帧数据回调（Base64模式）
            on_binary_frame: 二进制帧数据回调（header, bytes）
            on_stats: 统计信息回调
            on_status: 状态变更回调
            on_event: 事件回调（EOS等生命周期事件）
        """
        self._on_frame_callback = on_frame
        self._on_binary_frame_callback = on_binary_frame
        self._on_stats_callback = on_stats
        self._on_status_callback = on_status
        self._on_event_callback = on_event

        # 如果设置了二进制回调，优先使用二进制传输
        if on_binary_frame:
            self._use_binary_ws = True
        elif on_frame:
            self._use_binary_ws = False
