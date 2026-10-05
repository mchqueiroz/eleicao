import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plotar_forest_manual():
    PROC_DIR = Path("data/processed")
    # Carregar o resumo já gerado
    df = pd.read_csv(PROC_DIR / "hierarchical_summary.csv", index_col=0)
    
    # Filtrar apenas os betas (coeficientes)
    betas = df[df.index.str.startswith('beta')]
    
    # Calcular as distâncias para o erro (errorbar)
    x = betas['mean']
    x_err_low = betas['mean'] - betas['eti89_lb']
    x_err_high = betas['eti89_ub'] - betas['mean']
    
    plt.figure(figsize=(8, 4))
    plt.errorbar(x, betas.index, xerr=[x_err_low, x_err_high], fmt='o', 
                 capsize=5, color='darkblue', ecolor='gray')
    
    plt.axvline(x=0, color='red', linestyle='--', alpha=0.5)
    plt.title("Efeito das Variáveis (Forest Plot de 89% HDI)")
    plt.xlabel("Tamanho do Efeito (Coeficiente)")
    plt.grid(True, axis='x', linestyle='--', alpha=0.3)
    
    plt.savefig(PROC_DIR / "forest_plot_manual.png")
    print(f"✅ Gráfico gerado com sucesso em: {PROC_DIR}/forest_plot_manual.png")

if __name__ == '__main__':
    plotar_forest_manual()
