import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def log_experiment(record: dict, path: Path | None = None) -> Path:
    path = path or ROOT / "data" / "processed" / "experiments.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")
    return path
