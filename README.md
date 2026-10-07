# Indian Cyclone AI Weather Lab

Independent research prototype for **North Indian Ocean tropical cyclones** (Arabian Sea, Bay of Bengal, India and neighbouring coasts).

It is **not** Google DeepMind Weather Lab or WeatherNext. Those systems are cited only as public scientific/UX references. There are no proprietary weights or assets in this repo.

## What you can do now

- Browse a real **Indian Cyclone Dataset** built from NOAA IBTrACS v04r01 NI tracks, cropped to 0–30°N, 50–110°E, with IMD intensity classes.
- Replay historical storms on a **3D globe** centered on the Indian Ocean.
- Run **statistical** track/intensity/ensemble forecasts (persistence, CLIPER-style climatology, analog ensemble).
- See **measured** baseline track errors on held-out seasons — not invented accuracy.
- Inspect untrained ConvLSTM / spatiotemporal transformer **code** (weights are random; the UI will not pretend otherwise).

Live satellite/ERA5 ingestion is wired as a pipeline, not faked.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn numpy pandas pyyaml pytest
# optional neural stack: pip install -r requirements.txt

python scripts/validate_data.py          # or scripts/download_data.py if CSV missing
python scripts/create_cyclone_dataset.py
python scripts/evaluate.py               # real baseline metrics

cd frontend && npm install && npm run build && cd ..
PYTHONPATH=. uvicorn backend.api.main:app --host 0.0.0.0 --port 43127
```

Or `bash scripts/run_lab.sh`. Open http://127.0.0.1:43127. **Early detection** runs a satellite window and risk card on a historical fix; **Replay** steps through the IBTrACS track. Neither mode is an IMD warning product.

`cd frontend && npm run dev` still runs Vite on 43127 for local UI work; it proxies `/api` to 43128 if you start FastAPI there separately.

## Layout

See the tree in the repository: `frontend/`, `backend/`, `ml/`, `data/`, `scripts/`, `configs/`, `docs/`.

## Honesty

Neural forecasting models are **not trained yet**. Weather color fields are **parametric visualizations**. Formation probabilities are **climatological**. This is not an IMD warning system.

## Data credit

IBTrACS: NOAA NCEI, doi:10.25921/82ty-9e16.

## Docs

- [Datasets](docs/DATASETS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Research](docs/RESEARCH.md)
