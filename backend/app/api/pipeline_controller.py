"""
全局流水线控制器

用于协调API和WebSocket之间的流水线状态
"""

from typing import Dict, Optional, Callable
import asyncio
from ..core.session import SessionManager
from ..core.pipeline import Pipeline, PipelineState
from ..schemas.pipeline import PipelineConfig


class GlobalPipelineController:
    """全局流水线控制器，用于共享流水线状态"""
    
    def __init__(self):
        self._pipeline: Optional[Pipeline] = None
        self._session_manager: Optional[SessionManager] = None
        self._ws_callbacks: Dict[str, Callable] = {}  # WebSocket回调函数
    
    def initialize(self, session_manager: SessionManager):
        """初始化控制器"""
        self._session_manager = session_manager
        session = session_manager.get_or_create_session()
        
        # 初始化全局流水线实例
        if self._pipeline is None:
            from ..core.pipeline import Pipeline
            self._pipeline = Pipeline(session.config)
            self._pipeline.initialize()
    
    @property
    def pipeline(self) -> Optional[Pipeline]:
        """获取全局流水线实例"""
        return self._pipeline
    
    def register_ws_callbacks(self, on_frame=None, on_stats=None, on_status=None):
        """注册WebSocket回调函数"""
        if on_frame:
            self._ws_callbacks['frame'] = on_frame
        if on_stats:
            self._ws_callbacks['stats'] = on_stats
        if on_status:
            self._ws_callbacks['status'] = on_status
        
        # 如果流水线已存在，设置回调
        if self._pipeline:
            self._pipeline.set_callbacks(
                on_frame=on_frame,
                on_stats=on_stats,
                on_status=on_status
            )
    
    def update_config(self, config: PipelineConfig):
        """更新全局配置"""
        if self._pipeline:
            self._pipeline.update_config(config)
            # 更新会话管理器中的配置
            if self._session_manager:
                self._session_manager.update_config(config)
    
    def get_state(self) -> PipelineState:
        """获取当前状态"""
        if self._pipeline:
            return self._pipeline.state
        return PipelineState.IDLE
    
    def get_source_manager(self):
        """获取源管理器"""
        if self._pipeline:
            return self._pipeline.source_manager
        return None
    
    def cleanup(self):
        """清理资源"""
        if self._pipeline:
            self._pipeline.cleanup()
            self._pipeline = None


# 全局实例
global_controller = GlobalPipelineController()