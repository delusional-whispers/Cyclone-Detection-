# Implementation plan

Reconnaissance is complete. Incremental delivery:

| Phase | Status in this repo |
| --- | --- |
| 1 Repository | Done |
| 2 Dataset research | Done — `docs/DATASETS.md` |
| 3 Indian cyclone pipeline | Done for IBTrACS NI crop |
| 4 Baseline detection | Best-track + IMD classes (neural detector **not trained**) |
| 5 Train baseline | Statistical climatology from train split |
| 6 Evaluate baseline | `scripts/evaluate.py` on held-out storms |
| 7 ST-transformer | Architecture code; **not trained** |
| 8 Track prediction | Persistence / analog ensemble |
| 9 Intensity | Persistence + climatological ΔV |
| 10 Probabilistic | 21-member analog/perturbation ensemble |
| 11 Backend API | FastAPI |
| 12 3D globe | Three.js, India-centered |
| 13 Weather layers | Parametric fields, labeled |
| 14 Cyclone viz | Vortex particles, eye, tracks, cone |
| 15 Timeline | Play / pause / speed / scrub |
| 16 Model comparison | Persistence vs analog; neural disabled |
| 17 Historical replay | Default mode |
| 18 Live architecture | Endpoints ready; `live_data: false` |
| 19 Optimization | Mixed-precision flags only |
| 20 Documentation | `docs/` + README |

## Next (when you have CDS/MOSDAC access)

1. Crop ERA5 to cyclone windows only.  
2. Align INSAT IR.  
3. `generate_training_samples.py` → npz patches.  
4. Train ConvLSTM, then transformer.  
5. Compare generic (all NI) vs Arabian Sea / Bay of Bengal fine-tunes.  
6. Replace parametric globe layers with real fields.

Do **not** start those downloads from this environment without a storage budget.
