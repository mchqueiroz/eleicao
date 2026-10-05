"""Eixos 1–4 do pré-registro (HIPOTESES.md). SÓ RODA DEPOIS DA TAG `prereg-v1`.

Eixo 1: Shapley do R² ajustado entre {estrutura, vizinhança (filtro espacial MESF), território (UF)};
        T2 por pares de municípios contíguos em UFs diferentes, contra fronteiras-placebo.
Eixo 2/3: geovoto.metricas sobre locais de votação.
Eixo 4: Shapley entre as dimensões da estrutura (efeitos únicos + parcela compartilhada).
"""
import itertools
import json
import subprocess
import sys

import numpy as np
import pandas as pd

from geovoto import CONFIG, PROCESSED, ROOT
from geovoto.metricas import bootstrap_municipios, decompor_variancia, isolamento_exposicao

# Covariáveis com definição igual em 2010 e 2022 (ver geovoto.ibge)
DIMENSOES = {
    "economica": ["pct_ate_meio_sm"],
    "educacional": ["pct_superior_25mais"],
    "religiosa": ["pct_evangelicos", "pct_catolicos", "pct_sem_religiao"],
    "demografica": ["pct_urbana", "log_aptos"],
    "cor_raca": ["pct_pretos_pardos", "pct_indigenas"],
}
ALVOS = ["yA", "yB", "yComp", "margem_abs"]
ALVOS_BOOT = ["yA", "yB"]   # desfechos principais: intervalos por bootstrap
# Filtro espacial: autovetores com I de Moran ≥ limiar·λmax. A regra usual (0,25) daria 1.258
# vetores (23% de n) e inflaria a vizinhança por sobreajuste; principal 0,75 (217), sensibilidade 0,5 e 0,25.
MESF_LIMIAR = 0.75
MESF_SENSIBILIDADE = [0.5, 0.25]
N_BOOT = 200


# ---------- decomposição de Shapley ----------

def r2_ajustado(y, X, w) -> float:
    sw = np.sqrt(w)
    Xc = np.c_[np.ones(len(y)), X]
    beta, *_ = np.linalg.lstsq(Xc * sw[:, None], y * sw, rcond=None)
    res = y - Xc @ beta
    ybar = np.average(y, weights=w)
    r2 = 1 - np.sum(w * res**2) / np.sum(w * (y - ybar) ** 2)
    n, p = len(y), X.shape[1]
    return float(1 - (1 - r2) * (n - 1) / (n - p - 1))


def shapley(y, blocos: dict, w) -> dict:
    """Shapley de cada bloco no R² ajustado, amplitude entre ordens, efeitos únicos e compartilhado."""
    nomes = list(blocos)
    cache: dict = {(): 0.0}

    def v(S):
        if S not in cache:
            cache[S] = r2_ajustado(y, np.hstack([blocos[b] for b in S]), w)
        return cache[S]

    marg = {b: [] for b in nomes}
    for ordem in itertools.permutations(nomes):
        antes: tuple = ()
        for b in ordem:
            marg[b].append(v(tuple(sorted(antes + (b,)))) - v(tuple(sorted(antes))))
            antes += (b,)
    total = v(tuple(sorted(nomes)))
    unicos = {b: total - v(tuple(sorted(set(nomes) - {b}))) for b in nomes}
    return {"shapley": {b: float(np.mean(m)) for b, m in marg.items()},
            "min": {b: float(np.min(m)) for b, m in marg.items()},
            "max": {b: float(np.max(m)) for b, m in marg.items()},
            "unicos": unicos, "compartilhado": total - sum(unicos.values()), "total": total}


