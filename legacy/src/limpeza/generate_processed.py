# script baseado no local do arquivo — garante escrever no repositório
from pathlib import Path
import pandas as pd

# raiz do repositório (duas pastas acima de src/limpeza)
ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data/processed"

# garantir diretórios
(PROC / "eleitoral").mkdir(parents=True, exist_ok=True)
(PROC / "historico").mkdir(parents=True, exist_ok=True)

# criar pedersen.parquet de exemplo
pedersen = pd.DataFrame({
    "cod_municipio": [1100015, 1100023, 1100031, 1100049, 1100056],
    "pedersen": [0.12, 0.34, 0.23, 0.15, 0.45],
    "log_pop": [10.5, 9.8, 11.2, 8.7, 12.0],
    "idhm": [0.65, 0.72, 0.68, 0.59, 0.75],
    "regiao": ["Norte", "Norte", "Norte", "Norte", "Norte"],
})

pedersen.to_parquet(PROC / "eleitoral" / "pedersen.parquet", index=False)

# criar coronelismo_proxy.parquet de exemplo
coronelismo = pd.DataFrame({
    "cod_municipio": [1100015, 1100023, 1100031, 1100049, 1100056],
    "coronelismo_idx": [0.2, 0.8, 0.5, 0.1, 0.9],
})

coronelismo.to_parquet(PROC / "historico" / "coronelismo_proxy.parquet", index=False)

print("Arquivos de exemplo gerados em data/processed/")
