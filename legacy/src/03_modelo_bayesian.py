import pymc as pm
import pandas as pd
import arviz as az
from pathlib import Path

def rodar_modelo_completo():
    PROC_DIR = Path("data/processed")
    df = pd.read_parquet(PROC_DIR / "final_model_data.parquet")
    
    # Normalização
    df['coronelismo_std'] = (df['coronelismo_idx'] - df['coronelismo_idx'].mean()) / df['coronelismo_idx'].std()
    df['log_pop_std'] = (df['log_pop'] - df['log_pop'].mean()) / df['log_pop'].std()
    df['abstencao_std'] = (df['PCT_ABSTENCAO'] - df['PCT_ABSTENCAO'].mean()) / df['PCT_ABSTENCAO'].std()
    
    # Definição do Modelo
    with pm.Model() as model:
        alpha = pm.Normal("alpha", mu=0, sigma=1)
        beta_coronel = pm.Normal("beta_coronel", mu=0, sigma=1)
        beta_pop = pm.Normal("beta_pop", mu=0, sigma=1)
        beta_abst = pm.Normal("beta_abstencao", mu=0, sigma=1)
        sigma = pm.HalfNormal("sigma", sigma=1)
        
        mu = alpha + beta_coronel * df['coronelismo_std'].values + \
             beta_pop * df['log_pop_std'].values + \
             beta_abst * df['abstencao_std'].values
        
        y = pm.Normal("y", mu=mu, sigma=sigma, observed=df['PCT_VOTOS_VALIDOS'].values)
        trace = pm.sample(2000, return_inferencedata=True)
    
    # Salvar resultados
    trace.to_netcdf(PROC_DIR / "bayesian_model_full.nc")
    summary = az.summary(trace)
    summary.to_csv(PROC_DIR / "model_summary_full.csv")
    
    print("✅ Modelo Completo rodado e salvo com sucesso.")
    # Imprimir o resumo completo sem selecionar colunas específicas
    print(summary)

if __name__ == '__main__':
    rodar_modelo_completo()