def mesf(arestas: pd.DataFrame, ids: pd.Index, limiares=(MESF_LIMIAR,)) -> dict:
    """Autovetores de MWM com I de Moran alto (filtro espacial de Griffith), por limiar."""
    pos = pd.Series(np.arange(len(ids)), index=ids)
    a = arestas[arestas.origem.isin(ids) & arestas.destino.isin(ids)]
    W = np.zeros((len(ids), len(ids)))
    W[pos[a.origem].to_numpy(), pos[a.destino].to_numpy()] = 1
    M = np.eye(len(ids)) - 1 / len(ids)
    val, vec = np.linalg.eigh(M @ W @ M)
    return {t: vec[:, val >= t * val.max()] for t in limiares}


# ---------- território: fronteiras estaduais vs placebo ----------

def fronteira(df: pd.DataFrame, pares: pd.DataFrame, X: np.ndarray, grupo: str) -> float:
    """Salto médio |γ_a − γ_b| (p.p. de s_A) entre grupos contíguos, condicionado a X.

    Δy_ij = ΔX β + (γ_g(i) − γ_g(j)) + ε em pares contíguos com grupos diferentes.
    """
    pos = pd.Series(np.arange(len(df)), index=df.index)
    i, j = pos[pares.origem].to_numpy(), pos[pares.destino].to_numpy()
    cod = df[grupo].astype("category").cat.codes.to_numpy()
    G = np.eye(cod.max() + 1)[cod]
    y = df.sA_pp.to_numpy()
    D = np.c_[X[i] - X[j], (G[i] - G[j])[:, 1:]]
    coef, *_ = np.linalg.lstsq(D, y[i] - y[j], rcond=None)
    gama = np.r_[0.0, coef[X.shape[1]:]]
    return float(np.mean(np.abs(gama[cod[i]] - gama[cod[j]])))


def pares_entre(arestas: pd.DataFrame, rotulo: pd.Series) -> pd.DataFrame:
    a = arestas[(arestas.tipo == "queen") & (arestas.origem < arestas.destino)]
    a = a[a.origem.isin(rotulo.index) & a.destino.isin(rotulo.index)]
    return a[rotulo[a.origem].to_numpy() != rotulo[a.destino].to_numpy()]


# ---------- montagem e execução ----------

def base(ano: int) -> pd.DataFrame:
    p = pd.read_parquet(PROCESSED / "painel_presidente.parquet").query("ano == @ano & turno == 1")
    c = pd.read_parquet(PROCESSED / f"censo{2010 if ano < 2020 else 2022}_municipio.parquet")
    d = p.merge(c, on="cd_municipio_ibge", how="left").set_index("cd_municipio_ibge").sort_index()
    d["log_aptos"] = np.log(d.aptos)
    d["yA"] = np.log((d.votos_A + 0.5) / (d.validos - d.votos_A + 0.5))
    d["yB"] = np.log((d.votos_B + 0.5) / (d.validos - d.votos_B + 0.5))
    d["yComp"] = np.log(d.comparecimento / (d.aptos - d.comparecimento))
    d["margem_abs"] = (d.votos_A - d.votos_B).abs() / d.validos
    d["sA_pp"] = 100 * d.votos_A / d.validos
    d["uf"] = d.sigla_uf
    return d


def blocos(d: pd.DataFrame, V: np.ndarray) -> tuple[dict, dict]:
    z = lambda X: (X - X.mean(0)) / X.std(0)
    est = {k: z(d[cols].to_numpy(float)) for k, cols in DIMENSOES.items()}
    T = pd.get_dummies(d.uf, drop_first=True).to_numpy(float)
    return {"estrutura": np.hstack(list(est.values())), "vizinhanca": V, "territorio": T}, est


