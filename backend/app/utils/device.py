"""
设备管理模块

GPU/CPU设备检测与选择
"""

from dataclasses import dataclass
from typing import Literal, Optional

import torch

from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class DeviceInfo:
    """设备信息"""
    device_type: str  # "cuda" 或 "cpu"
    device_name: str  # 设备名称
    device_index: Optional[int]  # CUDA设备索引
    total_memory: Optional[int]  # 显存大小(字节)
    cuda_version: Optional[str]  # CUDA版本


def get_device_info() -> DeviceInfo:
    """
    获取当前设备信息
    
    Returns:
        设备信息对象
    """
    if torch.cuda.is_available():
        device_index = torch.cuda.current_device()
        device_name = torch.cuda.get_device_name(device_index)
        total_memory = torch.cuda.get_device_properties(device_index).total_memory
        cuda_version = torch.version.cuda
        
        return DeviceInfo(
            device_type="cuda",
            device_name=device_name,
            device_index=device_index,
            total_memory=total_memory,
            cuda_version=cuda_version
        )
    else:
        import platform
        return DeviceInfo(
            device_type="cpu",
            device_name=platform.processor() or "Unknown CPU",
            device_index=None,
            total_memory=None,
            cuda_version=None
        )


def select_device(
    device: Literal["auto", "cuda", "cpu"] = "auto",
    device_index: int = 0
) -> torch.device:
    """
    选择推理设备
    
    Args:
        device: 设备类型，auto会自动选择可用的GPU
        device_index: CUDA设备索引
        
    Returns:
        PyTorch设备对象
    """
    if device == "auto":
        if torch.cuda.is_available():
            selected = torch.device(f"cuda:{device_index}")
            logger.info(f"自动选择GPU设备: {torch.cuda.get_device_name(device_index)}")
        else:
            selected = torch.device("cpu")
            logger.info("未检测到GPU，使用CPU设备")
    elif device == "cuda":
        if torch.cuda.is_available():
            selected = torch.device(f"cuda:{device_index}")
            logger.info(f"使用GPU设备: {torch.cuda.get_device_name(device_index)}")
        else:
            logger.warning("请求使用GPU但未检测到可用GPU，回退到CPU")
            selected = torch.device("cpu")
    else:
        selected = torch.device("cpu")
        logger.info("使用CPU设备")
    
    return selected


def get_gpu_memory_usage() -> Optional[dict]:
    """
    获取GPU显存使用情况
    
    Returns:
        显存使用信息字典，无GPU时返回None
    """
    if not torch.cuda.is_available():
        return None
    
    device_index = torch.cuda.current_device()
    total = torch.cuda.get_device_properties(device_index).total_memory
    allocated = torch.cuda.memory_allocated(device_index)
    reserved = torch.cuda.memory_reserved(device_index)
    
    return {
        "total_mb": total / (1024 * 1024),
        "allocated_mb": allocated / (1024 * 1024),
        "reserved_mb": reserved / (1024 * 1024),
        "free_mb": (total - allocated) / (1024 * 1024),
        "usage_percent": allocated / total * 100 if total > 0 else 0
    }
