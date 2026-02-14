"""
图像预处理工具

提供裁剪、缩放、归一化等共享预处理函数，供所有情绪识别器使用
"""

from typing import Optional

import cv2
import numpy as np
import torch

from ...schemas.common import BoundingBox

# ============================================================
# 归一化常量（按区域类型分组）
# ============================================================

IMAGE_MEAN = [0.4690646, 0.4407227, 0.40508908]
IMAGE_STD = [0.2514227, 0.24312855, 0.24266963]

BODY_MEAN = [0.43832874, 0.3964344, 0.3706214]
BODY_STD = [0.24784276, 0.23621225, 0.2323653]

FACE_MEAN = [0.47491485, 0.37161113, 0.32988098]
FACE_STD = [0.28276006, 0.24852228, 0.24251911]


def crop_region(
    frame: np.ndarray,
    bbox: BoundingBox,
    target_size: tuple[int, int],
) -> np.ndarray:
    """
    从帧中裁剪指定区域并缩放到目标尺寸

    Args:
        frame: 输入图像帧 (BGR, HWC, uint8)
        bbox: 边界框
        target_size: 目标尺寸 (height, width)

    Returns:
        裁剪并缩放后的图像 (BGR, HWC, uint8)
    """
    h, w = frame.shape[:2]

    # 将 bbox 坐标裁剪到帧范围内
    x1 = max(0, int(bbox.x))
    y1 = max(0, int(bbox.y))
    x2 = min(w, int(bbox.x2))
    y2 = min(h, int(bbox.y2))

    # 处理无效区域（零面积）
    if x2 <= x1 or y2 <= y1:
        return np.zeros((target_size[0], target_size[1], 3), dtype=np.uint8)

    crop = frame[y1:y2, x1:x2]
    resized = cv2.resize(
        crop, (target_size[1], target_size[0]), interpolation=cv2.INTER_LINEAR
    )
    return resized


def to_normalized_tensor(
    crop: np.ndarray,
    mean: list[float],
    std: list[float],
) -> torch.Tensor:
    """
    将 BGR uint8 图像转换为归一化的 PyTorch 张量

    流程: BGR→RGB → HWC→CHW → /255.0 → per-channel normalize

    Args:
        crop: 输入图像 (BGR, HWC, uint8)
        mean: RGB 通道均值
        std: RGB 通道标准差

    Returns:
        归一化张量 (C, H, W), float32
    """
    # BGR → RGB
    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

    # HWC uint8 → CHW float32, /255.0
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div_(255.0)

    # Per-channel normalize
    mean_t = torch.tensor(mean, dtype=torch.float32).view(3, 1, 1)
    std_t = torch.tensor(std, dtype=torch.float32).view(3, 1, 1)
    tensor.sub_(mean_t).div_(std_t)

    return tensor


def prepare_context(
    frame: np.ndarray,
    size: tuple[int, int] = (224, 224),
) -> torch.Tensor:
    """
    预处理全图（上下文区域）

    Args:
        frame: 输入图像帧 (BGR, HWC, uint8)
        size: 目标尺寸 (height, width)

    Returns:
        归一化张量 (3, H, W)
    """
    resized = cv2.resize(frame, (size[1], size[0]), interpolation=cv2.INTER_LINEAR)
    return to_normalized_tensor(resized, IMAGE_MEAN, IMAGE_STD)


def prepare_face(
    frame: np.ndarray,
    bbox: BoundingBox,
    size: tuple[int, int] = (224, 224),
) -> torch.Tensor:
    """
    预处理人脸区域

    Args:
        frame: 输入图像帧 (BGR, HWC, uint8)
        bbox: 人脸边界框
        size: 目标尺寸 (height, width)

    Returns:
        归一化张量 (3, H, W)
    """
    crop = crop_region(frame, bbox, size)
    return to_normalized_tensor(crop, FACE_MEAN, FACE_STD)


def prepare_body(
    frame: np.ndarray,
    bbox: BoundingBox,
    size: tuple[int, int] = (224, 224),
) -> torch.Tensor:
    """
    预处理人体区域

    Args:
        frame: 输入图像帧 (BGR, HWC, uint8)
        bbox: 人体边界框
        size: 目标尺寸 (height, width)

    Returns:
        归一化张量 (3, H, W)
    """
    crop = crop_region(frame, bbox, size)
    return to_normalized_tensor(crop, BODY_MEAN, BODY_STD)


def batch_tensors(
    tensors: list[torch.Tensor],
    device: torch.device,
) -> Optional[torch.Tensor]:
    """
    将张量列表堆叠为批次并移至指定设备

    Args:
        tensors: 张量列表，每个形状为 (C, H, W)
        device: 目标设备

    Returns:
        批次张量 (B, C, H, W)，列表为空时返回 None
    """
    if not tensors:
        return None
    return torch.stack(tensors).to(device)
