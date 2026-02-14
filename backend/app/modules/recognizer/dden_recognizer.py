"""
SDDENFPN 情绪识别器

基于 SDDENFPN 模型的人脸情绪识别，仅使用人脸区域进行 7 类情绪多分类
（RAF-DB 标签: happy, sad, angry, fear, surprise, disgust, neutral）
"""

import time
from typing import List

import numpy as np
import torch

from ...schemas.pipeline import RecognizerConfig
from ...utils.device import select_device
from ...utils.logger import get_logger
from ..detector.schemas import Detection, DetectionType
from .base_recognizer import BaseEmotionRecognizer
from .model_builders import build_sddenfpn
from .preprocessing import batch_tensors, prepare_face
from .schemas import EmotionResult

logger = get_logger(__name__)

# RAF-DB 7 类情绪标签（与模型输出顺序一致）
RAFDB_LABELS = ["惊讶", "恐惧", "厌恶", "开心", "悲伤", "愤怒", "中性"]


class DDENRecognizer(BaseEmotionRecognizer):
    """
    SDDENFPN 情绪识别器

    仅对人脸区域进行多分类情绪识别，输入 224×224 人脸图像，
    输出 7 类情绪（RAF-DB）的概率分布。
    """

    # 人脸输入尺寸
    FACE_SIZE = (224, 224)

    def __init__(self, config: RecognizerConfig):
        """
        初始化 DDEN 识别器

        Args:
            config: 识别器配置
        """
        super().__init__(config)
        self._device: torch.device = torch.device("cpu")
        self._labels = RAFDB_LABELS

    def load_model(self, model_path: str = None) -> None:
        """
        加载 SDDENFPN 模型

        Args:
            model_path: 模型权重文件路径
        """
        self._device = select_device()

        # 构建模型
        self._model = build_sddenfpn()
        self._model.to(self._device)

        # 加载权重
        if model_path:
            from models.weight_utils import load_weights_init, weights_frozen

            load_weights_init(self._model, model_path)
            weights_frozen(self._model)
            logger.info(f"SDDENFPN 权重已加载: {model_path}")

        self._model.eval()
        logger.info(f"SDDENFPN 识别器初始化完成，设备: {self._device}")

    def predict(
        self,
        frame: np.ndarray,
        detections: List[Detection],
    ) -> List[EmotionResult]:
        """
        对检测到的人脸进行情绪识别

        SDDENFPN 仅使用人脸区域，不需要人体匹配。

        Args:
            frame: 原始图像帧 (BGR, HWC)
            detections: 检测结果列表

        Returns:
            情绪识别结果列表（每个人脸一个结果）
        """
        if self._model is None:
            raise RuntimeError("模型未加载，请先调用 initialize()")

        # 筛选人脸检测
        face_detections = [d for d in detections if d.type == DetectionType.FACE]
        if not face_detections:
            return []

        # 批量预处理人脸
        face_tensors = [
            prepare_face(frame, det.bbox, self.FACE_SIZE) for det in face_detections
        ]
        batch = batch_tensors(face_tensors, self._device)
        if batch is None:
            return []

        # 推理
        start = time.perf_counter()
        with torch.no_grad():
            logits = self._model(batch)  # (B, 7)
            probs = torch.softmax(logits, dim=1)  # (B, 7)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            f"DDEN 推理完成: {len(face_detections)} 张人脸, {elapsed_ms:.1f}ms"
        )

        # 构建结果
        probs_np = probs.cpu().numpy()
        results: List[EmotionResult] = []

        for i, det in enumerate(face_detections):
            prob_dict = {
                label: round(float(probs_np[i, j]), 4)
                for j, label in enumerate(self._labels)
            }
            dominant = max(prob_dict, key=prob_dict.get)  # type: ignore[arg-type]
            results.append(
                EmotionResult(
                    detection_id=det.id,
                    probabilities=prob_dict,
                    dominant_emotion=dominant,
                    confidence=prob_dict[dominant],
                )
            )

        return results
