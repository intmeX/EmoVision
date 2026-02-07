"""WebSocket消息数据模型"""

from typing import Literal, Union

from pydantic import BaseModel, Field

from .common import BoundingBox


class DetectionPayload(BaseModel):
    """检测结果载荷"""
    id: int = Field(..., description="检测目标ID")
    type: Literal["face", "person"] = Field(..., description="检测类型")
    bbox: BoundingBox = Field(..., description="边界框")
    confidence: float = Field(..., description="置信度")
    paired_id: int | None = Field(default=None, description="关联的face/person ID")


class EmotionPayload(BaseModel):
    """情绪识别结果载荷"""
    detection_id: int = Field(..., description="关联的检测目标ID")
    probabilities: dict[str, float] = Field(..., description="各情绪类别概率")
    dominant_emotion: str = Field(..., description="主导情绪")
    confidence: float = Field(..., description="置信度")


class FrameMessage(BaseModel):
    """帧数据消息"""
    type: Literal["frame"] = "frame"
    timestamp: float = Field(..., description="时间戳")
    frame_id: int = Field(..., description="帧ID")
    image: str = Field(..., description="Base64编码的JPEG图像")
    detections: list[DetectionPayload] = Field(default_factory=list)
    emotions: list[EmotionPayload] = Field(default_factory=list)


class BinaryFrameHeader(BaseModel):
    """二进制帧头部消息（用于二进制WebSocket传输）

    传输协议：
    1. 先发送此JSON头部
    2. 紧接着发送二进制JPEG图像数据
    """
    type: Literal["frame_header"] = "frame_header"
    timestamp: float = Field(..., description="时间戳")
    frame_id: int = Field(..., description="帧ID")
    image_size: int = Field(..., description="图像字节数")
    detections: list[DetectionPayload] = Field(default_factory=list)
    emotions: list[EmotionPayload] = Field(default_factory=list)


class StatusMessage(BaseModel):
    """状态消息"""
    type: Literal["status"] = "status"
    timestamp: float = Field(..., description="时间戳")
    pipeline_state: Literal["idle", "running", "paused", "error"] = Field(
        ..., description="流水线状态"
    )
    source_info: dict | None = Field(default=None, description="源信息")


class StatsMessage(BaseModel):
    """统计消息"""
    type: Literal["stats"] = "stats"
    timestamp: float = Field(..., description="时间戳")
    fps: float = Field(..., description="当前帧率")
    latency_ms: float = Field(..., description="延迟(毫秒)")
    detection_count: int = Field(..., description="检测数量")
    gpu_usage: float | None = Field(default=None, description="GPU使用率")


class ErrorMessage(BaseModel):
    """错误消息"""
    type: Literal["error"] = "error"
    timestamp: float = Field(..., description="时间戳")
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")
    details: dict | None = Field(default=None, description="详细信息")


class ControlMessage(BaseModel):
    """控制消息(客户端发送)"""
    action: Literal["start", "stop", "pause", "resume"] = Field(
        ..., description="控制动作"
    )


class EventMessage(BaseModel):
    """事件消息（用于EOS等生命周期事件）"""
    type: Literal["event"] = "event"
    timestamp: float = Field(..., description="时间戳")
    name: Literal["eos", "recording_started", "recording_stopped"] = Field(
        ..., description="事件名称"
    )
    reason: Literal["source_eof", "user_stop", "error"] | None = Field(
        default=None, description="事件原因"
    )
    frame_id: int | None = Field(default=None, description="相关帧ID")


# WebSocket消息联合类型
WSMessage = Union[FrameMessage, StatusMessage, StatsMessage, ErrorMessage, EventMessage]
