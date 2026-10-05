import arviz as az
import matplotlib.pyplot as plt
from pathlib import Path

def plotar_analise():
    PROC_DIR = Path("data/processed")
    # Carregar o modelo salvo
    trace = az.from_netcdf(PROC_DIR / "hierarchical_model.nc")
    
    # 1. Plot dos Coeficientes (Beta)
    # Selecionamos os betas para ver se o coronelismo, pop e abstenção são relevantes
    plt.figure(figsize=(10, 6))
    az.plot_forest(trace, var_names=['beta_coronel', 'beta_pop', 'beta_abstencao'], 
                   combined=True, hdi_prob=0.95, colors='blue')
    plt.title("Efeito das Variáveis sobre Votos Válidos (Forest Plot)")
    plt.axvline(x=0, color='red', linestyle='--', alpha=0.5) # Linha do zero
    plt.savefig(PROC_DIR / "forest_plot_betas.png")
    
    # 2. Plot dos Interceptos Estaduais (Alpha)
    plt.figure(figsize=(10, 10))
    az.plot_forest(trace, var_names=['alpha_states'], 
                   combined=True, hdi_prob=0.95, colors='green')
    plt.title("Variação do Intercepto por Estado (Baseline de Votos)")
    plt.savefig(PROC_DIR / "forest_plot_states.png")
    
    print(f"✅ Gráficos salvos em: {PROC_DIR}")

if __name__ == '__main__':
    plotar_analise()
