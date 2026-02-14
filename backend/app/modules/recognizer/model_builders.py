"""
模型构建工具

提供干净的模型构建函数，避免训练时工具（torchsummary等）的副作用
"""

import argparse

from models.clip import ClipCaptain
from models.dden import SDDENFPN
from models.emotic import CaerMultiStream, SEEmoticQuadrupleStream
from models.fer_cnn import load_trained_sfer

from ...utils.logger import get_logger

import torch.nn as nn
import torchvision.models as models

logger = get_logger(__name__)


# ============================================================
# SDDENFPN 默认参数
# ============================================================

SDDENFPN_DEFAULT_ARGS = argparse.Namespace(
    mode="inference",
    growth_rate=64,
    dense_layers=5,
    dense_features=512,
    emb_dim=128,
    dropout=0,
    num_classes=7,
    proj_head=3,
)


def build_sddenfpn(
    args: argparse.Namespace = SDDENFPN_DEFAULT_ARGS,
) -> SDDENFPN:
    """
    构建 SDDENFPN 模型

    Args:
        args: 模型参数（使用默认值即可）

    Returns:
        SDDENFPN 模型实例
    """
    model = SDDENFPN(args)
    logger.info("SDDENFPN 模型构建完成")
    return model


# ============================================================
# SEEmoticQuadrupleStream 构建
# ============================================================

EMOTIC_DEFAULT_ARGS = argparse.Namespace(
    context_model_frozen=True,
    body_model_frozen=True,
    face_model_frozen=True,
    fuse_r=4,
    fuse_L=64,
    fuse_2_layer=False,
)


def _build_backbone(
    model_name: str,
    frozen: bool = True,
) -> tuple[int, nn.Module]:
    """
    构建 torchvision 骨干网络（去掉最后的分类层）

    Args:
        model_name: torchvision 模型名称（如 'resnet18'）
        frozen: 是否冻结参数

    Returns:
        (特征维度, 模型)
    """
    backbone = models.__dict__[model_name](weights="DEFAULT")
    num_features = list(backbone.children())[-1].in_features
    backbone = nn.Sequential(*(list(backbone.children())[:-1]))

    if frozen:
        for param in backbone.parameters():
            param.requires_grad = False

    return num_features, backbone


def _build_face_model(
    face_model: str = "sfer",
    frozen: bool = True,
) -> tuple[int, nn.Module]:
    """
    构建人脸特征提取模型

    Args:
        face_model: 模型名称，'sfer' 使用预训练 SFER CNN
        frozen: 是否冻结参数

    Returns:
        (特征维度, 模型)
    """
    if face_model == "sfer":
        model = load_trained_sfer()
        num_features = list(model.children())[-1].out_features
    else:
        model = models.__dict__[face_model](weights="DEFAULT")
        num_features = list(model.children())[-1].in_features
        model = nn.Sequential(*(list(model.children())[:-1]))

    if frozen:
        for param in model.parameters():
            param.requires_grad = False

    return num_features, model


def _build_caption_model() -> tuple[int, nn.Module]:
    """
    构建 CLIP 图像编码器（caption 流）

    Returns:
        (特征维度, 模型)
    """
    model = ClipCaptain()
    for param in model.parameters():
        param.requires_grad = False
    return 512, model


def build_emotic_quadruple_stream(
    context_model: str = "resnet18",
    body_model: str = "resnet18",
    face_model: str = "sfer",
    fuse_r: int = 4,
    fuse_l: int = 64,
    fuse_2_layer: bool = False,
) -> SEEmoticQuadrupleStream:
    """
    构建 SEEmoticQuadrupleStream 模型

    Args:
        context_model: 上下文骨干网络名称
        body_model: 身体骨干网络名称
        face_model: 人脸模型名称（'sfer' 或 torchvision 模型名）
        fuse_r: SE 融合降维比率
        fuse_l: SESeg1D 分段长度
        fuse_2_layer: 是否使用二级融合

    Returns:
        SEEmoticQuadrupleStream 模型实例
    """
    num_ctx, model_ctx = _build_backbone(context_model, frozen=True)
    num_body, model_body = _build_backbone(body_model, frozen=True)
    num_face, model_face = _build_face_model(face_model, frozen=True)
    num_caption, model_caption = _build_caption_model()

    model = SEEmoticQuadrupleStream(
        num_context_features=num_ctx,
        num_body_features=num_body,
        num_face_features=num_face,
        num_caption_feature=num_caption,
        model_context=model_ctx,
        model_body=model_body,
        model_face=model_face,
        model_caption=model_caption,
        r=fuse_r,
        L=fuse_l,
        fuse_2_layer=fuse_2_layer,
    )
    logger.info("SEEmoticQuadrupleStream 模型构建完成")
    return model


# ============================================================
# CaerMultiStream 构建
# ============================================================

CAER_DEFAULT_ARGS = argparse.Namespace(
    context_model_frozen=True,
    face_model_frozen=True,
    fuse_model="se_fusion",
    fuse_L=64,
    fuse_r=4,
)


def build_caer_multistream(
    context_model: str = "resnet18",
    face_model: str = "sfer",
    fusion: str = "se_fusion",
    fuse_l: int = 64,
    fuse_r: int = 4,
) -> CaerMultiStream:
    """
    构建 CaerMultiStream 模型

    Args:
        context_model: 上下文骨干网络名称
        face_model: 人脸模型名称
        fusion: 融合方式（'se_fusion' 或其他）
        fuse_l: SESeg1D 分段长度
        fuse_r: SE 融合降维比率

    Returns:
        CaerMultiStream 模型实例
    """
    num_ctx, model_ctx = _build_backbone(context_model, frozen=True)
    num_face, model_face = _build_face_model(face_model, frozen=True)
    num_caption, model_caption = _build_caption_model()

    model = CaerMultiStream(
        num_features=[num_ctx, num_face, num_caption],
        models=[model_ctx, model_face, model_caption],
        fusion=fusion,
        fuse_l=fuse_l,
        fuse_r=fuse_r,
    )
    logger.info("CaerMultiStream 模型构建完成")
    return model
