import os
import argparse
import torch
import torch.nn as nn
from torch.nn import functional as F
from .inception_resnet_v1 import InceptionResnetV1DDEN, InceptionResnetV1FPN
from .densenet import DenseNet, DenseNetIRDDEN
from .project_head import ProjectHead
from .weight_utils import kaiming_init, weights_frozen


class DDEN(nn.Module):
    def __init__(self, args: argparse.Namespace):
        super(DDEN, self).__init__()
        self.mode = args.mode
        self.dense_out_dim = args.dense_features + args.dense_layers * args.growth_rate
        self.idn = InceptionResnetV1DDEN(pretrained='vggface2')
        weights_frozen(self.idn)
        self.fan = InceptionResnetV1DDEN(pretrained='vggface2')
        self.dense = DenseNet(
            growth_rate=args.growth_rate,
            block_config=[args.dense_layers],
            num_classes=args.emb_dim,
            small_inputs=True,
            drop_rate=args.dropout,
            efficient=True,
            num_init_features=args.dense_features,
            args=args,
        )
        self.proj_head = ProjectHead(self.dense_out_dim, args)
        self.classifier = nn.Sequential(
            nn.ReLU(),
            nn.BatchNorm1d(self.proj_head.fc.out_features),
            nn.Linear(self.proj_head.fc.out_features, args.num_classes),
        )
        kaiming_init(self.proj_head)
        kaiming_init(self.fan.block8)
        kaiming_init(self.classifier)

    def forward(self, x):
        idf = self.idn(x)
        faf = self.fan(x)
        x = faf - idf
        x = self.dense(x)
        x = self.proj_head(x)
        if self.mode in ['pretrain', 'retrieval']:
            return F.normalize(x, p=2, dim=1)
        else:
            return self.classifier(x)


class SDDENFPN(DDEN):
    def __init__(self, args: argparse.Namespace):
        super().__init__(args)
        self.fan = InceptionResnetV1FPN(pretrained='vggface2')
        self.idn = None
        self.dense = DenseNetIRDDEN(
            growth_rate=args.growth_rate,
            block_config=[args.dense_layers],
            num_classes=args.emb_dim,
            small_inputs=True,
            drop_rate=args.dropout,
            efficient=True,
            num_init_features=args.dense_features,
            num_input_features=1792,
            args=args,
        )
        kaiming_init(self.fan.fix_depth1)
        kaiming_init(self.fan.fix_depth2)
        kaiming_init(self.fan.fix_depth3)
        kaiming_init(self.fan.fix_depth4)
        kaiming_init(self.fan.smooth1)
        kaiming_init(self.fan.smooth2)
        kaiming_init(self.fan.smooth3)
        kaiming_init(self.fan.smooth4)

    def forward(self, x):
        x = self.fan(x)
        x = self.dense(x)
        x = self.proj_head(x)
        if self.mode in ['pretrain', 'retrieval']:
            return F.normalize(x, p=2, dim=1)
        else:
            return self.classifier(x)
