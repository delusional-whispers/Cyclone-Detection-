"""Metrics for cyclone detection, track, intensity, and ensembles."""

from __future__ import annotations

import math

import numpy as np

from backend.models.geo import haversine_km


def binary_scores(y_true, y_prob, thr=0.5):
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob)
    y_hat = (y_prob >= thr).astype(int)
    tp = int(((y_hat == 1) & (y_true == 1)).sum())
    fp = int(((y_hat == 1) & (y_true == 0)).sum())
    fn = int(((y_hat == 0) & (y_true == 1)).sum())
    tn = int(((y_hat == 0) & (y_true == 0)).sum())
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    acc = (tp + tn) / max(1, tp + fp + fn + tn)
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def roc_auc(y_true, y_prob):
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    if y_true.min() == y_true.max():
        return float("nan")
    order = np.argsort(-y_prob)
    y = y_true[order]
    tps = np.cumsum(y)
    fps = np.cumsum(1 - y)
    tps = np.r_[0, tps]
    fps = np.r_[0, fps]
    tpr = tps / max(1, tps[-1])
    fpr = fps / max(1, fps[-1])
    trapz = getattr(np, "trapezoid", None) or np.trapz
    return float(trapz(tpr, fpr))


def mae_rmse_r2(y, yhat):
    y = np.asarray(y, dtype=float)
    yhat = np.asarray(yhat, dtype=float)
    mask = np.isfinite(y) & np.isfinite(yhat)
    y, yhat = y[mask], yhat[mask]
    if len(y) == 0:
        return {"mae": None, "rmse": None, "r2": None, "n": 0}
    err = yhat - y
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else None
    return {"mae": mae, "rmse": rmse, "r2": r2, "n": int(len(y))}


def track_errors_km(obs, pred):
    """obs/pred: list of (lat, lon) aligned."""
    return [haversine_km(a[0], a[1], b[0], b[1]) for a, b in zip(obs, pred)]


def crps_ensemble(obs: float, members: list[float]) -> float:
    x = np.sort(np.asarray(members, dtype=float))
    n = len(x)
    # Fair CRPS for a sample (Gneiting)
    term1 = np.mean(np.abs(x - obs))
    term2 = np.mean(np.abs(x[:, None] - x[None, :]))
    return float(term1 - 0.5 * term2)


def interval_coverage(obs, lo, hi):
    obs = np.asarray(obs)
    lo = np.asarray(lo)
    hi = np.asarray(hi)
    return float(np.mean((obs >= lo) & (obs <= hi)))
