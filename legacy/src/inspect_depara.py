import pandas as pd
import requests
import io

def inspecionar_depara():
    url = "https://raw.githubusercontent.com/beta-git/tse-ibge/master/tse_ibge.csv"
    r = requests.get(url).content
    depara = pd.read_csv(io.BytesIO(r), sep=';')
    
    print("--- COLUNAS DO ARQUIVO DE-PARA ---")
    print(depara.columns.tolist())
    print("\n--- AMOSTRA DOS DADOS ---")
    print(depara.head())

if __name__ == '__main__':
    inspecionar_depara()
