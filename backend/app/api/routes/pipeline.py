"""
流水线控制API

提供流水线的启动、停止、暂停等控制接口
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..deps import get_pipeline, get_session_manager
from ...core import Pipeline, SessionManager
from ...schemas.common import ApiResponse

router = APIRouter()


class PipelineStatus(BaseModel):
    """流水线状态"""
    state: str
    source_info: Optional[dict] = None


@router.get("/status", response_model=ApiResponse[PipelineStatus])
async def get_status(
    pipeline: Pipeline = Depends(get_pipeline)
) -> ApiResponse[PipelineStatus]:
    """获取流水线状态"""
    status = PipelineStatus(
        state=pipeline.state.value,
        source_info=pipeline.source_manager.source_info.to_dict()
        if pipeline.source_manager.source_info else None
    )
    return ApiResponse(data=status, message="获取状态成功")


@router.post("/start", response_model=ApiResponse)
async def start_pipeline(
    background_tasks: BackgroundTasks,
    pipeline: Pipeline = Depends(get_pipeline)
) -> ApiResponse:
    """启动流水线"""
    if pipeline.state.value == "running":
        raise HTTPException(status_code=400, detail="流水线已在运行中")
    
    if not pipeline.source_manager.source_info:
        raise HTTPException(status_code=400, detail="请先选择视觉源")
    
    # 在后台运行流水线
    background_tasks.add_task(pipeline.run)
    
    return ApiResponse(message="流水线启动中")


@router.post("/stop", response_model=ApiResponse)
async def stop_pipeline(
    pipeline: Pipeline = Depends(get_pipeline)
) -> ApiResponse:
    """停止流水线"""
    pipeline.stop()
    return ApiResponse(message="流水线已停止")


@router.post("/pause", response_model=ApiResponse)
async def pause_pipeline(
    pipeline: Pipeline = Depends(get_pipeline)
) -> ApiResponse:
    """暂停流水线"""
    if pipeline.state.value != "running":
        raise HTTPException(status_code=400, detail="流水线未在运行中")
    
    pipeline.pause()
    return ApiResponse(message="流水线已暂停")


@router.post("/resume", response_model=ApiResponse)
async def resume_pipeline(
    pipeline: Pipeline = Depends(get_pipeline)
) -> ApiResponse:
    """恢复流水线"""
    if pipeline.state.value != "paused":
        raise HTTPException(status_code=400, detail="流水线未处于暂停状态")
    
    pipeline.resume()
    return ApiResponse(message="流水线已恢复")
