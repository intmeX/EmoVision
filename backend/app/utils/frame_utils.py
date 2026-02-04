"""
帧处理工具函数

提供图像帧编码、解码和相关操作的工具函数
"""

import base64
from typing import Optional

import cv2
import numpy as np


def encode_frame_to_jpeg(frame: np.ndarray, quality: int = 80) -> str:
    """
    将图像帧编码为JPEG base64字符串
    
    Args:
        frame: 图像帧 (BGR格式, HWC排列)
        quality: JPEG压缩质量 (1-100)
        
    Returns:
        base64编码的JPEG图像字符串
    """
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buffer = cv2.imencode('.jpg', frame, encode_params)
    buffer_bytes = np.array(buffer).tobytes()
    return base64.b64encode(buffer_bytes).decode('utf-8')


def decode_jpeg_from_base64(image_base64: str) -> Optional[np.ndarray]:
    """
    将base64编码的JPEG图像解码为numpy数组
    
    Args:
        image_base64: base64编码的JPEG图像字符串
        
    Returns:
        解码后的图像数组，失败时返回None
    """
    try:
        image_bytes = base64.b64decode(image_base64)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    except Exception:
        return None


# TurboJPEG support (optional, faster encoding)
try:
    from turbojpeg import TurboJPEG, TJPF_BGR
    _jpeg: TurboJPEG | None = TurboJPEG()
    _TJPF_BGR = TJPF_BGR
except ImportError:
    _jpeg = None
    _TJPF_BGR = 0  # Placeholder, won't be used if _jpeg is None


def encode_frame_turbo(frame: np.ndarray, quality: int = 80) -> bytes:
    """
    使用TurboJPEG编码帧为JPEG字节（比cv2快2-3倍）
    
    Args:
        frame: 图像帧 (BGR格式, HWC排列)
        quality: JPEG压缩质量 (1-100)
        
    Returns:
        JPEG编码的字节数据
        
    Raises:
        RuntimeError: 如果TurboJPEG未安装
    """
    if _jpeg is None:
        raise RuntimeError(
            "TurboJPEG not installed. Install with: pip install PyTurboJPEG"
        )
    return _jpeg.encode(frame, quality=quality, pixel_format=_TJPF_BGR)


def encode_frame_bytes(frame: np.ndarray, quality: int = 80) -> bytes:
    """
    将帧编码为JPEG字节（优先使用TurboJPEG，回退到OpenCV）
    
    Args:
        frame: 图像帧 (BGR格式, HWC排列)
        quality: JPEG压缩质量 (1-100)
        
    Returns:
        JPEG编码的字节数据
    """
    if _jpeg is not None:
        return _jpeg.encode(frame, quality=quality, pixel_format=_TJPF_BGR)
    else:
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        _, buffer = cv2.imencode('.jpg', frame, encode_params)
        return np.array(buffer).tobytes()


def is_turbojpeg_available() -> bool:
    """检查TurboJPEG是否可用"""
    return _jpeg is not None


def get_preview_frame(cap: cv2.VideoCapture) -> Optional[np.ndarray]:
    """
    从视频捕获对象获取预览帧
    
    Args:
        cap: OpenCV视频捕获对象
        
    Returns:
        预览帧，失败时返回None
    """
    try:
        # 保存当前位置
        current_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        # 跳转到第一帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        # 读取第一帧
        ret, frame = cap.read()
        # 恢复原始位置
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
        return frame if ret else None
    except Exception:
        return None