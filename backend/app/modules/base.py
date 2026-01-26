"""
模块基类定义

定义流水线各模块的抽象基类接口
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel


ConfigT = TypeVar("ConfigT", bound=BaseModel)


class BaseModule(ABC, Generic[ConfigT]):
    """
    流水线模块抽象基类
    
    所有流水线模块(检测器、识别器、可视化器)都应继承此基类
    """
    
    def __init__(self, config: ConfigT):
        """
        初始化模块
        
        Args:
            config: 模块配置对象
        """
        self._config = config
        self._initialized = False
    
    @property
    def config(self) -> ConfigT:
        """获取当前配置"""
        return self._config
    
    @property
    def is_initialized(self) -> bool:
        """模块是否已初始化"""
        return self._initialized
    
    @abstractmethod
    def initialize(self) -> None:
        """
        初始化模块资源
        
        应在此方法中加载模型、初始化设备等
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        清理模块资源
        
        应在此方法中释放模型、关闭连接等
        """
        pass
    
    def update_config(self, config: ConfigT) -> None:
        """
        更新模块配置
        
        Args:
            config: 新的配置对象
        """
        self._config = config
    
    def get_status(self) -> dict[str, Any]:
        """
        获取模块状态
        
        Returns:
            模块状态字典
        """
        return {
            "initialized": self._initialized,
            "config": self._config.model_dump()
        }
