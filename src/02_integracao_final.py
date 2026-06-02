import pandas as pd
from pathlib import Path

PROC_DIR = Path("data/processed")
HIST_DIR = PROC_DIR / "historico"

# Carregar
df_master = pd.read_parquet(PROC_DIR / "master_table_real.parquet")
df_coronelismo = pd.read_parquet(HIST_DIR / "coronelismo_proxy.parquet")

# 1. Garantir que as chaves de união sejam ambas do tipo STRING
df_master['CD_MUNICIPIO'] = df_master['CD_MUNICIPIO'].astype(str)
df_coronelismo['cod_municipio'] = df_coronelismo['cod_municipio'].astype(str)

# 2. Executar o Merge agora com tipos alinhados
df_final = df_master.merge(
    df_coronelismo, 
    left_on="CD_MUNICIPIO", 
    right_on="cod_municipio", 
    how="inner"
)

# 3. Limpeza
df_final = df_final.drop(columns=["cod_municipio"])
df_final.to_parquet(PROC_DIR / "final_model_data.parquet", index=False)

print(f"✅ Master Table final pronta! Municípios unificados: {len(df_final)}")
print(f"💾 Ficheiro guardado em: {PROC_DIR / 'final_model_data.parquet'}")
