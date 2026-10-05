import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from pathlib import Path

# 1. Configurando caminhos da nossa infraestrutura
ROOT = Path(".")
PROC_DIR = ROOT / "data/processed"
OUT_MODELOS = ROOT / "data/output/modelos"

print("📖 Carregando a base nacional processada...")
df_painel = pd.read_parquet(PROC_DIR / "eleitoral/presidente_painel.parquet")
df_base = df_painel[["SG_UF", "CD_MUNICIPIO", "PCT_VOTOS_VALIDOS"]].copy()

# =====================================================================
# GERADOR SINTÉTICO DE FEATURES (Até termos os dados reais do IBGE)
# =====================================================================
print("⚙️ Injetando features Econômicas e Espaciais...")
np.random.seed(42)
n_rows = len(df_base)

# Feature Hec: Variação de Renda (Pocketbook voting) e Desemprego
# Simulamos que a renda subiu levemente em média, mas com variação entre cidades
df_base["var_renda_real"] = np.random.normal(2.5, 4.0, size=n_rows)
df_base["taxa_desemprego"] = np.random.uniform(5.0, 14.0, size=n_rows)

# Feature H5: Lag Espacial (A influência dos vizinhos)
# Simulamos uma variável que representa a média de votos da região em volta da cidade
df_base["voto_vizinhanca_lag"] = df_base["PCT_VOTOS_VALIDOS"] * 0.7 + np.random.normal(0, 10, size=n_rows)

# Simulamos a variável dependente (Voto no Incumbente/Governo) com base na economia e nos vizinhos
# Lógica matemática: Aumenta com a renda, cai com o desemprego, e segue os vizinhos
df_base["voto_incumbente"] = 40 + (df_base["var_renda_real"] * 1.5) - (df_base["taxa_desemprego"] * 0.8) + (df_base["voto_vizinhanca_lag"] * 0.3) + np.random.normal(0, 5, size=n_rows)
df_base["voto_incumbente"] = df_base["voto_incumbente"].clip(0, 100)

# =====================================================================
# TESTE DA HIPÓTESE Hec (Voto Econômico)
# =====================================================================
print("\n" + "="*50)
print(" 🔬 TESTE Hec: VOTO ECONÔMICO (Pocketbook Voting)")
print("="*50)
formula_hec = "voto_incumbente ~ var_renda_real + taxa_desemprego"
modelo_hec = smf.ols(formula_hec, data=df_base).fit()
print(modelo_hec.summary().tables[1])

# =====================================================================
# TESTE DA HIPÓTESE H5 (Dependência Espacial - Pseudo Moran's I)
# =====================================================================
print("\n" + "="*50)
print(" 🔬 TESTE H5: AUTOCORRELAÇÃO ESPACIAL (Spatial Lag)")
print("="*50)
formula_h5 = "voto_incumbente ~ voto_vizinhanca_lag + var_renda_real"
modelo_h5 = smf.ols(formula_h5, data=df_base).fit()
print(modelo_h5.summary().tables[1])

# Salvando as novas features para a modelagem final
df_base.to_parquet(PROC_DIR / "eleitoral/features_completas.parquet", index=False)
print("\n🚀 Pipeline de features finalizado e salvo com sucesso em features_completas.parquet!")
