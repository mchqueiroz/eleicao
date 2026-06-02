import pandas as pd
from pathlib import Path

# URL direta para os dados em formato CSV (estável e robusta)
URL = "http://www.ipeadata.gov.br/ExibeSerie.aspx?serid=RDPC&formato=csv"
PROC_DIR = Path("data/processed")

print("💰 A extrair Renda Per Capita via CSV direto...")

try:
    # O IPEA fornece um CSV com cabeçalhos na linha 1
    df = pd.read_csv(URL, sep=';', encoding='latin1', skiprows=1)
    
    # Selecionar a última coluna (que contém o dado mais recente)
    # A estrutura do CSV do IPEA costuma ser [Data; Valor]
    colunas = df.columns
    df_recent = df.iloc[-1:] # Pega a última linha
    
    # Salvar
    df_recent.to_parquet(PROC_DIR / "ipea_economia.parquet", index=False)
    print("✅ Sucesso! Dados económicos integrados na infraestrutura.")
    print(df_recent)

except Exception as e:
    print(f"❌ Erro na extração direta: {e}")