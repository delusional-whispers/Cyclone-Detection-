"""Patch spatiotemporal transformer for cyclone track/intensity heads.

Inspired by general ViT + temporal attention ideas used in modern data-driven
weather models. This is not GraphCast, Pangu-Weather, FourCastNet, or WeatherNext.
Weights are untrained unless a checkpoint is loaded.
"""

from __future__ import annotations

import torch
from torch import nn


class SpatiotemporalTransformer(nn.Module):
    def __init__(
        self,
        channels: int = 8,
        patch: int = 8,
        dim: int = 96,
        depth: int = 4,
        heads: int = 4,
        grid: int = 64,
        frames: int = 8,
    ):
        super().__init__()
        assert grid % patch == 0
        nspat = (grid // patch) ** 2
        self.patch = nn.Conv2d(channels, dim, patch, stride=patch)
        self.pos = nn.Parameter(torch.randn(1, frames * nspat, dim) * 0.02)
        layer = nn.TransformerEncoderLayer(d_model=dim, nhead=heads, batch_first=True, dim_feedforward=dim * 4)
        self.enc = nn.TransformerEncoder(layer, num_layers=depth)
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, 6)

    def forward(self, x):
        # B, T, C, H, W
        b, t, c, h, w = x.shape
        tokens = []
        for ti in range(t):
            p = self.patch(x[:, ti])  # B, dim, gh, gw
            tokens.append(p.flatten(2).transpose(1, 2))
        tok = torch.cat(tokens, 1)
        tok = tok + self.pos[:, : tok.size(1)]
        z = self.norm(self.enc(tok))
        return self.head(z.mean(1))
