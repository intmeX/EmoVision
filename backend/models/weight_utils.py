import torch
import torch.nn as nn


def kaiming_init(module):
    for m in module.modules():
        if isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.BatchNorm2d):
            nn.init.constant_(m.weight, 1)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, 0, 0.01)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)


def load_weights_init(model, model_path):
    ckpt = torch.load(model_path, weights_only=False)
    model_dict = model.state_dict()
    pretrained_dict = ckpt['state_dict']
    matched_dict = {
        k: v
        for k, v in pretrained_dict.items()
        if k in model_dict and model_dict[k].size() == v.size()
    }
    missing_keys = [k for k in model_dict if k not in matched_dict]
    skipped_keys = [k for k in pretrained_dict if k not in matched_dict]

    if not matched_dict:
        raise RuntimeError(f"权重文件与模型结构不匹配: {model_path}")

    model_dict.update(matched_dict)
    model.load_state_dict(model_dict, strict=False)
    if "emotic" in model_path:
        ckpt = torch.load(model_path, weights_only=False)
        model.load_state_dict(ckpt['state_dict'])

    return {
        'matched_keys': len(matched_dict),
        'model_keys': len(model_dict),
        'checkpoint_keys': len(pretrained_dict),
        'missing_keys': missing_keys,
        'skipped_keys': skipped_keys,
    }


def weights_frozen(model):
    for param in model.parameters():
        param.requires_grad = False


def weights_melted(model):
    for param in model.parameters():
        param.requires_grad = True
