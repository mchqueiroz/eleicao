import pandas as pd
import requests
import numpy as np
from pathlib import Path

# 1. Configurar Caminhos
ROOT = Path(".")
PROC_DIR = ROOT / "data/processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

print("📡 A iniciar o Extrator da API do IBGE...")

# =====================================================================
# ETAPA 1: Bater na API do SIDRA para extrair População (Censo 2022)
# =====================================================================
print("📥 A extrair dados da População (Censo 2022) via API SIDRA...")
url_ibge = "https://apisidra.ibge.gov.br/values/t/4709/n6/all/v/93/p/2022"

response = requests.get(url_ibge)
if response.status_code != 200:
    print(f"❌ Erro na API do IBGE: {response.status_code}")
    exit()

dados_json = response.json()
df_ibge = pd.DataFrame(dados_json[1:])

df_ibge = df_ibge[['D1C', 'V']]
df_ibge.columns = ['codigo_ibge', 'populacao']
df_ibge['populacao'] = pd.to_numeric(df_ibge['populacao'], errors='coerce')
df_ibge['log_pop'] = np.log(df_ibge['populacao'] + 1)

print(f"✅ Dados do IBGE extraídos com sucesso! ({len(df_ibge)} municípios)")

# =====================================================================
# ETAPA 2: Resolver a Inconsistência de Chaves (Mapeamento IBGE <-> TSE)
# =====================================================================
print("🔄 A descarregar Tabela de Mapeamento (De-Para) TSE-IBGE oficial...")
# Usando o repositório betafcc, padrão ouro e estável para mapeamento
url_mapa = "https://raw.githubusercontent.com/betafcc/Municipios-Brasileiros-TSE/master/municipios_brasileiros_tse.csv"

try:
    df_mapa = pd.read_csv(url_mapa)
    # As colunas neste repositório vêm em minúsculo: codigo_tse, uf, nome_municipio, capital, codigo_ibge
    df_mapa['codigo_tse'] = df_mapa['codigo_tse'].astype(str)
    df_mapa['codigo_ibge'] = df_mapa['codigo_ibge'].astype(str)
except Exception as e:
    print(f"❌ Erro ao descarregar o mapa de conversão: {e}")
    exit()

# =====================================================================
# ETAPA 3: Cruzamento (Merge) e Exportação
# =====================================================================
print("🔀 A traduzir os códigos IBGE para o padrão TSE...")
df_final = df_ibge.merge(df_mapa, on='codigo_ibge', how='inner')

# Ficar apenas com as colunas essenciais
df_final = df_final[['codigo_tse', 'nome_municipio', 'populacao', 'log_pop']]
df_final = df_final.rename(columns={'codigo_tse': 'cod_municipio', 'nome_municipio': 'municipio_nome'})

# Salvar o Parquet final
caminho_saida = PROC_DIR / "ibge_populacao.parquet"
df_final.to_parquet(caminho_saida, index=False)

print(f"🚀 Extrator finalizado com sucesso! Ficheiro guardado em: {caminho_saida}")
print(f"📊 Municípios processados e mapeados: {len(df_final)}")
