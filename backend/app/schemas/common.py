"""通用数据模型"""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field


DataT = TypeVar("DataT")


class BoundingBox(BaseModel):
    """边界框模型"""
    x: float = Field(..., description="左上角X坐标")
    y: float = Field(..., description="左上角Y坐标")
    width: float = Field(..., description="宽度")
    height: float = Field(..., description="高度")
    
    @property
    def x2(self) -> float:
        """右下角X坐标"""
        return self.x + self.width
    
    @property
    def y2(self) -> float:
        """右下角Y坐标"""
        return self.y + self.height
    
    @property
    def center(self) -> tuple[float, float]:
        """中心点坐标"""
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def area(self) -> float:
        """面积"""
        return self.width * self.height
    
    def to_xyxy(self) -> tuple[float, float, float, float]:
        """转换为 (x1, y1, x2, y2) 格式"""
        return (self.x, self.y, self.x2, self.y2)
    
    def to_xywh(self) -> tuple[float, float, float, float]:
        """转换为 (x, y, w, h) 格式"""
        return (self.x, self.y, self.width, self.height)
    
    @classmethod
    def from_xyxy(cls, x1: float, y1: float, x2: float, y2: float) -> "BoundingBox":
        """从 (x1, y1, x2, y2) 格式创建"""
        return cls(x=x1, y=y1, width=x2 - x1, height=y2 - y1)
    
    def iou(self, other: "BoundingBox") -> float:
        """计算与另一个边界框的IoU"""
        # 计算交集
        inter_x1 = max(self.x, other.x)
        inter_y1 = max(self.y, other.y)
        inter_x2 = min(self.x2, other.x2)
        inter_y2 = min(self.y2, other.y2)
        
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
        
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        union_area = self.area + other.area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0


class ApiResponse(BaseModel, Generic[DataT]):
    """统一API响应模型"""
    success: bool = Field(default=True, description="请求是否成功")
    message: str = Field(default="", description="响应消息")
    data: Optional[DataT] = Field(default=None, description="响应数据")
    timestamp: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="响应时间戳"
    )


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(default=False)
    error_code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")
    details: Optional[dict[str, Any]] = Field(default=None, description="详细信息")
    timestamp: float = Field(
        default_factory=lambda: datetime.now().timestamp()
    )
