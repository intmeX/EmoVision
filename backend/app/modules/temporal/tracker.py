"""面部跟踪器

集成 ByteTrack、边界框平滑、情绪融合和标签决策的完整跟踪器。
"""

import time
from typing import Dict, List, Tuple

import numpy as np

from ...modules.detector.schemas import Detection, DetectionType
from ...modules.recognizer.schemas import EmotionResult
from ...schemas.common import BoundingBox
from ...utils.logger import get_logger
from .bbox_smoother import BboxSmoother
from .emotion_fusion import EmotionFusion
from .label_policy import LabelPolicy
from .track_state import TrackState

logger = get_logger(__name__)


class FaceTracker:
    """
    面部跟踪器

    整合时序平滑的完整流水线：
    1. ByteTrack 分配持久 track_id
    2. One Euro Filter 平滑边界框
    3. 多尺度情绪融合
    4. 滞后标签决策
    """

    def __init__(
        self,
        track_thresh: float = 0.5,
        track_buffer: int = 30,
        match_thresh: float = 0.8,
        frame_rate: int = 30,
        # 边界框平滑参数
        bbox_min_cutoff: float = 1.0,
        bbox_beta: float = 0.007,
        # 情绪融合参数
        emotion_alpha_fast: float = 0.7,
        emotion_alpha_med: float = 0.4,
        emotion_alpha_slow: float = 0.18,
        # 标签决策参数
        label_switch_margin: float = 0.08,
        label_min_conf: float = 0.45,
        label_dwell_frames: int = 4,
    ):
        """
        初始化面部跟踪器

        Args:
            track_thresh: 跟踪置信度阈值
            track_buffer: 跟踪缓冲帧数
            match_thresh: 匹配 IoU 阈值
            frame_rate: 视频帧率
            bbox_min_cutoff: 边界框平滑最小截止频率
            bbox_beta: 边界框平滑速度系数
            emotion_alpha_fast: 情绪快速分支 EMA 系数
            emotion_alpha_med: 情绪中速分支 EMA 系数
            emotion_alpha_slow: 情绪慢速分支 EMA 系数
            label_switch_margin: 标签切换所需置信度差距
            label_min_conf: 标签切换最小置信度
            label_dwell_frames: 标签切换驻留帧数
        """
        # ByteTrack 参数
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.frame_rate = frame_rate

        # 轨迹状态字典 {track_id: TrackState}
        self.tracks: Dict[int, TrackState] = {}

        # 下一个可用的 track_id
        self._next_track_id = 1

        # 帧计数
        self.frame_count = 0

        # 平滑器和融合器的默认参数
        self.bbox_min_cutoff = bbox_min_cutoff
        self.bbox_beta = bbox_beta
        self.emotion_alpha_fast = emotion_alpha_fast
        self.emotion_alpha_med = emotion_alpha_med
        self.emotion_alpha_slow = emotion_alpha_slow
        self.label_switch_margin = label_switch_margin
        self.label_min_conf = label_min_conf
        self.label_dwell_frames = label_dwell_frames

    def update(
        self,
        detections: List[Detection],
        emotions: List[EmotionResult],
        frame_shape: Tuple[int, int],
    ) -> Tuple[List[Detection], List[EmotionResult]]:
        """
        更新跟踪器并返回平滑后的检测和情绪结果

        Args:
            detections: 原始检测结果列表
            emotions: 原始情绪识别结果列表
            frame_shape: 帧尺寸 (height, width)

        Returns:
            (平滑后的检测列表, 平滑后的情绪列表)
        """
        self.frame_count += 1
        timestamp = time.time()

        # 构建情绪字典 {detection_id: EmotionResult}
        emotion_map = {e.detection_id: e for e in emotions}

        # 简化版跟踪：使用 IoU 匹配
        tracked_detections, tracked_emotions = self._simple_track(
            detections, emotion_map, timestamp, frame_shape
        )

        # 清理过期轨迹
        self._cleanup_stale_tracks()

        return tracked_detections, tracked_emotions

    def _simple_track(
        self,
        detections: List[Detection],
        emotion_map: Dict[int, EmotionResult],
        timestamp: float,
        frame_shape: Tuple[int, int],
    ) -> Tuple[List[Detection], List[EmotionResult]]:
        """
        简化版跟踪实现（使用 IoU 匹配）

        Args:
            detections: 检测列表
            emotion_map: 情绪字典
            timestamp: 时间戳
            frame_shape: 帧尺寸

        Returns:
            (跟踪后的检测, 跟踪后的情绪)
        """
        # 只跟踪人脸，人体框直接透传
        face_detections = [d for d in detections if d.type == DetectionType.FACE]
        person_detections = [d for d in detections if d.type == DetectionType.PERSON]

        if not face_detections:
            # 所有轨迹标记为未更新
            for track in self.tracks.values():
                track.update_age(matched=False)
            # 人体框直接透传，不做跟踪平滑
            return person_detections, []

        # 匹配现有轨迹
        matched_tracks = {}
        unmatched_detections = []

        for det in face_detections:
            best_track_id = None
            best_iou = 0.0

            # 寻找最佳匹配轨迹
            for track_id, track_state in self.tracks.items():
                if track_state.prev_bbox is None:
                    continue

                # 计算 IoU
                prev_bbox = BoundingBox(
                    x=track_state.prev_bbox[0],
                    y=track_state.prev_bbox[1],
                    width=track_state.prev_bbox[2],
                    height=track_state.prev_bbox[3],
                )
                iou = det.bbox.iou(prev_bbox)

                if iou > best_iou and iou > self.match_thresh:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id is not None:
                matched_tracks[best_track_id] = det
            else:
                unmatched_detections.append(det)

        # 更新匹配的轨迹
        tracked_detections = []
        tracked_emotions = []

        for track_id, det in matched_tracks.items():
            track_state = self.tracks[track_id]
            track_state.update_age(matched=True)

            # 应用时序平滑
            smoothed_det, smoothed_emo = self._apply_temporal_smoothing(
                track_id, track_state, det, emotion_map.get(det.id), timestamp
            )

            if smoothed_det:
                tracked_detections.append(smoothed_det)
            if smoothed_emo:
                tracked_emotions.append(smoothed_emo)

        # 创建新轨迹
        for det in unmatched_detections:
            track_id = self._next_track_id
            self._next_track_id += 1

            track_state = TrackState(track_id=track_id, last_ts=timestamp)
            self.tracks[track_id] = track_state
            track_state.update_age(matched=True)

            # 初始化平滑（首帧直接使用原始值）
            smoothed_det, smoothed_emo = self._apply_temporal_smoothing(
                track_id, track_state, det, emotion_map.get(det.id), timestamp
            )

            if smoothed_det:
                tracked_detections.append(smoothed_det)
            if smoothed_emo:
                tracked_emotions.append(smoothed_emo)

        # 未匹配的轨迹标记为未更新
        for track_id in self.tracks:
            if track_id not in matched_tracks:
                self.tracks[track_id].update_age(matched=False)

        # 人体框直接透传（不做跟踪平滑）
        tracked_detections.extend(person_detections)

        return tracked_detections, tracked_emotions

    def _apply_temporal_smoothing(
        self,
        track_id: int,
        track_state: TrackState,
        detection: Detection,
        emotion: EmotionResult | None,
        timestamp: float,
    ) -> Tuple[Detection | None, EmotionResult | None]:
        """
        对单个轨迹应用时序平滑

        Args:
            track_id: 轨迹 ID
            track_state: 轨迹状态
            detection: 原始检测
            emotion: 原始情绪（可能为 None）
            timestamp: 时间戳

        Returns:
            (平滑后的检测, 平滑后的情绪)
        """
        # 1. 边界框平滑（One Euro Filter）
        smoothed_bbox = self._smooth_bbox(track_state, detection.bbox, timestamp)

        # 2. 估计运动水平
        motion_level = self._estimate_motion(track_state, smoothed_bbox)

        # 3. 更新前一帧边界框
        track_state.prev_bbox = (
            smoothed_bbox.x,
            smoothed_bbox.y,
            smoothed_bbox.width,
            smoothed_bbox.height,
        )
        track_state.motion_level = motion_level

        # 创建平滑后的检测
        smoothed_detection = Detection(
            id=track_id,  # 使用 track_id 作为 id
            type=detection.type,
            bbox=smoothed_bbox,
            confidence=detection.confidence,
            paired_id=detection.paired_id,
        )

        # 4. 情绪融合和标签决策
        if emotion is None:
            return smoothed_detection, None

        smoothed_emotion = self._smooth_emotion(
            track_state, emotion, motion_level, timestamp, track_id
        )

        return smoothed_detection, smoothed_emotion

    def _smooth_bbox(
        self, track_state: TrackState, bbox: BoundingBox, timestamp: float
    ) -> BoundingBox:
        """使用 One Euro Filter 平滑边界框"""
        # 懒初始化平滑器
        if not hasattr(track_state, "_bbox_smoother"):
            track_state._bbox_smoother = BboxSmoother(  # type: ignore
                min_cutoff=self.bbox_min_cutoff,
                beta=self.bbox_beta,
            )

        return track_state._bbox_smoother.smooth(bbox, timestamp)  # type: ignore

    def _estimate_motion(
        self, track_state: TrackState, current_bbox: BoundingBox
    ) -> float:
        """估计运动水平（0-1）"""
        if track_state.prev_bbox is None:
            return 0.0

        prev_center = (
            track_state.prev_bbox[0] + track_state.prev_bbox[2] / 2,
            track_state.prev_bbox[1] + track_state.prev_bbox[3] / 2,
        )
        curr_center = current_bbox.center

        # 计算中心点位移（归一化到边界框尺寸）
        dx = abs(curr_center[0] - prev_center[0]) / max(current_bbox.width, 1.0)
        dy = abs(curr_center[1] - prev_center[1]) / max(current_bbox.height, 1.0)

        # 运动水平（限制在 0-1）
        motion = min(1.0, (dx + dy) * 2.0)
        return motion

    def _smooth_emotion(
        self,
        track_state: TrackState,
        emotion: EmotionResult,
        motion_level: float,
        timestamp: float,
        track_id: int,
    ) -> EmotionResult:
        """平滑情绪概率并应用标签决策"""
        # 懒初始化情绪融合器和标签策略
        if not hasattr(track_state, "_emotion_fusion"):
            track_state._emotion_fusion = EmotionFusion(  # type: ignore
                alpha_fast=self.emotion_alpha_fast,
                alpha_med=self.emotion_alpha_med,
                alpha_slow=self.emotion_alpha_slow,
                num_classes=len(emotion.probabilities),
            )
        if not hasattr(track_state, "_label_policy"):
            track_state._label_policy = LabelPolicy(  # type: ignore
                switch_margin=self.label_switch_margin,
                min_conf_to_switch=self.label_min_conf,
                dwell_frames=self.label_dwell_frames,
            )

        # 转换概率字典为数组
        emotion_labels = sorted(emotion.probabilities.keys())
        prob_array = np.array([emotion.probabilities[label] for label in emotion_labels])

        # 多尺度融合
        fused_probs = track_state._emotion_fusion.update(  # type: ignore
            prob_array, emotion.confidence, motion_level
        )

        # 转换回字典
        fused_prob_dict = {
            label: float(prob) for label, prob in zip(emotion_labels, fused_probs)
        }

        # 标签决策
        stable_label, stable_score = track_state._label_policy.update(fused_prob_dict)  # type: ignore

        return EmotionResult(
            detection_id=track_id,  # 使用 track_id 而非原始 detection_id
            probabilities=fused_prob_dict,
            dominant_emotion=stable_label,
            confidence=stable_score,
            context_attention=emotion.context_attention,
        )

    def _cleanup_stale_tracks(self) -> None:
        """清理过期轨迹"""
        stale_ids = [
            track_id
            for track_id, track_state in self.tracks.items()
            if track_state.is_stale(max_age=self.track_buffer)
        ]

        for track_id in stale_ids:
            del self.tracks[track_id]

        if stale_ids:
            logger.debug(f"清理 {len(stale_ids)} 个过期轨迹")

    def reset(self) -> None:
        """重置跟踪器（切换视频源时调用）"""
        self.tracks.clear()
        self._next_track_id = 1
        self.frame_count = 0
        logger.info("跟踪器已重置")
