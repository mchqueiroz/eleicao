from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ELEITORAL = ROOT / "data/processed/eleitoral/pedersen.parquet"
HISTORICO = ROOT / "data/processed/historico/coronelismo_proxy.parquet"

def ensure():
    missing = []
    if not ELEITORAL.exists():
        missing.append(str(ELEITORAL))
    if not HISTORICO.exists():
        missing.append(str(HISTORICO))

    if not missing:
        print("Arquivos processados presentes.")
        return 0

    print("Arquivos ausentes:")
    for p in missing:
        print(" -", p)
    print("Gerando arquivos de exemplo com generate_processed.py ...")

    ret = subprocess.run([sys.executable, "src/limpeza/generate_processed.py"], cwd=str(ROOT))
    return ret.returncode

if __name__ == '__main__':
    exit(ensure())
