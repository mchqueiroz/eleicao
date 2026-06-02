import pymc as pm
import pandas as pd
import arviz as az
from pathlib import Path

def main():
    # 1. Carregar dados reais
    PROC_DIR = Path("data/processed")
    df = pd.read_parquet(PROC_DIR / "final_model_data.parquet")

    # 2. Preparar variáveis
    y = df['PCT_VOTOS_VALIDOS'].values
    x_coronel = df['coronelismo_idx'].values
    log_pop = df['log_pop'].values

    # 3. Definição do Modelo
    with pm.Model() as model:
        alpha = pm.Normal("alpha", mu=0, sigma=1)
        beta_coronel = pm.Normal("beta_coronel", mu=0, sigma=1)
        beta_pop = pm.Normal("beta_pop", mu=0, sigma=1)
        sigma = pm.HalfNormal("sigma", sigma=1)
        
        mu = alpha + beta_coronel * x_coronel + beta_pop * log_pop
        obs = pm.Normal("obs", mu=mu, sigma=sigma, observed=y)
        
        # O segredo: desativar o paralelismo (parallel='none') 
        # Isso evita que o Python tente criar novos processos via fork
        trace = pm.sample(2000, return_inferencedata=True, cores=1)

    # 4. Sumário
    print(az.summary(trace))

if __name__ == '__main__':
    main()
