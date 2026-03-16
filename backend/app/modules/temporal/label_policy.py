"""标签决策策略

使用滞后机制防止情绪标签的频繁跳变。
"""


class LabelPolicy:
    """
    标签决策策略

    使用滞后（hysteresis）机制：
    - 需要新标签持续一定帧数才切换
    - 需要足够的置信度差距才切换
    - 防止单帧噪声导致的标签闪烁
    """

    def __init__(
        self,
        switch_margin: float = 0.08,
        min_conf_to_switch: float = 0.45,
        dwell_frames: int = 4,
    ):
        """
        初始化标签决策策略

        Args:
            switch_margin: 切换所需的最小置信度差距
            min_conf_to_switch: 切换所需的最小置信度
            dwell_frames: 切换前需要持续的帧数
        """
        self.switch_margin = switch_margin
        self.min_conf_to_switch = min_conf_to_switch
        self.dwell_frames = dwell_frames

        # 状态
        self.stable_label: str = ""
        self.stable_score: float = 0.0
        self.dwell_count: int = 0

    def update(
        self,
        probabilities: dict[str, float],
    ) -> tuple[str, float]:
        """
        更新并返回稳定的标签

        Args:
            probabilities: 情绪概率分布 {"开心": 0.8, ...}

        Returns:
            (稳定标签, 稳定得分)
        """
        if not probabilities:
            return self.stable_label, self.stable_score

        # 找到当前最高概率的标签
        new_label = max(probabilities.items(), key=lambda x: x[1])[0]
        new_score = probabilities[new_label]

        # 首次调用，直接设置
        if not self.stable_label:
            self.stable_label = new_label
            self.stable_score = new_score
            self.dwell_count = 1
            return self.stable_label, self.stable_score

        # 获取当前稳定标签的得分
        cur_score = probabilities.get(self.stable_label, 0.0)

        # 判断是否想要切换
        wants_switch = (
            new_label != self.stable_label
            and new_score > self.min_conf_to_switch
            and (new_score - cur_score) > self.switch_margin
        )

        if wants_switch:
            # 累计驻留计数
            self.dwell_count += 1
            # 达到阈值，执行切换
            if self.dwell_count >= self.dwell_frames:
                self.stable_label = new_label
                self.stable_score = new_score
                self.dwell_count = 0
        else:
            # 不想切换，重置计数
            self.dwell_count = 0
            # 缓慢衰减稳定得分，同时更新为当前得分
            self.stable_score = max(self.stable_score * 0.9, cur_score)

        return self.stable_label, self.stable_score

    def reset(self) -> None:
        """重置决策状态"""
        self.stable_label = ""
        self.stable_score = 0.0
        self.dwell_count = 0
