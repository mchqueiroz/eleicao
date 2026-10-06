"""Análises EXPLORATÓRIAS do artigo, feitas depois de ver os resultados parciais (fora do pré-registro).

E1 Alinhamento por campo: o PT esteve entre os dois primeiros nas quatro eleições, então "PT" e
   "adversário" são definidos sem escolha arbitrária; as séries posicionais A/B misturam lados.
E2 Distribuição nula do salto nas divisas: 200 linhas-placebo aleatórias por ano (direção e corte
   sorteados em cada UF), no lugar da linha única de longitude do pré-registro.
E3 Coeficientes padronizados das covariáveis no modelo completo (estrutura + MESF + UF), por ano,
   com bootstrap de municípios estratificado por UF.
E4 Efeitos de UF condicionais à estrutura (p.p. de voto no PT), para o mapa do território.

Saída: data/output/exploratorio_teses/resultados.json
"""
import json

import numpy as np
import pandas as pd

from geovoto import CONFIG, PROCESSED, ROOT
from geovoto.eixos import DIMENSOES, MESF_LIMIAR, base, blocos, fronteira, mesf, pares_entre

SAIDA = ROOT / "data" / "output" / "exploratorio_teses"
N_PLACEBO = 200
N_BOOT = 200


def campo_pt(ano: int) -> str:
    """'A' ou 'B': qual bloco posicional é o PT (nº 13) naquele ano."""
    if ano >= 2026:
        c = pd.read_parquet(PROCESSED / "candidatos_2026.parquet")
    else:
        c = pd.read_parquet(PROCESSED / "candidatos_presidente.parquet").query("ano == @ano")
    pos = int(c.loc[c.nr_candidato == 13, "posicao_1t"].iloc[0])
    assert pos in (1, 2), f"PT fora dos dois primeiros em {ano}"
    return "AB"[pos - 1]


def linha_aleatoria(d: pd.DataFrame, centro: pd.DataFrame, rng) -> pd.Series:
    """Parte cada UF por uma reta de direção uniforme, cortando entre os quantis 30% e 70%."""
    c = centro.loc[d.index]
    x = c.lon * np.cos(np.deg2rad(c.lat))
    rotulo = pd.Series("", index=d.index)
    for uf, idx in c.groupby("uf").groups.items():
        t = rng.uniform(0, np.pi)
        proj = x[idx] * np.cos(t) + c.lat[idx] * np.sin(t)
        corte = np.quantile(proj, rng.uniform(0.3, 0.7))
        rotulo[idx] = uf + np.where(proj > corte, "1", "0")
    return rotulo


def placebos(d, arestas, centro, S, n: int, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        d2 = d.assign(placebo=linha_aleatoria(d, centro, rng))
        pl = pares_entre(arestas, d2.placebo)
        pl = pl[d2.uf[pl.origem].to_numpy() == d2.uf[pl.destino].to_numpy()]
        out.append(fronteira(d2, pl, S, "placebo"))
    return out


def coeficientes(d: pd.DataFrame, V: np.ndarray, y: np.ndarray) -> dict:
    """β padronizados (desvio-padrão de logit por desvio-padrão da covariável) no modelo completo."""
    b1, _ = blocos(d, V)
    w = d.aptos.to_numpy(float)
    X = np.c_[np.ones(len(y)), b1["estrutura"], b1["vizinhanca"], b1["territorio"]]
    sw = np.sqrt(w)
    beta = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
    nomes = sum(DIMENSOES.values(), [])
    return dict(zip(nomes, (beta[1:1 + len(nomes)] / np.sqrt(np.cov(y, aweights=w))).tolist()))


def efeitos_uf(d: pd.DataFrame, s_pp: np.ndarray) -> dict:
    """γ̂ de UF (p.p.) num MQO ponderado com a estrutura, centrados na média ponderada por aptos."""
    b1, _ = blocos(d, np.empty((len(d), 0)))
    U = pd.get_dummies(d.uf).astype(float)
    X = np.c_[b1["estrutura"], U.to_numpy()]
    w = d.aptos.to_numpy(float)
    sw = np.sqrt(w)
    beta = np.linalg.lstsq(X * sw[:, None], s_pp * sw, rcond=None)[0]
    g = pd.Series(beta[-U.shape[1]:], index=U.columns)
    peso = d.groupby("uf").aptos.sum().reindex(g.index)
    return (g - np.average(g, weights=peso)).to_dict()


def rodar() -> dict:
    arestas = pd.read_parquet(PROCESSED / "vizinhanca.parquet")
    centro = pd.read_parquet(PROCESSED / "centroides.parquet").set_index("cd_municipio_ibge")
    res, ids, V = {}, None, None
    for ano in CONFIG["anos"]:
        d = base(ano)
        if ids is None or not d.index.equals(ids):
            V, ids = mesf(arestas, d.index)[MESF_LIMIAR], d.index
        pt = campo_pt(ano)
        y = d[f"y{pt}"].to_numpy(float)
        s_pt = 100 * d[f"votos_{pt}"].to_numpy(float) / d.validos.to_numpy(float)
        S = blocos(d, V)[0]["estrutura"]
        rng = np.random.default_rng(CONFIG["seed"])
        pos_uf = [np.flatnonzero(d.uf.to_numpy() == u) for u in d.uf.unique()]
        boot = []
        for _ in range(N_BOOT):
            idx = np.concatenate([rng.choice(p, len(p)) for p in pos_uf])
            boot.append(coeficientes(d.iloc[idx], V[idx], y[idx]))
        res[ano] = {"campo_pt": pt,
                    "placebos_aleatorios": placebos(d, arestas, centro, S, N_PLACEBO, CONFIG["seed"]),
                    "coeficientes": coeficientes(d, V, y), "coeficientes_boot": boot,
                    "efeitos_uf_pp": efeitos_uf(d, s_pt)}
        print(ano, pt, f"placebo mediano {np.median(res[ano]['placebos_aleatorios']):.2f}", flush=True)
    return res


if __name__ == "__main__":
    assert campo_pt(2014) == "A" and campo_pt(2018) == "B" and campo_pt(2022) == "A"
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "resultados.json").write_text(json.dumps(rodar()))
    print("ok:", SAIDA / "resultados.json")
