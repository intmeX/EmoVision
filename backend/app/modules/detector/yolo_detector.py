"""
YOLO11 目标检测器实现

使用 ultralytics YOLO11 进行人脸和人体检测
"""

import time
from pathlib import Path
from typing import List, Optional

import numpy as np

from ...schemas.common import BoundingBox
from ...schemas.pipeline import DetectorConfig
from ...utils.logger import get_logger
from ..recognizer.matching import apply_pairing, match_faces_to_persons
from .base_detector import BaseDetector
from .schemas import Detection, DetectionType

logger = get_logger(__name__)


class YOLODetector(BaseDetector):
    """
    YOLO11 目标检测器

    支持检测人脸(face)和人体(person)两种目标类型
    """

    PERSON_CLASS_ID = 0  # COCO数据集中person的类别ID

    def __init__(self, config: DetectorConfig, model_path: Optional[Path] = None):
        """
        初始化YOLO检测器

        Args:
            config: 检测器配置
            model_path: 模型权重路径，为None时使用默认预训练模型
        """
        super().__init__(config)
        self._model_path = model_path
        self._use_custom_model = model_path is not None

    def load_model(self) -> None:
        """加载YOLO26模型"""
        try:
            from ultralytics import YOLO

            if self._model_path and Path(self._model_path).exists():
                # 使用自定义模型
                logger.info(f"加载自定义YOLO模型: {self._model_path}")
                self._model = YOLO(str(self._model_path))
            else:
                # 使用预训练模型
                model_name = "yolo26m_ch.pt"
                logger.info(f"加载预训练YOLO模型: {model_name}")
                self._model = YOLO(model_name)

            # 预热模型
            dummy_input = np.zeros((640, 640, 3), dtype=np.uint8)
            self._model.predict(dummy_input, verbose=False)
            logger.info("YOLO模型加载完成并已预热")

        except Exception as e:
            logger.error(f"YOLO模型加载失败: {e}")
            raise

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        执行目标检测

        Args:
            frame: 输入图像帧 (BGR格式)

        Returns:
            检测结果列表
        """
        if self._model is None:
            raise RuntimeError("模型未加载，请先调用 initialize()")

        start_time = time.perf_counter()

        # 使用两个阈值中较小的作为 YOLO 推理底线，后处理中按类型过滤
        min_conf = min(
            self._config.face_confidence_threshold,
            self._config.person_confidence_threshold,
        )

        # 执行推理
        results = self._model.predict(
            frame,
            conf=min_conf,
            iou=self._config.iou_threshold,
            max_det=self._config.max_detections,
            verbose=False,
        )

        detections: List[Detection] = []
        faces: List[Detection] = []
        persons: List[Detection] = []

        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            if boxes is not None:
                for box in boxes:
                    cls_id = int(box.cls.item())
                    conf = float(box.conf.item())
                    xyxy = box.xyxy[0].cpu().numpy()

                    bbox = BoundingBox.from_xyxy(
                        float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])
                    )

                    # 判断类别 (根据模型输出调整)
                    # 对于COCO预训练模型，cls_id=0 是 person
                    # 对于自定义模型，需要根据实际类别映射调整
                    if cls_id == self.PERSON_CLASS_ID:
                        if (
                            self._config.detect_person
                            and conf >= self._config.person_confidence_threshold
                        ):
                            detection = Detection(
                                id=self._next_id(),
                                type=DetectionType.PERSON,
                                bbox=bbox,
                                confidence=conf,
                            )
                            persons.append(detection)
                    else:
                        # 假设其他类别为face (自定义模型)
                        if (
                            self._config.detect_face
                            and conf >= self._config.face_confidence_threshold
                        ):
                            detection = Detection(
                                id=self._next_id(),
                                type=DetectionType.FACE,
                                bbox=bbox,
                                confidence=conf,
                            )
                            faces.append(detection)

        # 配对人脸和人体
        mapping = match_faces_to_persons(faces, persons)
        apply_pairing(faces, persons, mapping)

        # 合并结果
        detections.extend(faces)
        detections.extend(persons)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(
            f"检测完成: {len(faces)}张人脸, {len(persons)}个人体, "
            f"耗时 {elapsed_ms:.1f}ms"
        )

        return detections

    def update_config(self, config: DetectorConfig) -> None:
        """更新检测器配置"""
        old_size = self._config.model_size
        super().update_config(config)

        # 如果模型尺寸变化，需要重新加载模型
        if config.model_size != old_size and not self._use_custom_model:
            logger.info(f"模型尺寸变更: {old_size} -> {config.model_size}")
            self.load_model()
