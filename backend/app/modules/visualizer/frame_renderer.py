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
        face_index = 0
        for detection in detections:
            current_face_index = None
            if detection.type == DetectionType.FACE:
                face_index += 1
                current_face_index = face_index
            
            self._draw_detection(
                rendered, 
                detection, 
                emotion_map.get(detection.id),
                face_index=current_face_index
            )

        return rendered

    def _draw_detection(
        self,
        frame: np.ndarray,
        detection: Detection,
        emotion: Optional[EmotionResult] = None,
        face_index: Optional[int] = None,
    ) -> None:
        """
        绘制单个检测结果

        Args:
            frame: 图像帧
            detection: 检测结果
            emotion: 情绪识别结果 (可选)
            face_index: 面部索引 (可选)
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

        # 绘制边界框：面部框受 show_bounding_box 控制，人体框受 show_person_box 控制
        if detection.type == DetectionType.FACE:
            if not self._config.show_bounding_box:
                pass  # 不绘制面部框，但继续绘制标签
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, self._config.box_thickness)
                
                # 绘制面部索引数字 (1, 2, 3...) 到右下角
                if face_index is not None:
                    text = str(face_index)
                    # 获取文本尺寸
                    bbox = self._font.getbbox(text)
                    tw = int(bbox[2] - bbox[0])
                    th = int(bbox[3] - bbox[1])
                    
                    # 计算位置 (右下角，留2像素边距)
                    tx = x2 - tw - 2
                    ty = y2 - th - 2 - bbox[1] # 考虑 baseline
                    
                    # 确保不超出画面
                    frame_h, frame_w = frame.shape[:2]
                    tx = max(0, min(frame_w - tw, tx))
                    ty = max(0, min(frame_h - th, ty))
                    
                    # 使用 PIL 绘制（透明背景，黑色文字）
                    # 确定 ROI
                    roi_x1, roi_y1 = int(tx), int(ty + bbox[1])
                    roi_x2, roi_y2 = int(tx + tw), int(ty + th + bbox[1])
                    
                    if 0 <= roi_x1 < frame_w and 0 <= roi_y1 < frame_h:
                        roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
                        pil_roi = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
                        draw = ImageDraw.Draw(pil_roi)
                        draw.text((0, -bbox[1]), text, font=self._font, fill=(0, 0, 0))
                        frame[roi_y1:roi_y2, roi_x1:roi_x2] = cv2.cvtColor(
                            np.array(pil_roi), cv2.COLOR_RGB2BGR
                        )
        elif detection.type == DetectionType.PERSON:
            if not self._config.show_person_box:
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
        绘制多级情绪标签（使用PIL支持中文渲染，透明背景）

        Args:
            frame: 图像帧
            x, y: 边界框左上角坐标
            y2: 边界框底部 y 坐标
            emotion: 情绪识别结果
            color: 标签主颜色 (BGR) - 当前主要由边框逻辑决定，各标签使用各自颜色
        """
        frame_h, frame_w = frame.shape[:2]

        # 1. 准备要绘制的所有标签数据
        display_count = getattr(self._config, "emotion_display_count", 2)
        sorted_emotions = sorted(
            emotion.probabilities.items(), key=lambda x: x[1], reverse=True
        )[:display_count]

        labels_data = []
        max_text_width = 0
        total_stack_height = 0
        padding = 4

        for i, (emotion_label, prob) in enumerate(sorted_emotions):
            parts: List[str] = []
            if self._config.show_emotion_label:
                parts.append(emotion_label)
            if self._config.show_confidence:
                parts.append(f"{prob:.2f}")

            if not parts:
                continue

            text = " ".join(parts)
            # 使用 PIL 测量文本尺寸
            bbox = self._font.getbbox(text)
            tw = int(bbox[2] - bbox[0])
            th = int(bbox[3] - bbox[1])

            # 获取颜色 (从缓存中获取 BGR 并转换为 RGB 用于 PIL)
            bgr = self._emotion_color_cache.get(emotion_label, self._default_color)
            rgb = (bgr[2], bgr[1], bgr[0])

            label_h = th + padding * 2
            
            labels_data.append({
                "text": text,
                "rgb": rgb,
                "tw": tw,
                "th": th,
                "label_h": label_h,
                "y_offset": bbox[1]
            })

            max_text_width = max(max_text_width, tw)
            total_stack_height += label_h
            if i < len(sorted_emotions) - 1:
                total_stack_height += padding

        if not labels_data:
            return

        # 2. 确定堆栈起始位置（基于第一个标签的逻辑：上方或内部顶端）
        first_label_h = labels_data[0]["label_h"]
        if y - first_label_h >= 0:
            stack_y_start = y - first_label_h
        else:
            stack_y_start = y

        # 水平方向：超出右边界时左移，超出左边界时右移
        stack_w = max_text_width + padding * 2
        stack_x_start = x
        if stack_x_start + stack_w > frame_w:
            stack_x_start = frame_w - stack_w
        stack_x_start = max(0, stack_x_start)

        # 3. 确定绘制区域 (ROI)
        roi_x1 = int(max(0, stack_x_start))
        roi_y1 = int(max(0, stack_y_start))
        roi_x2 = int(min(frame_w, stack_x_start + stack_w))
        roi_y2 = int(min(frame_h, stack_y_start + total_stack_height))

        if roi_x2 <= roi_x1 or roi_y2 <= roi_y1:
            return

        # 4. 使用 PIL 绘制文本（直接在 ROI 上绘制实现透明背景效果）
        roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
        pil_roi = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_roi)

        current_y_offset = 0
        for item in labels_data:
            # 文本在 ROI 内的相对偏移
            text_x = int(stack_x_start + padding - roi_x1)
            text_y = int(stack_y_start + current_y_offset + padding - roi_y1 - item["y_offset"])

            draw.text((text_x, text_y), item["text"], font=self._font, fill=item["rgb"])
            current_y_offset += item["label_h"] + padding

        # 5. 写回 frame (RGB -> BGR)
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

        # 按概率排序，使用配置的显示数量
        display_count = getattr(self._config, 'emotion_display_count', 2)
        sorted_emotions = sorted(
            emotion.probabilities.items(), key=lambda x: x[1], reverse=True
        )[:display_count]

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
        return base64.b64encode(buffer.tobytes()).decode("utf-8")
