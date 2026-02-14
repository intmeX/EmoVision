"""
模拟情绪识别器

用于开发和测试，生成随机的情绪识别结果
"""

import random
import time
from typing import List

import numpy as np

from ...schemas.pipeline import RecognizerConfig
from ...utils.logger import get_logger
from ..detector.schemas import Detection, DetectionType
from .base_recognizer import BaseEmotionRecognizer
from .schemas import EmotionResult

logger = get_logger(__name__)


class MockEmotionRecognizer(BaseEmotionRecognizer):
    """
    模拟情绪识别器

    生成随机的情绪概率分布，用于开发阶段测试流水线
    """

    def __init__(self, config: RecognizerConfig):
        """
        初始化模拟识别器

        Args:
            config: 识别器配置
        """
        super().__init__(config)
        self._simulate_delay = True  # 模拟推理延迟
        self._delay_ms = 10  # 模拟延迟毫秒数

    def load_model(self, model_path: str = None) -> None:
        """模拟加载模型"""
        logger.info("加载模拟情绪识别器 (MockEmotionRecognizer)")
        # 模拟加载延迟
        time.sleep(0.1)
        self._model = "mock_model"
        logger.info("模拟识别器加载完成")

    def predict(
        self, frame: np.ndarray, detections: List[Detection]
    ) -> List[EmotionResult]:
        """
        生成模拟的情绪识别结果

        Args:
            frame: 原始图像帧 (未使用)
            detections: 检测结果列表

        Returns:
            模拟的情绪识别结果列表
        """
        if self._model is None:
            raise RuntimeError("模型未加载，请先调用 initialize()")

        # 模拟推理延迟
        if self._simulate_delay:
            time.sleep(self._delay_ms / 1000)

        results: List[EmotionResult] = []
        labels = self.emotion_labels

        # 只对face类型的检测生成情绪结果
        face_detections = [d for d in detections if d.type == DetectionType.FACE]

        for detection in face_detections:
            # 生成随机概率分布
            probs = self._generate_random_probabilities(labels)

            # 找出主导情绪
            dominant = max(probs, key=probs.get)
            confidence = probs[dominant]

            result = EmotionResult(
                detection_id=detection.id,
                probabilities=probs,
                dominant_emotion=dominant,
                confidence=confidence,
            )
            results.append(result)

        logger.debug(f"模拟识别完成: {len(results)} 个结果")
        return results

    def _generate_random_probabilities(self, labels: List[str]) -> dict[str, float]:
        """
        生成随机概率分布

        Args:
            labels: 情绪类别列表

        Returns:
            概率分布字典
        """
        # 生成随机权重并归一化
        weights = [random.random() ** 2 for _ in labels]  # 使用平方使分布更集中
        total = sum(weights)

        probs = {
            label: round(weight / total, 4) for label, weight in zip(labels, weights)
        }

        return probs

    def set_simulate_delay(self, enabled: bool, delay_ms: int = 10) -> None:
        """
        设置是否模拟推理延迟

        Args:
            enabled: 是否启用延迟
            delay_ms: 延迟毫秒数
        """
        self._simulate_delay = enabled
        self._delay_ms = delay_ms
