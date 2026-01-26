"""
情绪识别器抽象基类

定义情绪识别器的统一接口，支持自定义模型接入
"""

from abc import abstractmethod
from typing import List

import numpy as np

from ..base import BaseModule
from ..detector.schemas import Detection
from ...schemas.pipeline import RecognizerConfig
from .schemas import EmotionResult


class BaseEmotionRecognizer(BaseModule[RecognizerConfig]):
    """
    情绪识别器抽象基类
    
    用户可继承此类实现自定义的情绪识别模型接入
    """
    
    def __init__(self, config: RecognizerConfig):
        """
        初始化识别器
        
        Args:
            config: 识别器配置
        """
        super().__init__(config)
        self._model = None
    
    @property
    def emotion_labels(self) -> List[str]:
        """当前使用的情绪类别列表"""
        return self._config.emotion_labels
    
    @abstractmethod
    def load_model(self, model_path: str = None) -> None:
        """
        加载情绪识别模型
        
        Args:
            model_path: 模型权重文件路径，为 None 时使用配置中的路径
        """
        pass
    
    @abstractmethod
    def predict(
        self,
        frame: np.ndarray,
        detections: List[Detection]
    ) -> List[EmotionResult]:
        """
        对检测到的目标进行情绪识别
        
        Args:
            frame: 原始图像帧 (BGR格式, HWC排列)
            detections: 检测结果列表，包含 face 和 person 边界框
            
        Returns:
            情绪识别结果列表，与 detections 中的 face 一一对应
        """
        pass
    
    def initialize(self) -> None:
        """初始化识别器，加载模型"""
        self.load_model(self._config.model_path)
        self._initialized = True
    
    def cleanup(self) -> None:
        """清理资源"""
        self._model = None
        self._initialized = False
    
    def update_labels(self, labels: List[str]) -> None:
        """
        动态更新情绪类别标签
        
        Args:
            labels: 新的情绪类别列表
        """
        self._config.emotion_labels = labels
