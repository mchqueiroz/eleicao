import pandas as pd
from pathlib import Path

# 1. Configurar Caminhos
ROOT = Path(".")
PROC_DIR = ROOT / "data/processed"

print("📖 A aceder ao Data Lake...")
# Carregar as bases reais
df_tse = pd.read_parquet(PROC_DIR / "eleitoral/presidente_painel.parquet")
df_ibge = pd.read_parquet(PROC_DIR / "ibge_populacao.parquet")

# 2. Tratamento de Tipos para o Join
# Garantir que ambas as chaves são strings para evitar falhas de cruzamento por zeros à esquerda
df_tse["CD_MUNICIPIO"] = df_tse["CD_MUNICIPIO"].astype(str)
df_ibge["cod_municipio"] = df_ibge["cod_municipio"].astype(str)

print("🔀 A executar o Join (TSE + IBGE)...")
# Cruzar os dados do TSE com os dados do IBGE
df_master = df_tse.merge(df_ibge, left_on="CD_MUNICIPIO", right_on="cod_municipio", how="inner")

# Remover colunas redundantes do merge
df_master = df_master.drop(columns=["cod_municipio", "municipio_nome"])

# 3. Exportar a Master Table
caminho_saida = PROC_DIR / "master_table_real.parquet"
df_master.to_parquet(caminho_saida, index=False)

print(f"🚀 Feature Engineering concluída com sucesso!")
print(f"📊 Municípios unificados na Master Table: {len(df_master)}")
print(f"💾 Ficheiro guardado em: {caminho_saida}")
