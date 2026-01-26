"""数据模型模块"""

from .common import ApiResponse, BoundingBox, ErrorResponse
from .pipeline import (
    DetectorConfig,
    ModelSize,
    PerformanceConfig,
    PipelineConfig,
    RecognizerConfig,
    VisualizerConfig,
)
from .websocket import (
    ControlMessage,
    DetectionPayload,
    EmotionPayload,
    ErrorMessage,
    FrameMessage,
    StatsMessage,
    StatusMessage,
    WSMessage,
)

__all__ = [
    # common
    "BoundingBox",
    "ApiResponse",
    "ErrorResponse",
    # pipeline
    "ModelSize",
    "DetectorConfig",
    "RecognizerConfig",
    "VisualizerConfig",
    "PerformanceConfig",
    "PipelineConfig",
    # websocket
    "DetectionPayload",
    "EmotionPayload",
    "FrameMessage",
    "StatusMessage",
    "StatsMessage",
    "ErrorMessage",
    "ControlMessage",
    "WSMessage",
]
