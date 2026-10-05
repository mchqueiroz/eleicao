import pandas as pd
import glob
from pathlib import Path

# Configurando caminhos baseados na raiz
ROOT = Path(".")
RAW_TSE_DIR = ROOT / "data/raw/tse/detalhe_votacao_munzona_2022"
PROCESSED_DIR = ROOT / "data/processed/eleitoral"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

print("🔍 Buscando arquivos em data/raw/tse/detalhe_votacao_munzona_2022...")
arquivos_estados = glob.glob(str(RAW_TSE_DIR / "detalhe_votacao_munzona_2022_*.csv"))

if len(arquivos_estados) == 0:
    print(f"❌ Erro: Nenhum arquivo CSV encontrado em: {RAW_TSE_DIR.resolve()}")
    exit()

print(f"📦 Encontrados {len(arquivos_estados)} arquivos. Iniciando varredura...\n")

lista_dfs = []

for caminho_arquivo in arquivos_estados:
    estado = Path(caminho_arquivo).stem.split("_")[-1]
    
    # Lendo o CSV
    df_estado = pd.read_csv(caminho_arquivo, sep=";", encoding="latin-1", low_memory=False)
    
    # Converte a coluna para maiúsculo para garantir que o filtro funcione ("Presidente" vira "PRESIDENTE")
    df_filtrado = df_estado[
        (df_estado["DS_CARGO"].str.upper() == "PRESIDENTE") & 
        (df_estado["NR_TURNO"] == 1)
    ].copy()
    
    if len(df_filtrado) > 0:
        print(f"✅ Arquivo {estado}: Encontrou {len(df_filtrado)} linhas para Presidente!")
        lista_dfs.append(df_filtrado)
    else:
        print(f"❌ Arquivo {estado}: Sem dados presidenciais.")

print("\n🥞 Empilhando dados encontrados...")
df_nacional = pd.concat(lista_dfs, ignore_index=True)

print(f"📊 Total de linhas empilhadas: {len(df_nacional):,}")

print("🧮 Agrupando dados por município (somando as zonas eleitorais)...")
df_municipios = df_nacional.groupby(["SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO"]).agg({
    "QT_APTOS": "sum",
    "QT_COMPARECIMENTO": "sum",
    "QT_ABSTENCOES": "sum",
    "QT_TOTAL_VOTOS_VALIDOS": "sum",
    "QT_VOTOS_BRANCOS": "sum",
    "QT_TOTAL_VOTOS_NULOS": "sum"
}).reset_index()

print(f"🏁 Consolidação concluída! Total de municípios únicos: {len(df_municipios):,}")

# Criando as features estruturais para as nossas hipóteses (Abstenção e Votos Válidos)
df_municipios["PCT_ABSTENCAO"] = (df_municipios["QT_ABSTENCOES"] / df_municipios["QT_APTOS"]) * 100
df_municipios["PCT_VOTOS_VALIDOS"] = (df_municipios["QT_TOTAL_VOTOS_VALIDOS"] / df_municipios["QT_COMPARECIMENTO"]) * 100

# Salvando a base final
output_parquet = PROCESSED_DIR / "presidente_painel.parquet"
df_municipios.to_parquet(output_parquet, index=False)

print(f"🚀 Sucesso! Base salva em: {output_parquet}")
