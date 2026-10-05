import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
from pathlib import Path

# 1. Configurando caminhos
ROOT = Path(".")
PROC_DIR = ROOT / "data/processed"
OUT_MODELOS = ROOT / "data/output/modelos"
OUT_FIGURAS = ROOT / "data/output/figuras"

# Garantindo que as pastas de saída existam
OUT_MODELOS.mkdir(parents=True, exist_ok=True)
OUT_FIGURAS.mkdir(parents=True, exist_ok=True)

print("📖 Carregando os dados processados...")
# 2. Leitura dos dados
df_pedersen = pd.read_parquet(PROC_DIR / "eleitoral/pedersen.parquet")
df_coronelismo = pd.read_parquet(PROC_DIR / "historico/coronelismo_proxy.parquet")

# 3. Cruzamento (Merge) das bases pelo código do município
df = df_pedersen.merge(df_coronelismo, on="cod_municipio", how="inner")
print(f"🔗 Bases cruzadas com sucesso! Municípios na análise: {len(df):,}")

# 4. Análise Exploratória (EDA)
print("📊 Gerando gráfico de distribuição...")
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

df["pedersen"].hist(bins=40, ax=axes[0], color='#1f77b4', edgecolor='black', alpha=0.7)
axes[0].set_title("Distribuição da Volatilidade (Pedersen)")
axes[0].set_xlabel("Índice de Pedersen")
axes[0].set_ylabel("Frequência")

df.boxplot(column="pedersen", by="regiao", ax=axes[1], grid=False)
axes[1].set_title("Volatilidade por Região")
axes[1].set_xlabel("Região")
axes[1].set_ylabel("Índice de Pedersen")
plt.suptitle("") # Remove título automático do pandas
plt.tight_layout()

caminho_figura = OUT_FIGURAS / "h1_eda.png"
plt.savefig(caminho_figura, dpi=150)
print(f"🖼️ Gráfico salvo em: {caminho_figura}")

# 5. Modelagem Econométrica (OLS)
print("\n⚙️ Rodando a Regressão Linear Múltipla (OLS)...")
# A fórmula lê-se: pedersen explicado por coronelismo + log_pop + idhm + região (como categoria)
formula = "pedersen ~ coronelismo_idx + log_pop + idhm + C(regiao)"
modelo = smf.ols(formula, data=df).fit()

# Imprimindo o sumário estatístico no terminal
print("\n" + "="*60)
print(modelo.summary())
print("="*60 + "\n")

# 6. Salvando os coeficientes para o artigo
df_resultado = pd.DataFrame({
    "coeficiente": modelo.params,
    "erro_padrao": modelo.bse,
    "p_valor": modelo.pvalues,
    "ic_inferior": modelo.conf_int()[0],
    "ic_superior": modelo.conf_int()[1],
})

caminho_modelo = OUT_MODELOS / "h1_coeficientes.csv"
df_resultado.to_csv(caminho_modelo)
print(f"💾 Coeficientes salvos em: {caminho_modelo}")
