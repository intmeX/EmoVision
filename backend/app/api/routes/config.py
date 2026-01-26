"""
配置管理API

提供流水线配置的读取和更新接口
"""

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import get_current_config, get_pipeline, get_session_manager
from ...core import Pipeline, SessionManager
from ...schemas.common import ApiResponse
from ...schemas.pipeline import (
    DetectorConfig,
    PipelineConfig,
    RecognizerConfig,
    VisualizerConfig,
    PerformanceConfig,
)

router = APIRouter()


class EmotionLabelsUpdate(BaseModel):
    """情绪标签更新请求"""
    labels: List[str]


@router.get("", response_model=ApiResponse[PipelineConfig])
async def get_config(
    config: PipelineConfig = Depends(get_current_config)
) -> ApiResponse[PipelineConfig]:
    """获取当前完整配置"""
    return ApiResponse(data=config, message="获取配置成功")


@router.put("", response_model=ApiResponse[PipelineConfig])
async def update_config(
    config: PipelineConfig,
    pipeline: Pipeline = Depends(get_pipeline),
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse[PipelineConfig]:
    """更新完整配置"""
    pipeline.update_config(config)
    session_manager.update_config(config)
    return ApiResponse(data=config, message="配置更新成功")


@router.patch("/detector", response_model=ApiResponse[DetectorConfig])
async def update_detector_config(
    config: DetectorConfig,
    pipeline: Pipeline = Depends(get_pipeline),
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse[DetectorConfig]:
    """更新检测器配置"""
    current_config = session_manager.current_session.config
    current_config.detector = config
    pipeline.update_config(current_config)
    session_manager.update_config(current_config)
    return ApiResponse(data=config, message="检测器配置更新成功")


@router.patch("/recognizer", response_model=ApiResponse[RecognizerConfig])
async def update_recognizer_config(
    config: RecognizerConfig,
    pipeline: Pipeline = Depends(get_pipeline),
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse[RecognizerConfig]:
    """更新识别器配置"""
    current_config = session_manager.current_session.config
    current_config.recognizer = config
    pipeline.update_config(current_config)
    session_manager.update_config(current_config)
    return ApiResponse(data=config, message="识别器配置更新成功")


@router.patch("/visualizer", response_model=ApiResponse[VisualizerConfig])
async def update_visualizer_config(
    config: VisualizerConfig,
    pipeline: Pipeline = Depends(get_pipeline),
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse[VisualizerConfig]:
    """更新可视化配置"""
    current_config = session_manager.current_session.config
    current_config.visualizer = config
    pipeline.update_config(current_config)
    session_manager.update_config(current_config)
    return ApiResponse(data=config, message="可视化配置更新成功")


@router.patch("/performance", response_model=ApiResponse[PerformanceConfig])
async def update_performance_config(
    config: PerformanceConfig,
    pipeline: Pipeline = Depends(get_pipeline),
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse[PerformanceConfig]:
    """更新性能配置"""
    current_config = session_manager.current_session.config
    current_config.performance = config
    pipeline.update_config(current_config)
    session_manager.update_config(current_config)
    return ApiResponse(data=config, message="性能配置更新成功")


@router.post("/reset", response_model=ApiResponse[PipelineConfig])
async def reset_config(
    pipeline: Pipeline = Depends(get_pipeline),
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse[PipelineConfig]:
    """重置为默认配置"""
    default_config = PipelineConfig()
    pipeline.update_config(default_config)
    session_manager.update_config(default_config)
    return ApiResponse(data=default_config, message="配置已重置")


@router.get("/emotions/labels", response_model=ApiResponse[List[str]])
async def get_emotion_labels(
    config: PipelineConfig = Depends(get_current_config)
) -> ApiResponse[List[str]]:
    """获取当前情绪标签列表"""
    return ApiResponse(
        data=config.recognizer.emotion_labels,
        message="获取情绪标签成功"
    )


@router.put("/emotions/labels", response_model=ApiResponse[List[str]])
async def update_emotion_labels(
    request: EmotionLabelsUpdate,
    pipeline: Pipeline = Depends(get_pipeline),
    session_manager: SessionManager = Depends(get_session_manager)
) -> ApiResponse[List[str]]:
    """更新情绪标签列表"""
    current_config = session_manager.current_session.config
    current_config.recognizer.emotion_labels = request.labels
    pipeline.update_config(current_config)
    session_manager.update_config(current_config)
    return ApiResponse(data=request.labels, message="情绪标签更新成功")
