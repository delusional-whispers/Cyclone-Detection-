import torch
from torch import nn


class HuberTrackLoss(nn.Module):
    def forward(self, pred, target):
        return nn.functional.huber_loss(pred, target)
