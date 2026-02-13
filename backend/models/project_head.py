import argparse
import torch.nn as nn


class ProjectHead(nn.Module):
    def __init__(self, init_feature_dim, args: argparse.Namespace):
        super(ProjectHead, self).__init__()
        self.init_feature_dim = init_feature_dim
        self.num_proj = args.proj_head
        self.emb_dim = args.emb_dim
        self.mode = args.mode
        channels_in = self.init_feature_dim
        if 1 != self.num_proj:
            dim, relu = channels_in, True
        else:
            dim, relu = self.emb_dim, False
        self.fc = nn.Linear(channels_in, dim, bias=relu)
        layers = []
        for i in range(1, self.num_proj):
            layers.append(nn.ReLU())
            bn = nn.BatchNorm1d(dim, eps=1e-5, affine=True)
            layers.append(bn)
            if i != self.num_proj - 1:
                dim, relu = channels_in, True
            else:
                dim, relu = self.emb_dim, False
            layers.append(nn.Linear(channels_in, dim, bias=relu))
        self.pretrain_proj = nn.Sequential(*layers)

    def forward(self, x):
        x = x.view(x.shape[0], -1)
        x = self.fc(x)
        if self.mode in ['pretrain', 'retrieval']:
            return self.pretrain_proj(x)
        else:
            return x
