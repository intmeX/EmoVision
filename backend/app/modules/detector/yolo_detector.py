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
from .base_detector import BaseDetector
from .schemas import Detection, DetectionType

logger = get_logger(__name__)


class YOLODetector(BaseDetector):
    """
    YOLO11 目标检测器
    
    支持检测人脸(face)和人体(person)两种目标类型
    """
    
    # YOLO11官方预训练模型的类别映射
    # 这里假设使用的是自定义训练的face+person模型
    # 如使用COCO预训练模型，person类别ID为0
    PERSON_CLASS_ID = 0  # COCO数据集中person的类别ID
    
    def __init__(
        self,
        config: DetectorConfig,
        model_path: Optional[Path] = None
    ):
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
        """加载YOLO11模型"""
        try:
            from ultralytics import YOLO
            
            if self._model_path and Path(self._model_path).exists():
                # 使用自定义模型
                logger.info(f"加载自定义YOLO模型: {self._model_path}")
                self._model = YOLO(str(self._model_path))
            else:
                # 使用预训练模型
                model_name = f"yolo11{self._config.model_size.value}.pt"
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
        
        # 执行推理
        results = self._model.predict(
            frame,
            conf=self._config.confidence_threshold,
            iou=self._config.iou_threshold,
            max_det=self._config.max_detections,
            verbose=False
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
                        float(xyxy[0]),
                        float(xyxy[1]),
                        float(xyxy[2]),
                        float(xyxy[3])
                    )
                    
                    # 判断类别 (根据模型输出调整)
                    # 对于COCO预训练模型，cls_id=0 是 person
                    # 对于自定义模型，需要根据实际类别映射调整
                    if cls_id == self.PERSON_CLASS_ID:
                        if self._config.detect_person:
                            detection = Detection(
                                id=self._next_id(),
                                type=DetectionType.PERSON,
                                bbox=bbox,
                                confidence=conf
                            )
                            persons.append(detection)
                    else:
                        # 假设其他类别为face (自定义模型)
                        if self._config.detect_face:
                            detection = Detection(
                                id=self._next_id(),
                                type=DetectionType.FACE,
                                bbox=bbox,
                                confidence=conf
                            )
                            faces.append(detection)
        
        # 配对人脸和人体
        self._pair_detections(faces, persons)
        
        # 合并结果
        detections.extend(faces)
        detections.extend(persons)
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(
            f"检测完成: {len(faces)}张人脸, {len(persons)}个人体, "
            f"耗时 {elapsed_ms:.1f}ms"
        )
        
        return detections
    
    def _pair_detections(
        self,
        faces: List[Detection],
        persons: List[Detection]
    ) -> None:
        """
        配对人脸和人体检测结果
        
        基于IoU重叠度进行顺次配对，face边界框应该在person边界框内部或有较大重叠
        
        Args:
            faces: 人脸检测列表
            persons: 人体检测列表
        """
        if not faces or not persons:
            return
        
        used_persons = set()
        
        for face in faces:
            best_iou = 0.0
            best_person = None
            
            for person in persons:
                if person.id in used_persons:
                    continue
                
                # 计算face是否在person内部的比例
                # 使用包含度而非纯IoU，因为face通常应该在person内部
                iou = face.bbox.iou(person.bbox)
                
                # 也检查face中心是否在person内
                face_center = face.bbox.center
                in_person = (
                    person.bbox.x <= face_center[0] <= person.bbox.x2 and
                    person.bbox.y <= face_center[1] <= person.bbox.y2
                )
                
                # 优先选择包含face中心的person，其次选择IoU最大的
                if in_person and (best_person is None or iou > best_iou):
                    best_iou = iou
                    best_person = person
                elif not in_person and best_person is None and iou > 0.1:
                    best_iou = iou
                    best_person = person
            
            if best_person is not None:
                face.paired_id = best_person.id
                best_person.paired_id = face.id
                used_persons.add(best_person.id)
    
    def update_config(self, config: DetectorConfig) -> None:
        """更新检测器配置"""
        old_size = self._config.model_size
        super().update_config(config)
        
        # 如果模型尺寸变化，需要重新加载模型
        if config.model_size != old_size and not self._use_custom_model:
            logger.info(f"模型尺寸变更: {old_size} -> {config.model_size}")
            self.load_model()
