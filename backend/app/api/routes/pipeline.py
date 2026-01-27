"""
流水线控制API

提供流水线的启动、停止、暂停等控制接口
注意：实际的控制通过WebSocket进行，HTTP API主要用于状态查询
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import get_session_manager, get_pipeline
from ...core import Pipeline, SessionManager
from ...schemas.common import ApiResponse

router = APIRouter()


class PipelineStatus(BaseModel):
    """流水线状态"""
    state: str
    source_info: Optional[dict] = None


@router.get("/status", response_model=ApiResponse[PipelineStatus])
async def get_status(
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse[PipelineStatus]:
    """获取流水线状态"""
    # 获取当前会话的配置和信息
    session = session_manager.get_or_create_session()
    
    # 获取最新状态 - 从活动的流水线获取
    pipeline = get_pipeline(session_manager)
    
    status = PipelineStatus(
        state=pipeline.state.value,
        source_info=pipeline.source_manager.source_info.to_dict()
        if pipeline.source_manager.source_info else None
    )
    return ApiResponse(data=status, message="获取状态成功")


@router.post("/start", response_model=ApiResponse)
async def start_pipeline(
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse:
    """启动流水线 - 实际上只是检查是否可以启动"""
    pipeline = get_pipeline(session_manager)
    
    if pipeline.state.value == "running":
        raise HTTPException(status_code=400, detail="流水线已在运行中")
    
    if not pipeline.source_manager.source_info:
        raise HTTPException(status_code=400, detail="请先选择视觉源")
    
    # 注意：实际启动通过WebSocket进行，这里只做验证
    return ApiResponse(message="流水线可以启动（通过WebSocket控制）")


@router.post("/stop", response_model=ApiResponse)
async def stop_pipeline(
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse:
    """停止流水线 - 实际上只是检查状态"""
    pipeline = get_pipeline(session_manager)
    
    # 注意：实际停止通过WebSocket进行，这里只做验证或提供备用手段
    pipeline.stop()
    return ApiResponse(message="流水线停止命令已发送")


@router.post("/pause", response_model=ApiResponse)
async def pause_pipeline(
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse:
    """暂停流水线 - 实际上只是检查状态"""
    pipeline = get_pipeline(session_manager)
    
    if pipeline.state.value != "running":
        raise HTTPException(status_code=400, detail="流水线未在运行中")
    
    # 注意：实际暂停通过WebSocket进行
    pipeline.pause()
    return ApiResponse(message="流水线暂停命令已发送")


@router.post("/resume", response_model=ApiResponse)
async def resume_pipeline(
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse:
    """恢复流水线 - 实际上只是检查状态"""
    pipeline = get_pipeline(session_manager)
    
    if pipeline.state.value != "paused":
        raise HTTPException(status_code=400, detail="流水线未处于暂停状态")
    
    # 注意：实际恢复通过WebSocket进行
    pipeline.resume()
    return ApiResponse(message="流水线恢复命令已发送")