def eixo1_e_4(d: pd.DataFrame, V: np.ndarray, arestas, centro, alvos=ALVOS) -> dict:
    w = d.aptos.to_numpy(float)
    b1, b4 = blocos(d, V)
    out = {"eixo1": {a: shapley(d[a].to_numpy(float), b1, w) for a in alvos},
           "eixo4": {a: shapley(d[a].to_numpy(float), b4, w) for a in alvos}}
    if arestas is not None:   # T2: divisa real vs placebo (cada UF partida na mediana da longitude)
        c = centro.loc[d.index]
        lado = np.where(c.lon > c.groupby("uf").lon.transform("median"), "L", "O")
        d = d.assign(placebo=d.uf + lado)
        pl = pares_entre(arestas, d.placebo)
        pl = pl[d.uf[pl.origem].to_numpy() == d.uf[pl.destino].to_numpy()]
        S = b1["estrutura"]
        out["fronteira_pp"] = {"real": fronteira(d, pares_entre(arestas, d.uf), S, "uf"),
                               "placebo": fronteira(d, pl, S, "placebo")}
    return out


def bootstrap_eixo1_4(d: pd.DataFrame, V: np.ndarray, n: int, seed: int) -> list:
    rng = np.random.default_rng(seed)
    pos_uf = [np.flatnonzero(d.uf.to_numpy() == u) for u in d.uf.unique()]
    reps = []
    for _ in range(n):
        idx = np.concatenate([rng.choice(p, len(p)) for p in pos_uf])
        r = eixo1_e_4(d.iloc[idx], V[idx], None, None, ALVOS_BOOT)
        reps.append({e: {a: r[e][a]["shapley"] for a in ALVOS_BOOT} for e in ("eixo1", "eixo4")})
    return reps


def rodar() -> dict:
    arestas = pd.read_parquet(PROCESSED / "vizinhanca.parquet")
    centro = pd.read_parquet(PROCESSED / "centroides.parquet").set_index("cd_municipio_ibge")
    locais = pd.read_parquet(PROCESSED / "locais_presidente.parquet")
    uf_tse = pd.read_parquet(PROCESSED / "painel_presidente.parquet").drop_duplicates(
        "cd_municipio_tse").set_index("cd_municipio_tse").sigla_uf
    resultados, Vs, ids = {}, {}, None
    for ano in CONFIG["anos"]:
        d = base(ano)
        if ids is None or not d.index.equals(ids):
            Vs, ids = mesf(arestas, d.index, [MESF_LIMIAR, *MESF_SENSIBILIDADE]), d.index
        V = Vs[MESF_LIMIAR]
        r = eixo1_e_4(d, V, arestas, centro)
        w = d.aptos.to_numpy(float)
        r["eixo1_sensibilidade_mesf"] = {
            t: {a: shapley(d[a].to_numpy(float), blocos(d, Vs[t])[0], w)["shapley"] for a in ALVOS_BOOT}
            for t in MESF_SENSIBILIDADE}
        r["eixo1_4_boot"] = bootstrap_eixo1_4(d, V, N_BOOT, CONFIG["seed"])
        loc = locais.query("ano == @ano & turno == 1").assign(uf=lambda x: x.cd_municipio_tse.map(uf_tse))
        r["eixo2"] = decompor_variancia(loc)
        r["eixo2_boot"] = bootstrap_municipios(loc, decompor_variancia, N_BOOT, CONFIG["seed"]).to_dict("list")
        r["eixo3"] = {"municipio": isolamento_exposicao(d), "local": isolamento_exposicao(loc)}
        r["eixo3_boot"] = bootstrap_municipios(loc, isolamento_exposicao, N_BOOT, CONFIG["seed"]).to_dict("list")
        r["n_autovetores_mesf"] = int(V.shape[1])
        resultados[ano] = r
    return resultados


def prereg_congelado() -> bool:
    tags = subprocess.run(["git", "tag", "-l", "prereg-v1"], cwd=ROOT, capture_output=True, text=True)
    return tags.stdout.strip() == "prereg-v1"


if __name__ == "__main__":
    if not prereg_congelado():
        sys.exit("Bloqueado: congele o pré-registro (git tag prereg-v1) antes de rodar os eixos.")
    saida = ROOT / "data" / "output" / "eixos"
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "resultados.json").write_text(json.dumps(rodar(), indent=1, default=float))
    print("resultados em", saida / "resultados.json")
