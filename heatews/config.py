from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load(path=None):
    path = Path(path) if path else ROOT / "config.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    for key in ("p90", "p95"):
        cfg["sop_appendix1"][key] = {int(k): float(v) for k, v in cfg["sop_appendix1"][key].items()}
    return cfg
