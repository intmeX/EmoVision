"""
帧渲染器

在图像帧上绘制检测结果和情绪标签
"""

import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ...schemas.pipeline import VisualizerConfig
from ...utils.logger import get_logger
from ..detector.schemas import Detection, DetectionType
from ..recognizer.schemas import EmotionResult

logger = get_logger(__name__)

# 字体搜索路径（优先使用项目内置字体）
_FONT_SEARCH_PATHS = [
    Path(__file__).resolve().parent.parent.parent
    / "assets"
    / "fonts"
    / "NotoSansSC-Regular.ttf",
    Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf"),
    Path("/System/Library/Fonts/PingFang.ttc"),
]


def _load_cjk_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """加载支持中文的字体，按优先级尝试多个路径"""
    for font_path in _FONT_SEARCH_PATHS:
        if font_path.exists():
            try:
                font = ImageFont.truetype(str(font_path), size)
                logger.info("已加载字体: %s (size=%d)", font_path.name, size)
                return font
            except Exception:
                logger.debug("字体加载失败: %s", font_path)
                continue
    logger.warning("未找到CJK字体，回退到PIL默认字体")
    return ImageFont.load_default()


def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
    """将十六进制颜色转换为BGR格式"""
    hex_color = hex_color.lstrip("#")
    rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
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
        self._font = _load_cjk_font(self._font_size)
        self._update_color_cache()

    @property
    def _font_size(self) -> int:
        """根据 font_scale 计算 PIL 字体像素大小"""
        return max(12, int(self._config.font_scale * 20))

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
        old_font_size = self._font_size
        self._config = config
        self._update_color_cache()
        if self._font_size != old_font_size:
            self._font = _load_cjk_font(self._font_size)

    def render(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        emotions: Optional[List[EmotionResult]] = None,
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
        emotion: Optional[EmotionResult] = None,
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

        # 绘制边界框（person 框受 show_person_box 控制）
        if self._config.show_bounding_box:
            if (
                detection.type == DetectionType.PERSON
                and not self._config.show_person_box
            ):
                return  # 跳过 person 框及其标签
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, self._config.box_thickness)

        # 绘制标签
        if emotion and (
            self._config.show_emotion_label or self._config.show_confidence
        ):
            self._draw_label(frame, x1, y1, y2, emotion, color)

        # 绘制情绪概率条
        if emotion and self._config.show_emotion_bar:
            self._draw_emotion_bar(frame, x1, y2, emotion)

    def _draw_label(
        self,
        frame: np.ndarray,
        x: int,
        y: int,
        y2: int,
        emotion: EmotionResult,
        color: Tuple[int, int, int],
    ) -> None:
        """
        绘制情绪标签（使用PIL支持中文渲染）

        当标签放在框上方会超出帧边界时，自动改为放在框内部顶端。

        Args:
            frame: 图像帧
            x, y: 边界框左上角坐标
            y2: 边界框底部 y 坐标
            emotion: 情绪识别结果
            color: 标签颜色 (BGR)
        """
        frame_h, frame_w = frame.shape[:2]

        # 构建标签文本
        parts: List[str] = []
        if self._config.show_emotion_label:
            parts.append(emotion.dominant_emotion)
        if self._config.show_confidence:
            parts.append(f"{emotion.confidence:.2f}")

        label = " ".join(parts)

        # 使用 PIL 测量文本尺寸
        bbox = self._font.getbbox(label)
        text_width = int(bbox[2] - bbox[0])
        text_height = int(bbox[3] - bbox[1])

        padding = 4
        label_h = text_height + padding * 2

        # 默认放在框上方；空间不足时放到框内部顶端
        if y - label_h >= 0:
            bg_y1 = y - label_h
            bg_y2 = y
        else:
            bg_y1 = y
            bg_y2 = min(y + label_h, frame_h)

        # 水平方向：超出右边界时整体左移，超出左边界时右移
        label_w = text_width + padding * 2
        bg_x1 = x
        if bg_x1 + label_w > frame_w:
            bg_x1 = frame_w - label_w
        bg_x1 = max(0, bg_x1)
        bg_x2 = bg_x1 + label_w

        # 绘制背景矩形（仍用 cv2，快速）
        cv2.rectangle(frame, (bg_x1, bg_y1), (bg_x2, bg_y2), color, -1)

        # 使用 PIL 绘制文本（仅转换标签区域，避免全帧转换开销）
        roi_x1 = max(0, bg_x1)
        roi_y1 = max(0, bg_y1)
        roi_x2 = min(frame_w, bg_x2)
        roi_y2 = min(frame_h, bg_y2)

        if roi_x2 <= roi_x1 or roi_y2 <= roi_y1:
            return

        roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
        pil_roi = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_roi)

        # 文本在 ROI 内的偏移
        text_x = bg_x1 + padding - roi_x1
        text_y = bg_y1 + padding - roi_y1 - bbox[1]
        draw.text((text_x, text_y), label, font=self._font, fill=(255, 255, 255))

        frame[roi_y1:roi_y2, roi_x1:roi_x2] = cv2.cvtColor(
            np.array(pil_roi), cv2.COLOR_RGB2BGR
        )

    def _draw_emotion_bar(
        self, frame: np.ndarray, x: int, y: int, emotion: EmotionResult
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
            emotion.probabilities.items(), key=lambda x: x[1], reverse=True
        )[:3]  # 只显示前3个

        current_y = y + padding

        for label, prob in sorted_emotions:
            color = self._emotion_color_cache.get(label, self._default_color)

            # 背景条
            cv2.rectangle(
                frame,
                (x, current_y),
                (x + bar_width, current_y + bar_height),
                (50, 50, 50),
                -1,
            )

            # 概率条
            fill_width = int(bar_width * prob)
            if fill_width > 0:
                cv2.rectangle(
                    frame,
                    (x, current_y),
                    (x + fill_width, current_y + bar_height),
                    color,
                    -1,
                )

            current_y += bar_height + padding

    def encode_frame(self, frame: np.ndarray, quality: int = 80) -> str:
        """
        将帧编码为Base64字符串

        Args:
            frame: 图像帧
            quality: JPEG压缩质量

        Returns:
            Base64编码的JPEG图像字符串
        """
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        _, buffer = cv2.imencode(".jpg", frame, encode_params)
        return base64.b64encode(buffer).decode("utf-8")
