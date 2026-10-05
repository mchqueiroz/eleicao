import pandas as pd
from pathlib import Path

def inspecionar_dados():
    PROC_DIR = Path("data/processed")
    df = pd.read_parquet(PROC_DIR / "final_model_data.parquet")
    
    print("--- ESTRUTURA DO DATAFRAME ---")
    print(f"Colunas disponíveis: {df.columns.tolist()}")
    print("\n--- AMOSTRA DOS DADOS (Primeiras 5 linhas) ---")
    print(df.head())

if __name__ == '__main__':
    inspecionar_dados()
