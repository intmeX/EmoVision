"""
检测器抽象基类

定义目标检测器的统一接口
"""

from abc import abstractmethod
from typing import List

import numpy as np

from ..base import BaseModule
from ...schemas.pipeline import DetectorConfig
from .schemas import Detection


class BaseDetector(BaseModule[DetectorConfig]):
    """
    目标检测器抽象基类
    
    所有检测器实现都应继承此类并实现抽象方法
    """
    
    def __init__(self, config: DetectorConfig):
        """
        初始化检测器
        
        Args:
            config: 检测器配置
        """
        super().__init__(config)
        self._model = None
        self._detection_counter = 0
    
    @abstractmethod
    def load_model(self) -> None:
        """
        加载检测模型
        
        子类应在此方法中加载具体的模型权重
        """
        pass
    
    @abstractmethod
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        执行目标检测
        
        Args:
            frame: 输入图像帧 (BGR格式, HWC排列)
            
        Returns:
            检测结果列表
        """
        pass
    
    def initialize(self) -> None:
        """初始化检测器，加载模型"""
        self.load_model()
        self._initialized = True
    
    def cleanup(self) -> None:
        """清理资源"""
        self._model = None
        self._initialized = False
    
    def reset_counter(self) -> None:
        """重置检测计数器"""
        self._detection_counter = 0
    
    def _next_id(self) -> int:
        """生成下一个检测ID"""
        self._detection_counter += 1
        return self._detection_counter
