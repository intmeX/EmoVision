"""
帧渲染器

在图像帧上绘制检测结果和情绪标签
"""

import base64
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from ..detector.schemas import Detection, DetectionType
from ..recognizer.schemas import EmotionResult
from ...schemas.pipeline import VisualizerConfig
from ...utils.logger import get_logger

logger = get_logger(__name__)


def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
    """将十六进制颜色转换为BGR格式"""
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (rgb[2], rgb[1], rgb[0])  # BGR


class FrameRenderer:
    """
    帧渲染器
    
    负责在图像帧上绘制检测框、情绪标签等可视化元素
    """
    
    def __init__(self, config: VisualizerConfig):
        """
        初始化渲染器
        
        Args:
            config: 可视化配置
        """
        self._config = config
        self._emotion_color_cache: Dict[str, Tuple[int, int, int]] = {}
        self._update_color_cache()
    
    def _update_color_cache(self) -> None:
        """更新颜色缓存"""
        self._emotion_color_cache = {
            emotion: hex_to_bgr(color)
            for emotion, color in self._config.emotion_colors.items()
        }
        # 默认颜色
        self._default_color = (128, 128, 128)  # 灰色
    
    def update_config(self, config: VisualizerConfig) -> None:
        """更新配置"""
        self._config = config
        self._update_color_cache()
    
    def render(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        emotions: Optional[List[EmotionResult]] = None
    ) -> np.ndarray:
        """
        渲染帧
        
        Args:
            frame: 输入图像帧 (BGR格式)
            detections: 检测结果列表
            emotions: 情绪识别结果列表 (可选)
            
        Returns:
            渲染后的图像帧
        """
        # 复制帧以避免修改原始数据
        rendered = frame.copy()
        
        # 构建检测ID到情绪结果的映射
        emotion_map: Dict[int, EmotionResult] = {}
        if emotions:
            emotion_map = {e.detection_id: e for e in emotions}
        
        # 绘制检测结果
        for detection in detections:
            self._draw_detection(rendered, detection, emotion_map.get(detection.id))
        
        return rendered
    
    def _draw_detection(
        self,
        frame: np.ndarray,
        detection: Detection,
        emotion: Optional[EmotionResult] = None
    ) -> None:
        """
        绘制单个检测结果
        
        Args:
            frame: 图像帧
            detection: 检测结果
            emotion: 情绪识别结果 (可选)
        """
        bbox = detection.bbox
        x1, y1, x2, y2 = int(bbox.x), int(bbox.y), int(bbox.x2), int(bbox.y2)
        
        # 确定颜色
        if self._config.box_color_by_emotion and emotion:
            color = self._emotion_color_cache.get(
                emotion.dominant_emotion, self._default_color
            )
        else:
            # 根据检测类型使用默认颜色
            color = (0, 255, 0) if detection.type == DetectionType.FACE else (255, 0, 0)
        
        # 绘制边界框
        if self._config.show_bounding_box:
            cv2.rectangle(
                frame, (x1, y1), (x2, y2),
                color, self._config.box_thickness
            )
        
        # 绘制标签
        if emotion and (self._config.show_emotion_label or self._config.show_confidence):
            self._draw_label(frame, x1, y1, emotion, color)
        
        # 绘制情绪概率条
        if emotion and self._config.show_emotion_bar:
            self._draw_emotion_bar(frame, x1, y2, emotion)
    
    def _draw_label(
        self,
        frame: np.ndarray,
        x: int,
        y: int,
        emotion: EmotionResult,
        color: Tuple[int, int, int]
    ) -> None:
        """
        绘制情绪标签
        
        Args:
            frame: 图像帧
            x, y: 标签位置
            emotion: 情绪识别结果
            color: 标签颜色
        """
        # 构建标签文本
        parts = []
        if self._config.show_emotion_label:
            parts.append(emotion.dominant_emotion)
        if self._config.show_confidence:
            parts.append(f"{emotion.confidence:.0%}")
        
        label = " ".join(parts)
        
        # 计算文本大小
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = self._config.font_scale * 0.5
        thickness = max(1, int(self._config.font_scale))
        
        (text_width, text_height), baseline = cv2.getTextSize(
            label, font, font_scale, thickness
        )
        
        # 绘制背景
        padding = 4
        bg_y1 = max(0, y - text_height - padding * 2)
        bg_y2 = y
        bg_x2 = x + text_width + padding * 2
        
        cv2.rectangle(frame, (x, bg_y1), (bg_x2, bg_y2), color, -1)
        
        # 绘制文本
        text_y = y - padding
        cv2.putText(
            frame, label, (x + padding, text_y),
            font, font_scale, (255, 255, 255), thickness
        )
    
    def _draw_emotion_bar(
        self,
        frame: np.ndarray,
        x: int,
        y: int,
        emotion: EmotionResult
    ) -> None:
        """
        绘制情绪概率条
        
        Args:
            frame: 图像帧
            x, y: 概率条起始位置
            emotion: 情绪识别结果
        """
        bar_height = 8
        bar_width = 120
        padding = 2
        
        # 按概率排序
        sorted_emotions = sorted(
            emotion.probabilities.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]  # 只显示前3个
        
        current_y = y + padding
        
        for label, prob in sorted_emotions:
            color = self._emotion_color_cache.get(label, self._default_color)
            
            # 背景条
            cv2.rectangle(
                frame,
                (x, current_y),
                (x + bar_width, current_y + bar_height),
                (50, 50, 50), -1
            )
            
            # 概率条
            fill_width = int(bar_width * prob)
            if fill_width > 0:
                cv2.rectangle(
                    frame,
                    (x, current_y),
                    (x + fill_width, current_y + bar_height),
                    color, -1
                )
            
            current_y += bar_height + padding
    
    def encode_frame(
        self,
        frame: np.ndarray,
        quality: int = 80
    ) -> str:
        """
        将帧编码为Base64字符串
        
        Args:
            frame: 图像帧
            quality: JPEG压缩质量
            
        Returns:
            Base64编码的JPEG图像字符串
        """
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        _, buffer = cv2.imencode('.jpg', frame, encode_params)
        return base64.b64encode(buffer).decode('utf-8')
