"""Compact ConvLSTM for storm-centered patch forecasting.

Default weights are random. Do not report accuracy until trained.
"""

from __future__ import annotations

import torch
from torch import nn


class ConvLSTMCell(nn.Module):
    def __init__(self, in_ch: int, hid: int, k: int = 3):
        super().__init__()
        self.hid = hid
        self.conv = nn.Conv2d(in_ch + hid, 4 * hid, k, padding=k // 2)

    def forward(self, x, h, c):
        gates = self.conv(torch.cat([x, h], 1))
        i, f, g, o = gates.chunk(4, 1)
        i, f, o = torch.sigmoid(i), torch.sigmoid(f), torch.sigmoid(o)
        g = torch.tanh(g)
        c = f * c + i * g
        h = o * torch.tanh(c)
        return h, c


class ConvLSTMForecast(nn.Module):
    def __init__(self, channels: int = 8, hidden: int = 32, depth: int = 2):
        super().__init__()
        self.hidden = hidden
        self.cells = nn.ModuleList(
            [ConvLSTMCell(channels if i == 0 else hidden, hidden) for i in range(depth)]
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(hidden, 64),
            nn.ReLU(),
            nn.Linear(64, 6),  # dlat, dlon, dwind, dpres, p_cyclone, p_ri
        )

    def forward(self, x):
        # x: B, T, C, H, W
        b, t, c, h, w = x.shape
        states = []
        for cell in self.cells:
            states.append(
                (
                    torch.zeros(b, self.hidden, h, w, device=x.device),
                    torch.zeros(b, self.hidden, h, w, device=x.device),
                )
            )
        for ti in range(t):
            inp = x[:, ti]
            new_states = []
            for i, cell in enumerate(self.cells):
                ht, ct = cell(inp, *states[i])
                new_states.append((ht, ct))
                inp = ht
            states = new_states
        return self.head(states[-1][0])


def param_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())
