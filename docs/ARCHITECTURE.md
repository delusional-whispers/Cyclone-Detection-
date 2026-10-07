# Architecture — Indian Cyclone AI Weather Lab

Independent research prototype. **Inspired by** public ideas from data-driven weather (graph/transformer sequence models, ensembles, interactive labs). **Not** Google WeatherNext, Weather Lab, GraphCast, GenCast, Pangu-Weather, or FourCastNet. No proprietary weights, assets, or code are used.

## Three layers

```
┌──────────────────────────────────────────┐
│ C. 3D Weather Lab (Vite + React + Three.js) │
└─────────────────┬────────────────────────┘
                  │ REST /api
┌─────────────────▼────────────────────────┐
│ B. Atmospheric / cyclone data engine     │
│    IBTrACS pipeline, climatology, grids  │
└─────────────────┬────────────────────────┘
                  │
┌─────────────────▼────────────────────────┐
│ A. Forecasting engine                    │
│    Statistical baselines (trained)       │
│    ConvLSTM + ST-Transformer (untrained) │
└──────────────────────────────────────────┘
```

## A. AI / forecast engine

**Selected for this prototype:** CLIPER-inspired **persistence + NIO motion climatology + analog ensemble**.

Why not a 100M-parameter mesh transformer on day one:

| Criterion | Finding |
| --- | --- |
| Dataset available now | Point tracks (~28 MB), not ERA5 cubes |
| Spatial resolution | Track points, not 0.25° fields |
| GPU | No dedicated training GPU assumed |
| Honesty | A huge untrained net would only decorate the UI |

**Stage 1 (implemented, evaluated):** persistence; climatology steering; analog ensemble; Holland wind kernel for viz.  
**Stage 2 (code only):** `ml/architectures/convlstm.py`.  
**Stage 3 (code only):** `ml/architectures/transformer.py` + ensemble CRPS metrics.  
**Stage 4:** Indian specialization is the **dataset and climatology**, not a fake fine-tune.

Outputs: detection snapshot from best track + IMD thresholds, track leads 6–120 h, intensity, RI/RW ensemble fractions, landfall gazetteer, formation **climatology** (not a trained genesis CNN).

## B. Data engine

`scripts/download_data.py` → `validate_data.py` → `create_cyclone_dataset.py` → climatology JSON.  
ERA5/INSAT downloaders are **recipes**, not silent multi-GB pulls.

## C. Weather Lab UI

Dark scientific layout: archive | 3D globe (India-centered) | forecast panel | timeline. Layers for weather and tracks. Historical replay only — **live mode is an interface, not a fake nowcast**.

Globe: Three.js (better custom particles/vortex than Cesium for this prototype).

## APIs

| Method | Path |
| --- | --- |
| GET | `/api/cyclones` |
| GET | `/api/cyclones/{id}` |
| GET | `/api/cyclones/{id}/track` |
| GET | `/api/cyclones/{id}/forecast` |
| POST | `/api/detect` |
| POST | `/api/predict` |
| GET | `/api/weather` |
| GET | `/api/satellite` |
| GET | `/api/models` |
| GET | `/api/evaluation` |

## Compute (realistic)

| Item | Estimate |
| --- | --- |
| IBTrACS NI | 28 MB |
| Processed catalog | on the order of 1–10 MB JSON |
| Statistical inference | CPU, milliseconds per storm |
| ConvLSTM 64², 8 ch, hidden 32 | ~2M params, ~1–2 GB VRAM to train |
| Compact ST-transformer | ~4M params |
| Full ERA5 NIO 1979–2023, 6-hourly, 8 vars, few levels | 10² GB scale — **do not download blindly** |
| WeatherNext-class global 0.25° / 0.05° | far beyond this prototype |

Mixed precision, grad accumulation, and checkpointing flags live in `configs/training.yaml` for when patches exist.

## Experiment log

JSONL via `ml/experiments.py` (no W&B key required). `scripts/evaluate.py` writes `data/processed/baseline_evaluation.json` with **measured** baseline errors only.
