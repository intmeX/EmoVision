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
_pipelines: dict = {}  # 存储管道实例，key为会话ID


def get_session_manager() -> SessionManager:
    """获取会话管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def get_pipeline(
    session_manager: SessionManager = Depends(get_session_manager)
) -> Pipeline:
    """获取流水线单例，基于当前会话"""
    global _pipelines
    
    # 确保有会话
    session = session_manager.get_or_create_session()
    
    # 使用会话ID作为键来存储/检索管道
    session_id = session.id
    if session_id not in _pipelines:
        pipeline = Pipeline(session.config)
        pipeline.initialize()
        _pipelines[session_id] = pipeline
    else:
        pipeline = _pipelines[session_id]
    
    return pipeline


def get_current_config(
    session_manager: SessionManager = Depends(get_session_manager)
) -> PipelineConfig:
    """获取当前配置"""
    session = session_manager.get_or_create_session()
    return session.config


async def cleanup_resources():
    """清理资源"""
    global _pipelines, _session_manager
    
    for pipeline in _pipelines.values():
        pipeline.cleanup()
    _pipelines.clear()
    
    _session_manager = None
