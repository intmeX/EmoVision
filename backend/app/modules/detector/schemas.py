"""检测器相关数据模型"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from ...schemas.common import BoundingBox


class DetectionType(str, Enum):
    """检测类型枚举"""
    FACE = "face"
    PERSON = "person"


class Detection(BaseModel):
    """单个检测结果"""
    id: int = Field(..., description="检测目标ID")
    type: DetectionType = Field(..., description="检测类型")
    bbox: BoundingBox = Field(..., description="边界框")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    paired_id: Optional[int] = Field(default=None, description="配对的目标ID")
    
    class Config:
        use_enum_values = True


class DetectionResult(BaseModel):
    """帧检测结果"""
    frame_id: int = Field(..., description="帧ID")
    detections: list[Detection] = Field(default_factory=list, description="检测列表")
    inference_time_ms: float = Field(..., description="推理时间(毫秒)")
