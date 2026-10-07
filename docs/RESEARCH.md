# Research notes — modern AI weather vs this lab

## Public concepts (inspired by)

Papers and open materials (GraphCast/WeatherNext Graph, GenCast/WeatherNext Gen, Pangu-Weather, FourCastNet, FuXi, NeuralGCM, and public WeatherNext 2/3 **product cards**) describe recurring ideas:

- Learn dynamics on grids or meshes from reanalysis.  
- Attention or message passing over space; roll out in time.  
- Ensembles (diffusion, functional generative nets, or perturbed ICs) for CRPS / cones.  
- Separate cyclone post-processing / specialized heads in some operational AI cyclone work.  
- Interactive labs: globe, time slider, overlay hierarchy, model comparison.

WeatherNext 3, as publicly described (2026 product documentation), is a **global** FGN mesh transformer with satellite mosaics, multi-resolution heads, and large ensembles. That is an **existence proof that AI weather is operationally interesting**, not a blueprint we can or should clone.

## What we copied: nothing proprietary

No Google code, weights, textures, or Weather Lab source. No “WeatherNext” branding in the product name.

## What we implemented independently

- NIO-only dataset construction from IBTrACS NI + IMD taxonomy.  
- CLIPER-like statistical steering (a classic statistical TC method, decades older than transformers).  
- Analog ensembles from same month/sub-basin.  
- Compact ConvLSTM and patch transformer **skeletons** sized for a student GPU.  
- A dark weather-lab UX: globe, layers, timeline, honesty banners.

## Architecture bake-off (qualitative)

| Approach | Fits prototype? | Verdict |
| --- | --- | --- |
| Persistence | Yes | Baseline |
| CLIPER / analog | Yes with tracks only | **Selected** |
| ConvLSTM on patches | Yes after ERA5 crops | Stage 2 |
| Compact ViT+time | Yes after ERA5 crops | Stage 3 |
| Spherical GNN (GraphCast-scale) | Needs global 0.25° cubes + serious GPU | Out of scope |
| Diffusion on 0.25° | Same | Out of scope |
| FGN / WeatherNext-class | Same + satellite mosaics | Out of scope |

## Scientific honesty

- Neural nets: **Model not trained yet.**  
- Weather overlays: parametric.  
- Formation probabilities: climatology.  
- Track errors shown in the UI come from `scripts/evaluate.py` or per-storm verification against remaining best track — not invented skill scores.  
- Not an IMD warning product.
