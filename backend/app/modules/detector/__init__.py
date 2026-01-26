"""检测器模块"""

from .base_detector import BaseDetector
from .yolo_detector import YOLODetector
from .schemas import Detection, DetectionType

__all__ = ["BaseDetector", "YOLODetector", "Detection", "DetectionType"]
