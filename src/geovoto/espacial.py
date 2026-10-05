"""Malha municipal (IBGE 2025, inclui Boa Esperança do Norte), grafo de vizinhança e AMC.

Grafo = contiguidade queen ∪ 1 vizinho mais próximo, para que ilhas (ex.: Fernando de Noronha,
Ilhabela) tenham vizinho e o grafo seja conexo — exigência do ICAR/BYM2.
"""
import geopandas as gpd
import pandas as pd
from libpysal import weights

from geovoto import PROCESSED, RAW

MALHA = RAW / "ibge" / "malha" / "BR_Municipios_2025.zip"
CRS_METRICO = 5880  # SIRGAS 2000 / Brazil Polyconic

# Área mínima comparável: Boa Esperança do Norte (instalado em 2025) saiu de Sorriso e Nova Ubiratã
AMC = {5101837: 5107925, 5106240: 5107925}  # código IBGE → código da AMC (Sorriso)


def amc(cd_municipio_ibge: pd.Series) -> pd.Series:
    return cd_municipio_ibge.map(AMC).fillna(cd_municipio_ibge).astype(int)


def malha() -> gpd.GeoDataFrame:
    g = gpd.read_file(f"zip://{MALHA}", columns=["CD_MUN", "NM_MUN", "SIGLA_UF"])
    g = g.rename(columns={"CD_MUN": "cd_municipio_ibge", "NM_MUN": "nome", "SIGLA_UF": "uf"})
    g["cd_municipio_ibge"] = g.cd_municipio_ibge.astype(int)
    g = g[~g.cd_municipio_ibge.isin([4300001, 4300002])]  # lagoas Mirim e dos Patos (sem eleitores)
    return g.set_index("cd_municipio_ibge").sort_index()


def vizinhanca(g: gpd.GeoDataFrame) -> pd.DataFrame:
    queen = weights.Queen.from_dataframe(g, use_index=True, silence_warnings=True)
    cent = g.to_crs(CRS_METRICO).centroid
    knn = weights.KNN.from_dataframe(gpd.GeoDataFrame(geometry=cent), k=1, use_index=True)
    arestas = [(i, j, "queen") for i, vs in queen.neighbors.items() for j in vs]
    arestas += [(a, b, "knn1") for i, vs in knn.neighbors.items() for j in vs
                for a, b in ((i, j), (j, i))]  # simetriza
    df = pd.DataFrame(arestas, columns=["origem", "destino", "tipo"])
    return df.drop_duplicates(["origem", "destino"]).reset_index(drop=True)


def adjacencia(arestas: pd.DataFrame, ids: pd.Index):
    """Matriz densa 0/1 do grafo restrita a ids, na ordem de ids (usada por MESF e BYM2)."""
    import numpy as np
    pos = pd.Series(np.arange(len(ids)), index=ids)
    a = arestas[arestas.origem.isin(ids) & arestas.destino.isin(ids)]
    W = np.zeros((len(ids), len(ids)))
    W[pos[a.origem].to_numpy(), pos[a.destino].to_numpy()] = 1
    return W


def componentes(arestas: pd.DataFrame, nos) -> int:
    w = weights.W({n: [] for n in nos} | arestas.groupby("origem").destino.apply(list).to_dict(),
                  silence_warnings=True)
    return w.n_components


if __name__ == "__main__":
    g = malha()
    a = vizinhanca(g)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    a.to_parquet(PROCESSED / "vizinhanca.parquet", index=False)
    c = g.to_crs(CRS_METRICO).centroid.to_crs(4674)  # centroide métrico, guardado em lon/lat
    pd.DataFrame({"cd_municipio_ibge": g.index, "uf": g.uf.values, "lon": c.x.values,
                  "lat": c.y.values}).to_parquet(PROCESSED / "centroides.parquet", index=False)
    print("municípios:", len(g), "| arestas:", len(a), "| só-knn:", (a.tipo == "knn1").sum(),
          "| componentes:", componentes(a, g.index))
