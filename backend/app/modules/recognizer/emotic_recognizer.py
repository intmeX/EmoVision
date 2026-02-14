"""
SEEmoticQuadrupleStream 情绪识别器

基于四流融合模型的多标签情绪识别，使用全图、身体区域和人脸区域，
输出 Emotic 数据集定义的 26 类情绪标签的 logits（多标签分类）。
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
from .matching import filter_by_type, get_detection_by_id, match_faces_to_persons
from .model_builders import build_emotic_quadruple_stream
from .preprocessing import batch_tensors, prepare_body, prepare_context, prepare_face
from .schemas import EmotionResult

logger = get_logger(__name__)

# Emotic 26 类离散情绪标签
EMOTIC_LABELS = [
    "喜爱",
    "愤怒",
    "烦恼",
    "期待",
    "厌恶",
    "自信",
    "不满",
    "疏离",
    "不安",
    "困惑",
    "尴尬",
    "投入",
    "尊重",
    "兴奋",
    "疲惫",
    "恐惧",
    "快乐",
    "痛苦",
    "平静",
    "愉悦",
    "悲伤",
    "敏感",
    "受苦",
    "惊讶",
    "同情",
    "渴望",
]

# 多标签分类的激活阈值
MULTI_LABEL_THRESHOLD = 0.5


class EmoticRecognizer(BaseEmotionRecognizer):
    """
    SEEmoticQuadrupleStream 情绪识别器

    四流融合模型：上下文（全图）+ 身体 + 人脸 + CLIP caption。
    输入：全图 224×224，身体 224×224，人脸 48×48。
    输出：26 类 Emotic 情绪标签的 sigmoid 概率（多标签）。

    需要人脸-人体匹配：每个人脸必须有配对的人体才能进行识别。
    未匹配到人体的人脸将被跳过（日志警告）。
    """

    CONTEXT_SIZE = (224, 224)
    BODY_SIZE = (224, 224)
    FACE_SIZE = (48, 48)

    def __init__(self, config: RecognizerConfig):
        """
        初始化 Emotic 识别器

        Args:
            config: 识别器配置
        """
        super().__init__(config)
        self._device: torch.device = torch.device("cpu")
        self._labels = EMOTIC_LABELS

    def load_model(self, model_path: str = None) -> None:
        """
        加载 SEEmoticQuadrupleStream 模型

        Args:
            model_path: 模型权重文件路径
        """
        self._device = select_device()

        self._model = build_emotic_quadruple_stream()
        self._model.to(self._device)

        if model_path:
            from ....models.weight_utils import load_weights_init

            load_weights_init(self._model, model_path)
            logger.info(f"Emotic 权重已加载: {model_path}")

        self._model.eval()
        logger.info(f"Emotic 识别器初始化完成，设备: {self._device}")

    def predict(
        self,
        frame: np.ndarray,
        detections: List[Detection],
    ) -> List[EmotionResult]:
        """
        对检测到的目标进行多标签情绪识别

        流程：
        1. 分离人脸和人体检测
        2. 执行人脸-人体匹配
        3. 对每个有配对人体的人脸，裁剪全图/身体/人脸区域
        4. 批量推理
        5. 将 sigmoid 概率转换为 EmotionResult

        Args:
            frame: 原始图像帧 (BGR, HWC)
            detections: 检测结果列表

        Returns:
            情绪识别结果列表
        """
        if self._model is None:
            raise RuntimeError("模型未加载，请先调用 initialize()")

        faces = filter_by_type(detections, DetectionType.FACE)
        persons = filter_by_type(detections, DetectionType.PERSON)

        if not faces:
            return []

        # 执行人脸-人体匹配
        mapping = match_faces_to_persons(faces, persons)

        # 筛选有配对人体的人脸
        matched_faces: List[Detection] = []
        matched_persons: List[Detection] = []

        for face in faces:
            person_id = mapping.get(face.id)
            if person_id is None:
                logger.debug(f"Emotic: 人脸 {face.id} 未匹配到人体，跳过")
                continue
            person = get_detection_by_id(detections, person_id)
            if person is None:
                continue
            matched_faces.append(face)
            matched_persons.append(person)

        if not matched_faces:
            logger.debug("Emotic: 无匹配的人脸-人体对，跳过推理")
            return []

        # 预处理
        context_tensor = prepare_context(frame, self.CONTEXT_SIZE)
        context_batch = [context_tensor] * len(matched_faces)

        body_tensors = [
            prepare_body(frame, p.bbox, self.BODY_SIZE) for p in matched_persons
        ]
        face_tensors = [
            prepare_face(frame, f.bbox, self.FACE_SIZE) for f in matched_faces
        ]

        ctx_batch = batch_tensors(context_batch, self._device)
        body_batch = batch_tensors(body_tensors, self._device)
        face_batch = batch_tensors(face_tensors, self._device)

        if ctx_batch is None or body_batch is None or face_batch is None:
            return []

        # 推理
        start = time.perf_counter()
        with torch.no_grad():
            logits = self._model(ctx_batch, body_batch, face_batch)  # (B, 26)
            probs = torch.sigmoid(logits)  # 多标签用 sigmoid

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            f"Emotic 推理完成: {len(matched_faces)} 个目标, {elapsed_ms:.1f}ms"
        )

        # 构建结果
        probs_np = probs.cpu().numpy()
        results: List[EmotionResult] = []

        for i, face in enumerate(matched_faces):
            prob_dict = {
                label: round(float(probs_np[i, j]), 4)
                for j, label in enumerate(self._labels)
            }
            dominant = max(prob_dict, key=prob_dict.get)  # type: ignore[arg-type]
            results.append(
                EmotionResult(
                    detection_id=face.id,
                    probabilities=prob_dict,
                    dominant_emotion=dominant,
                    confidence=prob_dict[dominant],
                )
            )

        return results
