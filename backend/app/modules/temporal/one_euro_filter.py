"""One Euro Filter 实现

自适应低通滤波器，根据信号速度动态调整平滑强度。
用于边界框坐标的平滑处理，减少抖动同时保持响应性。
"""

import math


class OneEuroFilter:
    """
    One Euro Filter - 自适应低通滤波器

    根据信号变化速度自适应调整截止频率：
    - 慢速运动 -> 更强平滑（减少抖动）
    - 快速运动 -> 更弱平滑（减少延迟）
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ):
        """
        初始化 One Euro Filter

        Args:
            min_cutoff: 最小截止频率（越小越平滑）
            beta: 速度系数（越大对快速运动响应越快）
            d_cutoff: 导数截止频率
        """
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        # 状态变量
        self.x_prev: float | None = None
        self.dx_prev: float = 0.0
        self.t_prev: float | None = None

    def _smoothing_factor(self, dt: float, cutoff: float) -> float:
        """计算平滑因子 alpha"""
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / max(dt, 1e-6))

    def __call__(self, x: float, t: float) -> float:
        """
        对信号进行滤波

        Args:
            x: 当前信号值
            t: 当前时间戳

        Returns:
            滤波后的信号值
        """
        # 首次调用，直接返回
        if self.t_prev is None or self.x_prev is None:
            self.x_prev = x
            self.t_prev = t
            return x

        # 计算时间间隔
        dt = t - self.t_prev
        if dt <= 0:
            return self.x_prev

        # 计算导数（速度）
        dx = (x - self.x_prev) / dt

        # 对导数进行低通滤波
        alpha_d = self._smoothing_factor(dt, self.d_cutoff)
        dx_hat = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev

        # 根据速度自适应调整截止频率
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)

        # 对信号进行低通滤波
        alpha = self._smoothing_factor(dt, cutoff)
        x_hat = alpha * x + (1.0 - alpha) * self.x_prev

        # 更新状态
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t

        return x_hat

    def reset(self) -> None:
        """重置滤波器状态"""
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None
