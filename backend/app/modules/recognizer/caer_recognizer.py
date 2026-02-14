"""
CaerMultiStream 情绪识别器

基于多流融合模型的情绪识别，使用全图和人脸区域（不需要身体区域），
输出 CAER-S 数据集定义的 7 类情绪（多分类）。
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
from .model_builders import build_caer_multistream
from .preprocessing import batch_tensors, prepare_context, prepare_face
from .schemas import EmotionResult

logger = get_logger(__name__)

# CAER-S 7 类情绪标签（与模型输出顺序一致）
CAER_LABELS = ["愤怒", "厌恶", "恐惧", "开心", "中性", "悲伤", "惊讶"]


class CaerRecognizer(BaseEmotionRecognizer):
    """
    CaerMultiStream 情绪识别器

    多流融合模型：上下文（全图）+ 人脸 + CLIP caption。
    与 Emotic 的区别：不需要身体区域输入。
    输入：全图 224×224，人脸 48×48。
    输出：7 类 CAER-S 情绪的 softmax 概率（多分类）。
    """

    CONTEXT_SIZE = (224, 224)
    FACE_SIZE = (48, 48)

    def __init__(self, config: RecognizerConfig):
        """
        初始化 CAER 识别器

        Args:
            config: 识别器配置
        """
        super().__init__(config)
        self._device: torch.device = torch.device("cpu")
        self._labels = CAER_LABELS

    def load_model(self, model_path: str = None) -> None:
        """
        加载 CaerMultiStream 模型

        Args:
            model_path: 模型权重文件路径
        """
        self._device = select_device()

        self._model = build_caer_multistream()
        self._model.to(self._device)

        if model_path:
            from models.weight_utils import load_weights_init

            load_weights_init(self._model, model_path)
            logger.info(f"CAER 权重已加载: {model_path}")

        self._model.eval()
        logger.info(f"CAER 识别器初始化完成，设备: {self._device}")

    def predict(
        self,
        frame: np.ndarray,
        detections: List[Detection],
    ) -> List[EmotionResult]:
        """
        对检测到的人脸进行情绪识别

        CaerMultiStream 使用全图 + 人脸，不需要人体匹配。
        每个人脸检测都会产生一个结果。

        Args:
            frame: 原始图像帧 (BGR, HWC)
            detections: 检测结果列表

        Returns:
            情绪识别结果列表
        """
        if self._model is None:
            raise RuntimeError("模型未加载，请先调用 initialize()")

        face_detections = [d for d in detections if d.type == DetectionType.FACE]
        if not face_detections:
            return []

        # 预处理：全图对所有人脸共享
        context_tensor = prepare_context(frame, self.CONTEXT_SIZE)
        context_batch = [context_tensor] * len(face_detections)

        face_tensors = [
            prepare_face(frame, det.bbox, self.FACE_SIZE) for det in face_detections
        ]

        ctx_batch = batch_tensors(context_batch, self._device)
        face_batch = batch_tensors(face_tensors, self._device)

        if ctx_batch is None or face_batch is None:
            return []

        # 推理
        start = time.perf_counter()
        with torch.no_grad():
            logits = self._model(ctx_batch, face_batch)  # (B, 7)
            probs = torch.softmax(logits, dim=1)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            f"CAER 推理完成: {len(face_detections)} 张人脸, {elapsed_ms:.1f}ms"
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
