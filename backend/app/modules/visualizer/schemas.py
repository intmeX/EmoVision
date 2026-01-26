"""可视化相关数据模型"""

from pydantic import BaseModel, Field


class RenderOptions(BaseModel):
    """渲染选项"""
    jpeg_quality: int = Field(default=80, ge=10, le=100, description="JPEG压缩质量")
    resize_factor: float = Field(default=1.0, ge=0.1, le=2.0, description="缩放因子")
    draw_face_bbox: bool = Field(default=True, description="绘制人脸边界框")
    draw_person_bbox: bool = Field(default=False, description="绘制人体边界框")
