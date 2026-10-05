import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((ROOT / "config.toml").read_text())
RAW = ROOT / CONFIG["raw_dir"]
PROCESSED = ROOT / CONFIG["processed_dir"]


def http_get(url: str, timeout: int = 60, tentativas: int = 4) -> bytes:
    """GET com novas tentativas (backoff exponencial); repassa o erro da última."""
    import time
    import urllib.request
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "geovoto (pesquisa academica)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:
            if i == tentativas - 1:
                raise
            time.sleep(2**i)
    raise AssertionError("inalcançável")
