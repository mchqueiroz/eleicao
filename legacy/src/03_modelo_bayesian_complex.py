import pymc as pm
import pandas as pd
import arviz as az
import numpy as np
from pathlib import Path

def rodar_modelo_hierarquico():
    PROC_DIR = Path("data/processed")
    df = pd.read_parquet(PROC_DIR / "final_model_data.parquet")
    
    # 1. Preparação dos dados
    df['state_idx'] = df['SG_UF'].astype("category").cat.codes
    n_states = df['state_idx'].nunique()
    
    # Normalização dos preditores
    df['coronelismo_std'] = (df['coronelismo_idx'] - df['coronelismo_idx'].mean()) / df['coronelismo_idx'].std()
    df['log_pop_std'] = (df['log_pop'] - df['log_pop'].mean()) / df['log_pop'].std()
    df['abstencao_std'] = (df['PCT_ABSTENCAO'] - df['PCT_ABSTENCAO'].mean()) / df['PCT_ABSTENCAO'].std()
    
    # Target (precisa estar no intervalo (0, 1))
    y_target = (df['PCT_VOTOS_VALIDOS'] / 100).clip(0.001, 0.999)

    with pm.Model() as model:
        # Priors Hierárquicos
        sigma_alpha = pm.HalfNormal("sigma_alpha", sigma=1)
        alpha_base = pm.Normal("alpha_base", mu=0, sigma=1)
        alpha_states = pm.Normal("alpha_states", mu=alpha_base, sigma=sigma_alpha, shape=n_states)
        
        # Priors dos coeficientes
        beta_coronel = pm.Normal("beta_coronel", mu=0, sigma=1)
        beta_pop = pm.Normal("beta_pop", mu=0, sigma=1)
        beta_abst = pm.Normal("beta_abstencao", mu=0, sigma=1)
        
        # Parâmetro de concentração (kappa)
        kappa = pm.Exponential("kappa", 1)
        
        # Equação Link (logit) para mu
        logit_mu = alpha_states[df['state_idx'].values] + \
                   beta_coronel * df['coronelismo_std'].values + \
                   beta_pop * df['log_pop_std'].values + \
                   beta_abst * df['abstencao_std'].values
        
        mu = pm.Deterministic("mu", pm.math.sigmoid(logit_mu))
        
        # Conversão para alpha e beta para a distribuição Beta
        alpha_param = mu * kappa
        beta_param = (1 - mu) * kappa
        
        # Likelihood Beta
        y = pm.Beta("y", alpha=alpha_param, beta=beta_param, observed=y_target.values)
        
        # Amostragem
        trace = pm.sample(2000, target_accept=0.95, return_inferencedata=True)
    
    # Salvar resultados
    trace.to_netcdf(PROC_DIR / "hierarchical_model.nc")
    summary = az.summary(trace)
    summary.to_csv(PROC_DIR / "hierarchical_summary.csv")
    
    print("✅ Modelo Hierárquico Beta rodado com sucesso.")
    print(summary[['mean', 'hdi_3%', 'hdi_97%']].filter(like='beta', axis=0))

if __name__ == '__main__':
    rodar_modelo_hierarquico()
