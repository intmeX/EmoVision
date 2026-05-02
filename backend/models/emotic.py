import torch
import torch.nn as nn
import logging
import torchvision.models as models
from torchsummary import summary
from .fer_cnn import load_trained_sfer
from .clip import ClipCaptain


class SESeg1D(nn.Module):

    def __init__(
            self,
            features,
            r,
            L=64,
    ):
        super(SESeg1D, self).__init__()
        self.L = L
        self.num_channel = int(features / L)
        self.d = int(self.num_channel / r)
        self.features = features
        self.gap = nn.AdaptiveAvgPool1d(1)
        self.fc1 = nn.Sequential(
            nn.Linear(self.num_channel, self.d),
            nn.ReLU(),
        )
        self.fc2 = nn.Sequential(
            nn.Linear(self.d, self.num_channel),
            nn.Softmax(dim=1),
        )

    def forward(self, x):
        x = x.view(-1, self.num_channel, self.L)
        fea_s = self.gap(x).squeeze(-1)
        fea_z = self.fc1(fea_s)
        attn = self.fc2(fea_z).view(-1, self.num_channel, 1)
        x = x * attn.expand_as(x)
        return x.view(-1, self.features), attn.squeeze(-1)


class SEEmoticQuadrupleStream(nn.Module):
    ''' Quad Stream Emotic Model'''

    def __init__(self, num_context_features, num_body_features, num_face_features, num_caption_feature, model_context,
                 model_body, model_face, model_caption, r, L, fuse_2_layer=False):
        super(SEEmoticQuadrupleStream, self).__init__()
        self.num_context_features = num_context_features
        self.num_body_features = num_body_features
        self.num_face_features = num_face_features
        self.num_caption_features = num_caption_feature
        self.model_context = model_context
        self.model_body = model_body
        self.model_face = model_face
        self.model_caption = model_caption
        self.context_fuse = SESeg1D(self.num_context_features + self.num_caption_features, r=r, L=L)
        self.body_fuse = SESeg1D(self.num_body_features + self.num_face_features, r=r, L=L)
        self.fuse_2_layer = fuse_2_layer
        self.fuse_len = self.num_context_features + self.num_body_features + self.num_face_features + self.num_caption_features
        if not self.fuse_2_layer:
            self.fuse_2 = nn.Sequential()
        else:
            self.fuse_2 = SESeg1D(self.fuse_len, r=r, L=L)
        self.fuse = nn.Sequential(
            nn.Linear(self.fuse_len, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(p=0.5),
        )
        self.fc_cat = nn.Linear(256, 26)
        self.fc_cont = nn.Linear(256, 3)
        self.brief = 'SEQuadrupleStreamNet'

    @staticmethod
    def _mean_attention(attn, start, length):
        return attn[:, start:start + length].mean(dim=1)

    @staticmethod
    def _safe_distribute(score_a, score_b):
        total = score_a + score_b
        default = torch.full_like(total, 0.5)
        weight_a = torch.where(total > 0, score_a / total, default)
        weight_b = torch.where(total > 0, score_b / total, default)
        return weight_a, weight_b

    @staticmethod
    def _normalize_attention(scores):
        score_iter = iter(scores.values())
        total = next(score_iter)
        for score in score_iter:
            total = total + score

        normalized_scores = {}
        default_value = 1.0 / len(scores)
        for key, score in scores.items():
            normalized_scores[key] = torch.where(
                total > 0,
                score / total,
                torch.full_like(score, default_value),
            )
        return normalized_scores

    def forward(self, x_context, x_body, x_face):
        context_features = self.model_context(x_context).view(-1, self.num_context_features)
        body_features = self.model_body(x_body).view(-1, self.num_body_features)
        face_features = self.model_face(x_face).view(-1, self.num_face_features)
        caption_features = self.model_caption(x_context).view(-1, self.num_caption_features)

        context_attention = None

        context_fuse_feature = torch.cat([context_features, caption_features], 1)
        context_fuse_feature, attn_ctx = self.context_fuse(context_fuse_feature)

        body_fuse_feature = torch.cat([body_features, face_features], 1)
        body_fuse_feature, attn_body = self.body_fuse(body_fuse_feature)

        fuse_features = torch.cat((context_fuse_feature, body_fuse_feature), 1)

        bg_channels = self.num_context_features // self.context_fuse.L
        caption_channels = self.num_caption_features // self.context_fuse.L
        body_channels = self.num_body_features // self.body_fuse.L
        face_channels = self.num_face_features // self.body_fuse.L

        score_bg_l1 = self._mean_attention(attn_ctx, 0, bg_channels)
        score_caption_l1 = self._mean_attention(attn_ctx, bg_channels, caption_channels)
        score_body_l1 = self._mean_attention(attn_body, 0, body_channels)
        score_face_l1 = self._mean_attention(attn_body, body_channels, face_channels)

        if isinstance(self.fuse_2, SESeg1D):
            fuse_features, attn_fuse_2 = self.fuse_2(fuse_features)
            ctx_blend_channels = (self.num_context_features + self.num_caption_features) // self.fuse_2.L
            body_blend_channels = (self.num_body_features + self.num_face_features) // self.fuse_2.L

            # score_bg_l2 = self._mean_attention(attn_fuse_2, 0, bg_channels)
            # score_caption_l2 = self._mean_attention(attn_fuse_2, bg_channels, caption_channels)
            # score_body_l2 = self._mean_attention(attn_fuse_2, 0, body_channels)
            # score_face_l2 = self._mean_attention(attn_fuse_2, body_channels, face_channels)

            score_ctx_blend_l2 = self._mean_attention(attn_fuse_2, 0, ctx_blend_channels)
            score_body_blend_l2 = self._mean_attention(
                attn_fuse_2, ctx_blend_channels, body_blend_channels
            )

            bg_weight, caption_weight = self._safe_distribute(
                score_bg_l1, score_caption_l1
            )
            body_weight, face_weight = self._safe_distribute(
                score_body_l1, score_face_l1
            )

            context_attention = self._normalize_attention(
                {
                    '背景': score_ctx_blend_l2 * bg_weight,
                    '身体': score_body_blend_l2 * body_weight,
                    '人脸': score_body_blend_l2 * face_weight,
                    '场景语义': score_ctx_blend_l2 * caption_weight,
                }
            )
        else:
            fuse_features = self.fuse_2(fuse_features)
            context_attention = self._normalize_attention(
                {
                    '背景': score_bg_l1,
                    '身体': score_body_l1,
                    '人脸': score_face_l1,
                    '场景语义': score_caption_l1,
                }
            )

        fuse_out = self.fuse(fuse_features)
        cat_out = self.fc_cat(fuse_out)
        return cat_out, context_attention


class CaerMultiStream(nn.Module):
    ''' Multi-Stream CAER Model'''

    def __init__(self, num_features, models, fusion, fuse_l, fuse_r):
        super(CaerMultiStream, self).__init__()
        self.num_features = num_features
        self.models = nn.ModuleList(models)
        self.fuse_dim = 0
        for i in range(len(num_features)):
            self.fuse_dim += self.num_features[i]
        self.first_fuse_dim = self.num_features[0] + self.num_features[1]
        if fusion == 'se_fusion':
            self.first_attn = SESeg1D(self.first_fuse_dim, fuse_r, fuse_l)
            self.attn = SESeg1D(self.fuse_dim, fuse_r, fuse_l)
        else:
            self.first_attn = nn.Sequential()
            self.attn = nn.Sequential()
        self.fuse = nn.Sequential(
            nn.Linear(self.fuse_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(p=0.5),
        )
        self.fc_cat = nn.Linear(256, 7)
        self.brief = 'CaerMultiStream'

    @staticmethod
    def _mean_attention(attn, start, length):
        return attn[:, start:start + length].mean(dim=1)

    @staticmethod
    def _normalize_attention(scores):
        score_iter = iter(scores.values())
        total = next(score_iter)
        for score in score_iter:
            total = total + score

        normalized_scores = {}
        default_value = 1.0 / len(scores)
        for key, score in scores.items():
            normalized_scores[key] = torch.where(
                total > 0,
                score / total,
                torch.full_like(score, default_value),
            )
        return normalized_scores

    def forward(self, x_context, x_face):
        xs = [x_context, x_face, x_context]
        features = []
        for i in range(len(xs)):
            features.append(self.models[i](xs[i]).view(-1, self.num_features[i]))

        if not isinstance(self.first_attn, SESeg1D) or not isinstance(self.attn, SESeg1D):
            features_low = self.first_attn(torch.cat(features[: 2], 1))
            features = self.attn(torch.cat([features[2], features_low], 1))
            features = self.fuse(features)
            cat_out = self.fc_cat(features)
            return cat_out, None

        features_low, attn_first = self.first_attn(torch.cat(features[: 2], 1))
        features, attn_second = self.attn(torch.cat([features[2], features_low], 1))

        context_channels = self.num_features[0] // self.first_attn.L
        face_channels = self.num_features[1] // self.first_attn.L
        caption_channels = self.num_features[2] // self.attn.L
        blend_channels = (self.num_features[0] + self.num_features[1]) // self.attn.L

        score_ctx_l1 = self._mean_attention(attn_first, 0, context_channels)
        score_face_l1 = self._mean_attention(attn_first, context_channels, face_channels)
        score_caption_l2 = self._mean_attention(attn_second, 0, caption_channels)
        score_blend_l2 = self._mean_attention(attn_second, caption_channels, blend_channels)

        blend_total = score_ctx_l1 + score_face_l1
        default_weight = torch.full_like(blend_total, 0.5)
        weight_ctx = torch.where(blend_total > 0, score_ctx_l1 / blend_total, default_weight)
        weight_face = torch.where(blend_total > 0, score_face_l1 / blend_total, default_weight)

        context_attention = self._normalize_attention(
            {
                '背景': score_blend_l2 * weight_ctx,
                '人脸': score_blend_l2 * weight_face,
                '场景语义': score_caption_l2,
            }
        )

        features = self.fuse(features)
        cat_out = self.fc_cat(features)
        return cat_out, context_attention


def build_context_model(context_model, args):
    logger = logging.getLogger('Experiment')
    model_context = models.__dict__[context_model](weights='DEFAULT')
    num_context_features = list(model_context.children())[-1].in_features
    model_context = nn.Sequential(*(list(model_context.children())[:-1]))
    logger.info('completed preparing context model: {}'.format(context_model))
    if args.context_model_frozen:
        for param in model_context.parameters():
            param.requires_grad = False
        logger.info('context model frozen')
    logger.info(summary(model_context, (3, 224, 224), device="cpu"))
    logger.info('num of features: {}'.format(num_context_features))
    return num_context_features, model_context


def build_body_model(body_model, args):
    logger = logging.getLogger('Experiment')
    model_body = models.__dict__[body_model](weights='DEFAULT')
    num_body_features = list(model_body.children())[-1].in_features
    model_body = nn.Sequential(*(list(model_body.children())[:-1]))
    logger.info('completed preparing body model: {}'.format(body_model))
    if args.body_model_frozen:
        for param in model_body.parameters():
            param.requires_grad = False
        logger.info('body model frozen')
    logger.info(summary(model_body, (3, 128, 128), device="cpu"))
    logger.info('num of features: {}'.format(num_body_features))
    return num_body_features, model_body


def build_face_model(face_model, args):
    logger = logging.getLogger('Experiment')
    if face_model == 'sfer':
        model_face = load_trained_sfer()
        num_face_features = list(model_face.children())[-1].out_features
        '''
        elif face_model == 'ResEmoteNet':
            if args.face_weight == 'initial':
                model_face = ResEmoteNet()
                model_face.weight_init()
            else:
                model_face = load_res_emote()
            num_face_features = 256
        '''
    else:
        model_face = models.__dict__[face_model](weights='DEFAULT')
        num_face_features = list(model_face.children())[-1].in_features
        model_face = nn.Sequential(*(list(model_face.children())[:-1]))
    logger.info('completed preparing face model: {}'.format(face_model))
    if args.face_model_frozen:
        for param in model_face.parameters():
            param.requires_grad = False
        logger.info('face model frozen')
    logger.info(summary(model_face, (3, 48, 48), device="cpu"))
    logger.info('num of features: {}'.format(num_face_features))
    return num_face_features, model_face


def build_caption_model(caption_model, args):
    logger = logging.getLogger('Experiment')
    model_caption = ClipCaptain()
    logger.info('completed preparing caption model: {}'.format(caption_model))
    for param in model_caption.parameters():
        param.requires_grad = False
    logger.info('caption model frozen')
    num_caption_feature = 512
    # logger.info(summary(model_caption, (3, 224, 224), device="cpu"))
    logger.info('num of features: {}'.format(num_caption_feature))
    return num_caption_feature, model_caption


def prep_models_quadruple_stream(context_model, body_model, face_model, caption_model, args):
    # create the network architecture
    num_context_features, model_context = build_context_model(context_model, args)
    num_body_features, model_body = build_body_model(body_model, args)
    num_face_features, model_face = build_face_model(face_model, args)
    num_caption_features, model_caption = build_caption_model(caption_model, args)
    emotic_model = SEEmoticQuadrupleStream(num_context_features, num_body_features, num_face_features,
                                             num_caption_features, model_context, model_body, model_face, model_caption,
                                               args.fuse_r, args.fuse_L, args.fuse_2_layer)
    return emotic_model


def prep_models_caer_multistream(context_model, face_model, caption_model, args):
    # create the network architecture
    num_context_features, model_context = build_context_model(context_model, args)
    num_face_features, model_face = build_face_model(face_model, args)
    num_caption_features, model_caption = build_caption_model(caption_model, args)
    caer_model = CaerMultiStream(
        [num_context_features, num_face_features, num_caption_features],
        [model_context, model_face, model_caption],
        args.fuse_model,
        args.fuse_L,
        args.fuse_r,
    )
    return caer_model


if __name__ == '__main__':
    pass
