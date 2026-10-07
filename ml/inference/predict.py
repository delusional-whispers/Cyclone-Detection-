"""Random-weight neural inference used only to prove the module loads.

Never mix this output with statistical baseline scores.
"""

from __future__ import annotations

import torch

from ml.architectures import ConvLSTMForecast, SpatiotemporalTransformer


def untrained_forward(arch: str = "convlstm"):
    x = torch.zeros(1, 4, 8, 64, 64)
    if arch == "transformer":
        model = SpatiotemporalTransformer()
        x = torch.zeros(1, 8, 8, 64, 64)
    else:
        model = ConvLSTMForecast()
    model.eval()
    with torch.no_grad():
        y = model(x)
    return {
        "arch": arch,
        "trained": False,
        "output": y.squeeze(0).tolist(),
        "disclaimer": "Model not trained yet. These numbers are meaningless.",
    }
