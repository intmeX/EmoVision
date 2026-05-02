import logging

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class _DummyCaptain(nn.Module):
    """当 CLIP 不可用时的零向量占位模型（输出 512 维零向量）。"""

    def __init__(self):
        super().__init__()

    def forward(self, x):
        batch = x.shape[0]
        return torch.zeros(batch, 512, device=x.device)


class ClipCaptain(nn.Module):
    def __init__(self, clip_name='openai/clip-vit-base-patch32'):
        super(ClipCaptain, self).__init__()
        self.model_name = clip_name
        self._dummy = False
        try:
            from transformers import CLIPModel
            self.model = CLIPModel.from_pretrained(
                self.model_name,
                local_files_only=True,  # 只使用本地缓存，不联网
            )
            logger.info(f'ClipCaptain 加载成功: {clip_name}')
        except Exception as e:
            logger.warning(
                f'ClipCaptain 无法加载 CLIP 模型 ({e})，降级为零向量占位模型。'
                f' 上下文注意力中 scene_semantics 分量将为零。'
            )
            self.model = _DummyCaptain()
            self._dummy = True

    def forward(self, x):
        if self._dummy:
            return self.model(x)
        x = self.model.get_image_features(x, output_hidden_states=True)  # type: ignore[arg-type]
        return x


if __name__ == '__main__':
    model_name = "openai/clip-vit-base-patch32"
    model = CLIPModel.from_pretrained(model_name)
    processor = CLIPProcessor.from_pretrained(model_name)

    image = torch.randint(low=-2, high=2, size=(15, 3, 224, 224))

    # image = processor(text=None, images=image, return_tensors="pt", padding=True)

    with torch.no_grad():
        image_features = model.get_image_features(image)
    print(image_features.shape)
