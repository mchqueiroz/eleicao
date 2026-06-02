import pandas as pd
import numpy as np
import pymc as pm
import arviz as az
from pathlib import Path

# 1. Configurando caminhos
ROOT = Path(".")
PROC_DIR = ROOT / "data/processed"
OUT_MODELOS = ROOT / "data/output/modelos"
OUT_MODELOS.mkdir(parents=True, exist_ok=True)

print("📖 Carregando o Data Lake eleitoral...")
df_features = pd.read_parquet(PROC_DIR / "eleitoral/features_completas.parquet")
df_coronelismo = pd.read_parquet(PROC_DIR / "historico/coronelismo_proxy.parquet")

# 🛠️ O FIX DO ENGENHEIRO DE DADOS: Padronizar a chave primária
if "CD_MUNICIPIO" in df_features.columns:
    df_features = df_features.rename(columns={"CD_MUNICIPIO": "cod_municipio"})

# Cruzando dados econômicos, espaciais e históricos
df = df_features.merge(df_coronelismo, on="cod_municipio", how="inner")

# O PyMC exige categorias numéricas para o agrupamento hierárquico
regioes = df["SG_UF"].unique() # Usando SG_UF como proxy regional para este teste
regiao_map = {reg: i for i, reg in enumerate(regioes)}
df["regiao_idx"] = df["SG_UF"].map(regiao_map)
n_regioes = len(regioes)

print(f"🔗 Dados prontos! Municípios: {len(df):,}. Estados/Regiões agrupadas: {n_regioes}.")
print("⚙️ Compilando a arquitetura do Modelo Hierárquico Bayesiano...")

# Isolando os vetores no NumPy para máxima performance em C++
X_renda = df["var_renda_real"].values
X_coronelismo = df["coronelismo_idx"].values
regiao_idx = df["regiao_idx"].values
Y_obs = df["voto_incumbente"].values

# =====================================================================
# O CORAÇÃO QUANTITATIVO: SIMULAÇÃO MONTE CARLO (MCMC)
# =====================================================================
with pm.Model() as modelo_eleitoral:
    # 1. Nível Nacional (Prior Global)
    mu_alpha = pm.Normal("mu_alpha", mu=40, sigma=10)
    sigma_alpha = pm.HalfNormal("sigma_alpha", sigma=5)
    
    # 2. Nível Regional (Efeito de Agrupamento)
    alpha_regiao = pm.Normal("alpha_regiao", mu=mu_alpha, sigma=sigma_alpha, shape=n_regioes)
    
    # 3. Coeficientes das Covariáveis (Hipóteses Hec e H1)
    beta_renda = pm.Normal("beta_renda", mu=0, sigma=2)
    beta_coronelismo = pm.Normal("beta_coronelismo", mu=0, sigma=5)
    
    # 4. Nível Municipal (Equação Final do Modelo)
    mu_municipio = alpha_regiao[regiao_idx] + (beta_renda * X_renda) + (beta_coronelismo * X_coronelismo)
    
    # Dispersão do erro
    sigma_erro = pm.HalfNormal("sigma_erro", sigma=5)
    
    # 5. Verossimilhança (Treinando o modelo com o dado real)
    Y_est = pm.Normal("Y_est", mu=mu_municipio, sigma=sigma_erro, observed=Y_obs)
    
    print("\n🚀 Iniciando amostragem MCMC...")
    print("⚠️ ATENÇÃO: Isso vai acionar todos os núcleos do processador. Pode levar de 1 a 3 minutos.")
    trace = pm.sample(draws=500, tune=500, chains=2, cores=1, return_inferencedata=True, progressbar=True)

print("\n✅ Simulação Bayesiana concluída com sucesso!")

resumo = az.summary(trace, var_names=["mu_alpha", "beta_renda", "beta_coronelismo"])

print("\n" + "="*60)
print(" 📊 RESULTADOS: MODELO HIERÁRQUICO BAYESIANO (PyMC)")
print("="*60)
print(resumo)

caminho_resumo = OUT_MODELOS / "pymc_summary.csv"
resumo.to_csv(caminho_resumo)
print(f"\n💾 Sumário Probabilístico salvo em: {caminho_resumo}")
