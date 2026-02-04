"""
视觉源管理API

提供图像、视频上传和摄像头设置接口
"""

import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..deps import get_pipeline
from ...config import settings
from ...core import Pipeline, SourceManager
from ...schemas.common import ApiResponse
import base64
import cv2
import numpy as np
import time

router = APIRouter()


class SourceInfo(BaseModel):
    """视觉源信息"""
    source_type: str
    path: Optional[str] = None
    camera_id: Optional[int] = None
    width: int = 0
    height: int = 0
    fps: float = 0.0
    total_frames: int = 0


class CameraRequest(BaseModel):
    """摄像头请求"""
    camera_id: int = 0


class CameraInfo(BaseModel):
    """摄像头信息"""
    id: int
    available: bool = True


def encode_frame_to_base64(frame: np.ndarray, quality: int = 80) -> str:
    """
    将图像帧编码为base64字符串
    
    Args:
        frame: 图像帧 (BGR format)
        quality: JPEG压缩质量
        
    Returns:
        base64编码的JPEG图像字符串
    """
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buffer = cv2.imencode('.jpg', frame, encode_params)
    # 转换为bytes再进行base64编码
    buffer_bytes = np.array(buffer).tobytes()
    return base64.b64encode(buffer_bytes).decode('utf-8')


@router.post("/upload", response_model=ApiResponse[SourceInfo])
async def upload_file(
    file: UploadFile = File(...),
    pipeline: Pipeline = Depends(get_pipeline)
) -> ApiResponse[SourceInfo]:
    """
    上传图像或视频文件
    
    支持的格式:
    - 图像: jpg, jpeg, png, bmp, webp
    - 视频: mp4, avi, mov, mkv, webm
    """
    # 创建上传目录
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查文件类型
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    
    if suffix not in image_exts and suffix not in video_exts:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {suffix}"
        )
    
    # 保存文件
    file_path = upload_dir / filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # 如果流水线正在运行，则停止它，因为在切换视觉源后需要重新启动
    if pipeline.state.value == "running":
        await pipeline.stop()
    
    # 打开视觉源
    source_manager = pipeline.source_manager
    
    if suffix in image_exts:
        success = source_manager.open_image(file_path)
    else:
        success = source_manager.open_video(file_path)
    
    if not success:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="无法打开文件")
    
    info = source_manager.source_info
    
    # 尝试获取预览帧并发送到WebSocket（如果存在回调）
    preview_frame = source_manager._current_frame
    if preview_frame is not None and pipeline._on_frame_callback:
        # 编码预览帧
        preview_image_base64 = encode_frame_to_base64(preview_frame)
        
        # 构建帧消息
        from ...schemas.websocket import FrameMessage
        preview_message = FrameMessage(
            timestamp=time.time(),
            frame_id=0,  # 预览帧ID为0
            image=preview_image_base64,
            detections=[],  # 空检测列表
            emotions=[]     # 空情绪列表
        )
        
        # 异步发送预览帧
        import asyncio
        asyncio.create_task(pipeline._on_frame_callback(preview_message))

    # 如果原先是运行状态，现在视觉源已更改，应保持在idle状态
    # 实际的重启应该通过WebSocket命令来完成
    if info:
        return ApiResponse(
            data=SourceInfo(
                source_type=info.source_type.value,
                path=info.path,
                width=info.width,
                height=info.height,
                fps=info.fps,
                total_frames=info.total_frames
            ),
            message="文件上传成功"
        )
    else:
        raise HTTPException(status_code=400, detail="无法获取视觉源信息")


@router.post("/camera", response_model=ApiResponse[SourceInfo])
async def set_camera(
    request: CameraRequest,
    pipeline: Pipeline = Depends(get_pipeline)
) -> ApiResponse[SourceInfo]:
    """设置摄像头源"""
    # 如果流水线正在运行，则停止它，因为在切换视觉源后需要重新启动
    if pipeline.state.value == "running":
        await pipeline.stop()
    
    source_manager = pipeline.source_manager
    
    success = source_manager.open_camera(request.camera_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"无法打开摄像头 {request.camera_id}"
        )
    
    info = source_manager.source_info
    if info:
        return ApiResponse(
            data=SourceInfo(
                source_type=info.source_type.value,
                camera_id=info.camera_id,
                width=info.width,
                height=info.height,
                fps=info.fps
            ),
            message="摄像头设置成功"
        )
    else:
        raise HTTPException(status_code=400, detail="无法设置摄像头")


@router.get("/list", response_model=ApiResponse[List[CameraInfo]])
async def list_cameras() -> ApiResponse[List[CameraInfo]]:
    """列出可用摄像头"""
    camera_ids = SourceManager.list_cameras()
    cameras = [CameraInfo(id=cid) for cid in camera_ids]
    
    return ApiResponse(
        data=cameras,
        message=f"发现 {len(cameras)} 个摄像头"
    )


@router.get("/current", response_model=ApiResponse[Optional[SourceInfo]])
async def get_current_source(
    pipeline: Pipeline = Depends(get_pipeline)
) -> ApiResponse[Optional[SourceInfo]]:
    """获取当前视觉源信息"""
    info = pipeline.source_manager.source_info
    
    if info is None:
        return ApiResponse(data=None, message="未选择视觉源")
    
    # 动态构造SourceInfo，处理可能为None的字段
    source_info_data = {
        "source_type": info.source_type.value,
        "width": info.width,
        "height": info.height,
        "fps": info.fps,
    }
    
    # 根据source_type添加特定字段
    if info.source_type.value == "camera":
        source_info_data["camera_id"] = info.camera_id
    else:
        source_info_data["path"] = info.path
        source_info_data["total_frames"] = info.total_frames
    
    return ApiResponse(
        data=SourceInfo(**source_info_data),
        message="获取成功"
    )


@router.delete("/close", response_model=ApiResponse)
async def close_source(
    pipeline: Pipeline = Depends(get_pipeline)
) -> ApiResponse:
    """关闭当前视觉源"""
    pipeline.source_manager.close()
    return ApiResponse(message="视觉源已关闭")



