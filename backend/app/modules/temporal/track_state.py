"""轨迹状态管理

存储每个跟踪目标的时序状态，包括几何信息、情绪历史和决策状态。
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class TrackState:
    """单个跟踪目标的状态"""

    track_id: int
    last_ts: float = 0.0

    # 几何状态 (One Euro Filter)
    euro_cx: Optional[float] = None
    euro_cy: Optional[float] = None
    euro_w: Optional[float] = None
    euro_h: Optional[float] = None
    euro_t_prev: Optional[float] = None
    euro_dx_prev: dict[str, float] = field(default_factory=lambda: {
        'cx': 0.0, 'cy': 0.0, 'w': 0.0, 'h': 0.0
    })

    # 卡尔曼滤波状态
    kf_state: Optional[np.ndarray] = None  # [cx, cy, w, h, vx, vy, vw, vh]
    kf_cov: Optional[np.ndarray] = None

    # 情绪分支 (多尺度融合)
    p_fast: Optional[np.ndarray] = None
    p_med: Optional[np.ndarray] = None
    p_slow: Optional[np.ndarray] = None

    # 决策状态 (滞后策略)
    stable_label: str = ""
    stable_score: float = 0.0
    dwell_count: int = 0
    recent_labels: deque = field(default_factory=lambda: deque(maxlen=30))

    # 运动估计
    prev_bbox: Optional[tuple[float, float, float, float]] = None
    motion_level: float = 0.0

    # 轨迹元数据
    age: int = 0  # 轨迹存在的帧数
    hits: int = 0  # 成功匹配的次数
    time_since_update: int = 0  # 自上次更新以来的帧数

    def update_age(self, matched: bool = True) -> None:
        """更新轨迹年龄和匹配状态"""
        self.age += 1
        if matched:
            self.hits += 1
            self.time_since_update = 0
        else:
            self.time_since_update += 1

    def is_confirmed(self, min_hits: int = 3) -> bool:
        """判断轨迹是否已确认（足够的匹配次数）"""
        return self.hits >= min_hits

    def is_stale(self, max_age: int = 30) -> bool:
        """判断轨迹是否过期（长时间未更新）"""
        return self.time_since_update > max_age
