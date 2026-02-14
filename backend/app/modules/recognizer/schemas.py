"""情绪识别相关数据模型"""

from pydantic import BaseModel, Field


class EmotionResult(BaseModel):
    """单个目标的情绪识别结果"""

    detection_id: int = Field(..., description="关联的检测目标ID")
    probabilities: dict[str, float] = Field(..., description="各情绪类别的概率分布")
    dominant_emotion: str = Field(..., description="主导情绪类别")
    confidence: float = Field(..., ge=0.0, le=1.0, description="识别置信度")


class RecognitionResult(BaseModel):
    """帧情绪识别结果"""

    frame_id: int = Field(..., description="帧ID")
    results: list[EmotionResult] = Field(
        default_factory=list, description="情绪识别结果列表"
    )
    inference_time_ms: float = Field(..., description="推理时间(毫秒)")
