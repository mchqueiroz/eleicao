import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def plotar_interceptos():
    PROC_DIR = Path("data/processed")
    # Carregar o resumo gerado
    summary = pd.read_csv(PROC_DIR / "hierarchical_summary.csv", index_col=0)
    
    # Filtrar apenas os interceptos (alpha_states)
    states = summary[summary.index.str.contains("alpha_states")]
    
    # Criar um mapeamento simples (ajuste a ordem se necessário conforme seu dataset)
    # Aqui assumimos que o índice dos estados segue a ordem alfabética da categoria criada
    # No seu modelo: df['state_idx'] = df['SG_UF'].astype("category").cat.codes
    # Vamos recuperar a ordem correta dos nomes dos estados:
    df_raw = pd.read_parquet(PROC_DIR / "final_model_data.parquet")
    uf_names = sorted(df_raw['SG_UF'].unique())
    
    states['UF'] = uf_names
    states = states.sort_values(by='mean') # Ordenar pelo valor médio
    
    # Plotar
    plt.figure(figsize=(10, 8))
    plt.errorbar(states['mean'], states['UF'], xerr=(states['eti89_ub'] - states['eti89_lb'])/2, 
                 fmt='o', capsize=5, color='darkblue')
    
    plt.title("Baseline de Votos Válidos por Estado (Interceptos do Modelo)")
    plt.xlabel("Logit da Proporção de Votos Válidos (Intercepto)")
    plt.grid(True, axis='x', linestyle='--', alpha=0.7)
    
    plt.savefig(PROC_DIR / "interceptos_estados.png")
    print(f"✅ Gráfico salvo em: {PROC_DIR}/interceptos_estados.png")

if __name__ == '__main__':
    plotar_interceptos()
