import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import requests
import unicodedata

def normalize_text(text):
    if not isinstance(text, str): return ""
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').upper().strip()

def plot_mapa_definitivo():
    PROC_DIR = Path("data/processed")
    MALHA_FILE = PROC_DIR / "malha_municipios.json"
    
    # 1. Carregar seus dados (TSE)
    df = pd.read_parquet(PROC_DIR / "final_model_data.parquet")
    df['SG_UF'] = df['SG_UF'].str.strip()
    df['NM_JOIN'] = df['NM_MUNICIPIO'].apply(normalize_text)
    
    # 2. Baixar lista de municípios do IBGE (com tratamento de segurança)
    print("📥 Baixando lista de municípios do IBGE...")
    url_ibge = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    resp = requests.get(url_ibge).json()
    
    lista_ibge = []
    for m in resp:
        micro = m.get('microrregiao')
        if micro and isinstance(micro, dict):
            meso = micro.get('mesorregiao')
            if meso and isinstance(meso, dict):
                uf = meso.get('UF', {})
                sigla = uf.get('sigla')
                
                lista_ibge.append({
                    'codarea': str(m['id'])[:6],
                    'NM_JOIN': normalize_text(m['nome']),
                    'SG_UF': sigla
                })
    
    df_ibge = pd.DataFrame(lista_ibge)
    
    # 3. Merge: TSE -> IBGE
    df_merged = df.merge(df_ibge, on=['NM_JOIN', 'SG_UF'], how='inner')
    
    # 4. Merge: Resultado -> Malha Geométrica
    malha_br = gpd.read_file(MALHA_FILE)
    malha_br['codarea'] = malha_br['codarea'].astype(str).str.slice(0, 6)
    
    final = malha_br.merge(df_merged, on='codarea', how='inner')
    
    # 5. Plotar
    final = final.to_crs("EPSG:5880")
    fig, ax = plt.subplots(1, 1, figsize=(15, 15))
    
    final.plot(column='coronelismo_idx', ax=ax, legend=True, 
               cmap='OrRd', scheme='quantiles', 
               legend_kwds={'title': "Índice de Coronelismo"},
               edgecolor='none')
    
    ax.set_axis_off()
    plt.title("Distribuição Espacial do Índice de Coronelismo (Brasil)")
    plt.savefig(PROC_DIR / "mapa_coronelismo_detalhado.png", dpi=300)
    print(f"✅ Mapa gerado com sucesso em: {PROC_DIR}/mapa_coronelismo_detalhado.png")

if __name__ == '__main__':
    plot_mapa_definitivo()
