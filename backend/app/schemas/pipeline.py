"""流水线配置数据模型"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ModelSize(str, Enum):
    """YOLO模型尺寸"""
    NANO = "n"
    SMALL = "s"
    MEDIUM = "m"
    LARGE = "l"
    XLARGE = "x"


class DetectorConfig(BaseModel):
    """目标检测器配置"""
    model_size: ModelSize = Field(
        default=ModelSize.NANO,
        description="模型尺寸: n/s/m/l/x"
    )
    confidence_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="置信度阈值"
    )
    iou_threshold: float = Field(
        default=0.45, ge=0.0, le=1.0,
        description="NMS IOU阈值"
    )
    detect_face: bool = Field(
        default=True,
        description="是否检测人脸"
    )
    detect_person: bool = Field(
        default=True,
        description="是否检测人体"
    )
    max_detections: int = Field(
        default=100, ge=1, le=300,
        description="最大检测数量"
    )


class RecognizerConfig(BaseModel):
    """情绪识别器配置"""
    model_path: Optional[str] = Field(
        default=None,
        description="模型权重文件路径"
    )
    emotion_labels: list[str] = Field(
        default=["happy", "sad", "angry", "fear", "surprise", "disgust", "neutral"],
        description="情绪类别标签列表"
    )
    batch_size: int = Field(
        default=8, ge=1, le=64,
        description="批处理大小"
    )
    use_face: bool = Field(
        default=True,
        description="使用人脸区域特征"
    )
    use_body: bool = Field(
        default=True,
        description="使用人体区域特征"
    )


class VisualizerConfig(BaseModel):
    """可视化渲染器配置"""
    show_bounding_box: bool = Field(default=True, description="显示边界框")
    show_emotion_label: bool = Field(default=True, description="显示情绪标签")
    show_confidence: bool = Field(default=True, description="显示置信度")
    show_emotion_bar: bool = Field(default=False, description="显示情绪概率条")
    box_color_by_emotion: bool = Field(default=True, description="边框颜色按情绪变化")
    font_scale: float = Field(default=1.5, ge=0.1, le=3.0, description="字体大小")
    box_thickness: int = Field(default=2, ge=1, le=10, description="边框粗细")
    emotion_colors: dict[str, str] = Field(
        default={
            "happy": "#22c55e",
            "sad": "#3b82f6",
            "angry": "#ef4444",
            "fear": "#a855f7",
            "surprise": "#f59e0b",
            "disgust": "#84cc16",
            "neutral": "#6b7280"
        },
        description="各情绪对应的颜色"
    )


class PerformanceConfig(BaseModel):
    """性能配置"""
    target_fps: int = Field(default=0, ge=-1, le=120, description="目标帧率")
    skip_frames: int = Field(default=0, ge=0, le=10, description="跳帧数")
    async_inference: bool = Field(default=True, description="异步推理")
    output_quality: int = Field(default=80, ge=10, le=100, description="输出JPEG质量")

    # 新增性能参数
    use_binary_ws: bool = Field(default=True, description="使用二进制WebSocket传输")
    inference_threads: int = Field(default=2, ge=1, le=4, description="推理线程数")
    frame_buffer_size: int = Field(default=2, ge=1, le=5, description="帧缓冲区大小")
    adaptive_skip: bool = Field(default=True, description="自适应跳帧（最新帧优先）")


class PipelineConfig(BaseModel):
    """完整流水线配置"""
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    recognizer: RecognizerConfig = Field(default_factory=RecognizerConfig)
    visualizer: VisualizerConfig = Field(default_factory=VisualizerConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
