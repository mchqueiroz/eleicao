import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_mapa():
    PROC_DIR = Path("data/processed")
    
    # 1. Carregar dados do seu modelo
    df = pd.read_parquet(PROC_DIR / "final_model_data.parquet")
    
    # 2. Carregar o mapa via URL direta (solução para GeoPandas 1.0+)
    # Usando o dataset oficial de países da Natural Earth
    url = "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
    world = gpd.read_file(url)
    brazil = world[world.NAME == "Brazil"]
    
    # 3. Gerar o mapa base
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    brazil.plot(ax=ax, color='#f2f2f2', edgecolor='black')
    
    plt.title("Brasil: Mapeamento de Influência")
    plt.savefig(PROC_DIR / "mapa_final_brasil.png")
    print(f"✅ Mapa final gerado com sucesso em: {PROC_DIR}/mapa_final_brasil.png")

if __name__ == '__main__':
    plot_mapa()
