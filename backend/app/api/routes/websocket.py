"""
WebSocket端点

提供实时帧流推送和双向通信
"""

import asyncio
import json
import time
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..deps import get_session_manager
from ...core import Pipeline, SessionManager
from ...schemas.websocket import (
    BinaryFrameHeader,
    ControlMessage,
    StatusMessage,
    WSMessage,
)
from ...utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._use_binary: bool = True  # 默认使用二进制传输
    
    @property
    def use_binary(self) -> bool:
        """是否使用二进制传输"""
        return self._use_binary
    
    @use_binary.setter
    def use_binary(self, value: bool) -> None:
        """设置是否使用二进制传输"""
        self._use_binary = value
    
    async def connect(self, websocket: WebSocket) -> None:
        """接受新连接"""
        await websocket.accept()
        self._connections.add(websocket)
        logger.info(f"WebSocket连接: {len(self._connections)} 个活跃连接")
    
    def disconnect(self, websocket: WebSocket) -> None:
        """断开连接"""
        self._connections.discard(websocket)
        logger.info(f"WebSocket断开: {len(self._connections)} 个活跃连接")
    
    async def broadcast(self, message: WSMessage) -> None:
        """广播消息到所有连接"""
        if not self._connections:
            return
        
        data = message.model_dump_json()
        disconnected = []
        
        for conn in self._connections:
            try:
                await conn.send_text(data)
            except Exception:
                disconnected.append(conn)
        
        for conn in disconnected:
            self._connections.discard(conn)
    
    async def broadcast_binary_frame(
        self,
        header: BinaryFrameHeader,
        image_bytes: bytes
    ) -> None:
        """
        广播二进制帧数据
        
        传输协议：
        1. 先发送JSON头部（包含元数据）
        2. 紧接着发送二进制图像数据
        
        Args:
            header: 帧头部信息
            image_bytes: JPEG图像字节数据
        """
        if not self._connections:
            return
        
        header_json = header.model_dump_json()
        disconnected = []
        
        for conn in self._connections:
            try:
                # 先发送JSON头部
                await conn.send_text(header_json)
                # 再发送二进制图像数据
                await conn.send_bytes(image_bytes)
            except Exception:
                disconnected.append(conn)
        
        for conn in disconnected:
            self._connections.discard(conn)
    
    async def send_to(self, websocket: WebSocket, message: WSMessage) -> None:
        """发送消息到指定连接"""
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"发送消息失败: {e}")


# 全局连接管理器
manager = ConnectionManager()


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """
    实时流WebSocket端点
    
    接收控制消息，推送帧数据和状态消息
    """
    await manager.connect(websocket)
    
    # 获取全局流水线实例（与API路由共享）
    from ..deps import get_pipeline
    session_manager = get_session_manager()
    pipeline = get_pipeline(session_manager)
    
    # 设置回调
    async def on_frame(msg):
        await manager.broadcast(msg)
    
    async def on_binary_frame(header, image_bytes):
        """二进制帧回调"""
        if manager.use_binary:
            await manager.broadcast_binary_frame(header, image_bytes)
        else:
            # 降级到Base64传输
            import base64
            from ...schemas.websocket import FrameMessage
            frame_msg = FrameMessage(
                timestamp=header.timestamp,
                frame_id=header.frame_id,
                image=base64.b64encode(image_bytes).decode('utf-8'),
                detections=header.detections,
                emotions=header.emotions
            )
            await manager.broadcast(frame_msg)
    
    async def on_stats(msg):
        await manager.broadcast(msg)
    
    async def on_status(msg):
        await manager.broadcast(msg)
    
    pipeline.set_callbacks(
        on_frame=on_frame,
        on_binary_frame=on_binary_frame,
        on_stats=on_stats,
        on_status=on_status
    )
    
    # 独立的任务来运行流水线
    running_task = None
    
    try:
        while True:
            # 接收控制消息
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=1.0
                )
                
                try:
                    msg = json.loads(data)
                    action = msg.get("action")
                    
                    if action == "start":
                        if pipeline.source_manager.source_info:
                            if running_task is None or running_task.done():
                                running_task = asyncio.create_task(pipeline.run())
                    elif action == "stop":
                        await pipeline.stop()
                        if running_task and not running_task.done():
                            running_task.cancel()
                            # 不在这里等待任务完成，避免阻塞WebSocket循环
                            running_task = None
                    elif action == "pause":
                        await pipeline.pause()
                    elif action == "resume":
                        await pipeline.resume()
                    
                except json.JSONDecodeError:
                    pass
                
            except asyncio.TimeoutError:
                # 超时正常，继续循环
                pass
    
    except WebSocketDisconnect:
        logger.info("WebSocket客户端断开连接")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        # 清理资源
        if running_task and not running_task.done():
            running_task.cancel()
            # 等待任务完成最多几秒钟
            try:
                await asyncio.wait_for(running_task, timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("流水线任务清理超时")
            except asyncio.CancelledError:
                pass
        # 注意：不再清理pipeline，因为它是由deps管理的共享实例
        manager.disconnect(websocket)
