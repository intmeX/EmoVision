"""多尺度情绪融合

使用快/中/慢三个时间尺度的 EMA 分支，结合置信度和运动感知加权，
实现稳定且响应及时的情绪概率融合。
"""

import numpy as np


class EmotionFusion:
    """
    多尺度情绪融合器

    维护三个不同时间常数的 EMA 分支：
    - 快速分支：快速响应真实情绪变化
    - 中速分支：基线平滑器
    - 慢速分支：抗闪烁锚点
    """

    def __init__(
        self,
        alpha_fast: float = 0.7,
        alpha_med: float = 0.4,
        alpha_slow: float = 0.18,
        num_classes: int = 7,
    ):
        """
        初始化情绪融合器

        Args:
            alpha_fast: 快速分支的 EMA 系数
            alpha_med: 中速分支的 EMA 系数
            alpha_slow: 慢速分支的 EMA 系数
            num_classes: 情绪类别数量
        """
        self.alpha_fast = alpha_fast
        self.alpha_med = alpha_med
        self.alpha_slow = alpha_slow
        self.num_classes = num_classes

        # 三个分支的概率分布
        self.p_fast: np.ndarray | None = None
        self.p_med: np.ndarray | None = None
        self.p_slow: np.ndarray | None = None

    def update(
        self,
        probabilities: np.ndarray,
        confidence: float,
        motion_level: float = 0.0,
    ) -> np.ndarray:
        """
        更新并融合情绪概率

        Args:
            probabilities: 当前帧的情绪概率分布 (shape: [num_classes])
            confidence: 当前帧的识别置信度 (0-1)
            motion_level: 运动水平 (0-1, 越大表示运动越剧烈)

        Returns:
            融合后的概率分布
        """
        # 归一化输入概率
        p = probabilities / (probabilities.sum() + 1e-8)

        # 首次调用，初始化所有分支
        if self.p_fast is None:
            self.p_fast = p.copy()
            self.p_med = p.copy()
            self.p_slow = p.copy()
            return p

        # 更新三个分支（EMA）
        self.p_fast = self.alpha_fast * p + (1 - self.alpha_fast) * self.p_fast
        self.p_med = self.alpha_med * p + (1 - self.alpha_med) * self.p_med
        self.p_slow = self.alpha_slow * p + (1 - self.alpha_slow) * self.p_slow

        # 计算分支一致性权重（使用 KL 散度的倒数）
        w_fast = self._consistency_weight(self.p_fast, self.p_med)
        w_med = 1.0
        w_slow = self._consistency_weight(self.p_slow, self.p_med)

        # 运动门控：高运动时减少快速分支权重，避免噪声翻转
        motion_gate_fast = max(0.4, 1.0 - 0.5 * motion_level)

        # 置信度增益：高置信度时增加快速分支权重
        conf_gain = 0.5 + 0.5 * confidence

        # 计算最终权重
        wf = w_fast * motion_gate_fast * conf_gain
        wm = w_med
        ws = w_slow * (1.1 - 0.3 * confidence)  # 低置信度时增加慢速分支

        # 加权融合
        wsum = wf + wm + ws + 1e-8
        fused = (wf * self.p_fast + wm * self.p_med + ws * self.p_slow) / wsum

        # 归一化
        return fused / (fused.sum() + 1e-8)

    def _consistency_weight(self, p1: np.ndarray, p2: np.ndarray) -> float:
        """
        计算两个概率分布的一致性权重

        使用 KL 散度的倒数作为一致性度量。
        KL 散度越小，分布越一致，权重越大。

        Args:
            p1: 概率分布 1
            p2: 概率分布 2

        Returns:
            一致性权重 (0-1)
        """
        # 计算 KL 散度: KL(p1 || p2)
        kl = np.sum(p1 * (np.log(p1 + 1e-8) - np.log(p2 + 1e-8)))
        # 转换为权重
        return 1.0 / (1.0 + kl)

    def reset(self) -> None:
        """重置所有分支"""
        self.p_fast = None
        self.p_med = None
        self.p_slow = None
