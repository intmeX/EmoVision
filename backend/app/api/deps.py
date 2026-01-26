"""
依赖注入模块

提供API路由所需的共享依赖
"""

from typing import Optional

from fastapi import Depends

from ..core import Pipeline, SessionManager
from ..schemas.pipeline import PipelineConfig


# 全局单例
_session_manager: Optional[SessionManager] = None
_pipeline: Optional[Pipeline] = None


def get_session_manager() -> SessionManager:
    """获取会话管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def get_pipeline(
    session_manager: SessionManager = Depends(get_session_manager)
) -> Pipeline:
    """获取流水线单例"""
    global _pipeline
    
    # 确保有会话
    session = session_manager.get_or_create_session()
    
    if _pipeline is None:
        _pipeline = Pipeline(session.config)
        _pipeline.initialize()
    
    return _pipeline


def get_current_config(
    session_manager: SessionManager = Depends(get_session_manager)
) -> PipelineConfig:
    """获取当前配置"""
    session = session_manager.get_or_create_session()
    return session.config


async def cleanup_resources():
    """清理资源"""
    global _pipeline, _session_manager
    
    if _pipeline:
        _pipeline.cleanup()
        _pipeline = None
    
    _session_manager = None
