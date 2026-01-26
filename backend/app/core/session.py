"""
会话管理模块

管理用户会话和配置隔离
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from ..schemas.pipeline import PipelineConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Session:
    """用户会话"""
    id: str
    created_at: datetime
    config: PipelineConfig
    is_active: bool = True
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "config": self.config.model_dump()
        }


class SessionManager:
    """
    会话管理器
    
    管理多个用户会话，提供配置隔离
    """
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._current_session_id: Optional[str] = None
    
    @property
    def current_session(self) -> Optional[Session]:
        """获取当前会话"""
        if self._current_session_id:
            return self._sessions.get(self._current_session_id)
        return None
    
    def create_session(self, config: Optional[PipelineConfig] = None) -> Session:
        """
        创建新会话
        
        Args:
            config: 初始配置，为None时使用默认配置
            
        Returns:
            新创建的会话
        """
        session_id = str(uuid.uuid4())[:8]
        session = Session(
            id=session_id,
            created_at=datetime.now(),
            config=config or PipelineConfig()
        )
        
        self._sessions[session_id] = session
        self._current_session_id = session_id
        
        logger.info(f"创建新会话: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取指定会话"""
        return self._sessions.get(session_id)
    
    def switch_session(self, session_id: str) -> bool:
        """
        切换到指定会话
        
        Args:
            session_id: 目标会话ID
            
        Returns:
            是否成功切换
        """
        if session_id in self._sessions:
            self._current_session_id = session_id
            logger.info(f"切换到会话: {session_id}")
            return True
        return False
    
    def update_config(
        self,
        config: PipelineConfig,
        session_id: Optional[str] = None
    ) -> bool:
        """
        更新会话配置
        
        Args:
            config: 新配置
            session_id: 会话ID，为None时使用当前会话
            
        Returns:
            是否成功更新
        """
        target_id = session_id or self._current_session_id
        if target_id and target_id in self._sessions:
            self._sessions[target_id].config = config
            logger.info(f"更新会话配置: {target_id}")
            return True
        return False
    
    def close_session(self, session_id: str) -> bool:
        """
        关闭会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功关闭
        """
        if session_id in self._sessions:
            self._sessions[session_id].is_active = False
            if self._current_session_id == session_id:
                self._current_session_id = None
            logger.info(f"关闭会话: {session_id}")
            return True
        return False
    
    def list_sessions(self) -> list[Session]:
        """列出所有活跃会话"""
        return [s for s in self._sessions.values() if s.is_active]
    
    def get_or_create_session(self) -> Session:
        """获取当前会话，如果不存在则创建"""
        if self.current_session:
            return self.current_session
        return self.create_session()
