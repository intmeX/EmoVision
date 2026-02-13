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
    pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict and model_dict[k].size() == v.size()}
    model_dict.update(pretrained_dict)
    model.load_state_dict(model_dict, strict=False)
    # model.load_state_dict(ckpt['state_dict'], strict=False)


def weights_frozen(model):
    for param in model.parameters():
        param.requires_grad = False


def weights_melted(model):
    for param in model.parameters():
        param.requires_grad = True
