"""边界框平滑器

使用 One Euro Filter 对边界框坐标进行自适应平滑。
"""

from ...schemas.common import BoundingBox
from .one_euro_filter import OneEuroFilter


class BboxSmoother:
    """
    边界框平滑器

    为边界框的每个坐标维度（cx, cy, w, h）维护独立的 One Euro Filter。
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ):
        """
        初始化边界框平滑器

        Args:
            min_cutoff: 最小截止频率
            beta: 速度系数
            d_cutoff: 导数截止频率
        """
        self.filters = {
            "cx": OneEuroFilter(min_cutoff, beta, d_cutoff),
            "cy": OneEuroFilter(min_cutoff, beta, d_cutoff),
            "w": OneEuroFilter(min_cutoff, beta * 0.5, d_cutoff),  # 尺寸变化更保守
            "h": OneEuroFilter(min_cutoff, beta * 0.5, d_cutoff),
        }

    def smooth(self, bbox: BoundingBox, timestamp: float) -> BoundingBox:
        """
        对边界框进行平滑

        Args:
            bbox: 原始边界框
            timestamp: 当前时间戳

        Returns:
            平滑后的边界框
        """
        # 计算中心点
        cx, cy = bbox.center

        # 对每个维度进行平滑
        cx_smooth = self.filters["cx"](cx, timestamp)
        cy_smooth = self.filters["cy"](cy, timestamp)
        w_smooth = self.filters["w"](bbox.width, timestamp)
        h_smooth = self.filters["h"](bbox.height, timestamp)

        # 从中心点和尺寸重建边界框
        x_smooth = cx_smooth - w_smooth / 2
        y_smooth = cy_smooth - h_smooth / 2

        return BoundingBox(
            x=x_smooth,
            y=y_smooth,
            width=w_smooth,
            height=h_smooth,
        )

    def reset(self) -> None:
        """重置所有滤波器"""
        for f in self.filters.values():
            f.reset()
