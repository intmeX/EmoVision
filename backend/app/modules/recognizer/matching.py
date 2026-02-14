"""
人脸-人体匹配工具

提供检测结果的人脸-人体配对逻辑，作为单一真相源供检测器和识别器共同使用
"""

from typing import Optional

from ..detector.schemas import Detection, DetectionType


def filter_by_type(
    detections: list[Detection],
    det_type: DetectionType,
) -> list[Detection]:
    """
    按类型过滤检测结果

    Args:
        detections: 检测结果列表
        det_type: 目标类型

    Returns:
        过滤后的检测列表
    """
    return [d for d in detections if d.type == det_type]


def get_detection_by_id(
    detections: list[Detection],
    det_id: int,
) -> Optional[Detection]:
    """
    按 ID 查找检测结果

    Args:
        detections: 检测结果列表
        det_id: 目标 ID

    Returns:
        匹配的检测对象，未找到返回 None
    """
    for d in detections:
        if d.id == det_id:
            return d
    return None


def match_faces_to_persons(
    faces: list[Detection],
    persons: list[Detection],
    iou_threshold: float = 0.1,
) -> dict[int, int]:
    """
    贪心匹配人脸与人体检测结果

    匹配策略：
    1. 优先选择包含人脸中心点的人体框
    2. 在满足条件的候选中选择 IoU 最大的
    3. 若无包含关系，退而选择 IoU 超过阈值的最佳候选
    4. 每个人体最多匹配一个人脸（1:1 配对）

    Args:
        faces: 人脸检测列表
        persons: 人体检测列表
        iou_threshold: 最低 IoU 阈值（无包含关系时的回退条件）

    Returns:
        匹配映射 {face.id: person.id}
    """
    if not faces or not persons:
        return {}

    mapping: dict[int, int] = {}
    used_persons: set[int] = set()

    for face in faces:
        best_iou = 0.0
        best_person: Optional[Detection] = None

        for person in persons:
            if person.id in used_persons:
                continue

            iou = face.bbox.iou(person.bbox)

            # 检查人脸中心是否在人体框内
            face_cx, face_cy = face.bbox.center
            in_person = (
                person.bbox.x <= face_cx <= person.bbox.x2
                and person.bbox.y <= face_cy <= person.bbox.y2
            )

            if in_person and (best_person is None or iou > best_iou):
                best_iou = iou
                best_person = person
            elif not in_person and best_person is None and iou > iou_threshold:
                best_iou = iou
                best_person = person

        if best_person is not None:
            mapping[face.id] = best_person.id
            used_persons.add(best_person.id)

    return mapping


def apply_pairing(
    faces: list[Detection],
    persons: list[Detection],
    mapping: dict[int, int],
) -> None:
    """
    将匹配结果写入检测对象的 paired_id 字段

    Args:
        faces: 人脸检测列表
        persons: 人体检测列表
        mapping: 匹配映射 {face.id: person.id}
    """
    person_lookup = {p.id: p for p in persons}

    for face in faces:
        person_id = mapping.get(face.id)
        if person_id is not None:
            face.paired_id = person_id
            person = person_lookup.get(person_id)
            if person is not None:
                person.paired_id = face.id
