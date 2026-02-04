"""
测试工具函数
"""
import numpy as np
import cv2
import base64
from app.utils.frame_utils import encode_frame_to_jpeg, decode_jpeg_from_base64


class TestFrameUtils:
    """帧工具函数测试"""
    
    def test_encode_decode_cycle(self):
        """测试编码解码循环"""
        # 创建一个简单的测试图像
        test_frame = np.ones((100, 100, 3), dtype=np.uint8) * 128  # 灰色图像
        
        # 编码
        encoded = encode_frame_to_jpeg(test_frame, quality=80)
        
        # 解码
        decoded = decode_jpeg_from_base64(encoded)
        
        # 验证
        assert decoded is not None
        assert isinstance(decoded, np.ndarray)
        # Note: Due to JPEG compression, decoded image may not be identical to original
        # but it should have similar dimensions
        assert decoded.shape == test_frame.shape