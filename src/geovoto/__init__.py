import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((ROOT / "config.toml").read_text())
RAW = ROOT / CONFIG["raw_dir"]
PROCESSED = ROOT / CONFIG["processed_dir"]
