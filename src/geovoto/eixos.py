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
from geovoto.espacial import adjacencia
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


def _r2_por_subconjunto(y, blocos: dict, w):
    """R² ajustado de qualquer união de blocos a partir de uma única matriz Z'WZ do modelo completo.

    Equivale a r2_ajustado(y, hstack(blocos de S), w) (ver tests/test_eixos.py), mas cada submodelo
    resolve um sistema p×p em vez de uma regressão n×p: viabiliza bootstrap e simulação de poder.
    """
    nomes = list(blocos)
    Z = np.hstack([np.ones((len(y), 1))] + [blocos[b] for b in nomes])
    Zw = Z * w[:, None]
    G, g = Zw.T @ Z, Zw.T @ y
    sst = float(np.sum(w * (y - np.average(y, weights=w)) ** 2))
    syy, sy, sw = float(np.sum(w * y * y)), float(np.sum(w * y)), float(np.sum(w))
    cols, i = {}, 1
    for b in nomes:
        cols[b] = np.arange(i, i + blocos[b].shape[1])
        i += blocos[b].shape[1]
    n = len(y)

    def r2(S) -> float:
        idx = np.concatenate([[0]] + [cols[b] for b in S])
        beta = np.linalg.lstsq(G[np.ix_(idx, idx)], g[idx], rcond=None)[0]
        sse = syy - float(g[idx] @ beta)                 # Σw(y−Zβ)² = y'Wy − β'Z'Wy na solução
        r = 1 - sse / sst
        p = len(idx) - 1
        return float(1 - (1 - r) * (n - 1) / (n - p - 1))
    return r2


def shapley(y, blocos: dict, w) -> dict:
    """Shapley de cada bloco no R² ajustado, amplitude entre ordens, efeitos únicos e compartilhado."""
    nomes = list(blocos)
    cache: dict = {(): 0.0}
    r2 = _r2_por_subconjunto(np.asarray(y, float), blocos, np.asarray(w, float))

    def v(S):
        if S not in cache:
            cache[S] = r2(S)
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
    W = adjacencia(arestas, ids)
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

def base(ano: int, turno: int = 1) -> pd.DataFrame:
    p = pd.read_parquet(PROCESSED / "painel_presidente.parquet").query("ano == @ano & turno == @turno")
    c = pd.read_parquet(PROCESSED / f"censo{2010 if ano < 2020 else 2022}_municipio.parquet")
    d = p.merge(c, on="cd_municipio_ibge", how="left").set_index("cd_municipio_ibge").sort_index()
    return _desfechos(d.assign(uf=d.sigla_uf))


def _desfechos(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["log_aptos"] = np.log(d.aptos)
    d["yA"] = np.log((d.votos_A + 0.5) / (d.validos - d.votos_A + 0.5))
    d["yB"] = np.log((d.votos_B + 0.5) / (d.validos - d.votos_B + 0.5))
    d["yComp"] = np.log(d.comparecimento / (d.aptos - d.comparecimento))
    d["margem_abs"] = (d.votos_A - d.votos_B).abs() / d.validos
    d["sA_pp"] = 100 * d.votos_A / d.validos
    return d


# ---------- robustez pré-especificada (HIPOTESES.md §1 e §8) ----------

EXTRAS_2022 = {"renda_media": ["renda_pc_media"], "internet": ["pct_domicilios_internet"],
               "idade": ["idade_mediana"], "alfabetizacao": ["pct_alfabetizados_15mais"]}


def regioes_imediatas() -> pd.Series:
    from geovoto import RAW
    r = pd.read_csv(RAW / "bd" / "municipio.csv.gz", usecols=["id_municipio", "id_regiao_imediata"])
    r = r.set_index("id_municipio").id_regiao_imediata
    return pd.concat([r, pd.Series({5101837: r[5107925]})])   # Boa Esperança do Norte → região de Sorriso


def agregar_regioes(d: pd.DataFrame) -> pd.DataFrame:
    """Escala alternativa (MAUP): soma contagens e pondera covariáveis por aptos em cada região imediata."""
    reg = d.index.map(regioes_imediatas())
    contagens = ["votos_A", "votos_B", "validos", "aptos", "comparecimento"]
    covs = [c for c in sum(DIMENSOES.values(), []) if c != "log_aptos"]
    w = d.aptos
    agg = d[contagens].groupby(reg).sum()
    agg[covs] = d[covs].mul(w, axis=0).groupby(reg).sum().div(w.groupby(reg).sum(), axis=0)
    agg["uf"] = d.uf.groupby(reg).first()
    return _desfechos(agg.rename_axis("cd_regiao"))


def arestas_regioes(arestas: pd.DataFrame) -> pd.DataFrame:
    reg = regioes_imediatas()
    a = pd.DataFrame({"origem": arestas.origem.map(reg), "destino": arestas.destino.map(reg), "tipo": arestas.tipo})
    return a[a.origem != a.destino].drop_duplicates(["origem", "destino"])


def robustez(ano: int, d: pd.DataFrame, V: np.ndarray, arestas: pd.DataFrame) -> dict:
    """Escala (regiões imediatas), 2º turno como desfecho e, em 2022+, dimensões só do Censo 2022."""
    out = {}
    dr = agregar_regioes(d)
    Vr = mesf(arestas_regioes(arestas), dr.index)[MESF_LIMIAR]
    br, _ = blocos(dr, Vr)
    wr = dr.aptos.to_numpy(float)
    out["regioes_imediatas"] = {a: shapley(dr[a].to_numpy(float), br, wr)["shapley"] for a in ALVOS_BOOT}
    d2 = base(ano, turno=2)
    if len(d2) and d2.index.equals(d.index):
        b2, _ = blocos(d2, V)
        out["segundo_turno"] = {"yA": shapley(d2.yA.to_numpy(float), b2, d2.aptos.to_numpy(float))["shapley"]}
    if ano >= 2020:
        _, b4 = blocos(d, V)
        z = lambda X: (X - X.mean(0)) / X.std(0)
        b4 = b4 | {k: z(d[c].to_numpy(float)) for k, c in EXTRAS_2022.items()}
        w = d.aptos.to_numpy(float)
        def unicos(y):                       # 9 blocos: 9! ordens seria caro; só os efeitos únicos interessam
            r2 = _r2_por_subconjunto(y, b4, w)
            todos = tuple(b4)
            return {k: r2(todos) - r2(tuple(x for x in todos if x != k)) for k in todos}
        out["eixo4_estendido"] = {a: unicos(d[a].to_numpy(float)) for a in ALVOS_BOOT}
    return out


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
    if arestas is not None:
        S = b1["estrutura"]
        d, reais, pl = pares_fronteira(d, arestas, centro)
        out["fronteira_pp"] = {"real": fronteira(d, reais, S, "uf"),
                               "placebo": fronteira(d, pl, S, "placebo")}
        out["fronteira_boot"] = bootstrap_fronteira(d, reais, pl, S, N_BOOT, CONFIG["seed"])
    return out


def pares_fronteira(d: pd.DataFrame, arestas, centro) -> tuple:
    """Pares contíguos em UFs diferentes (reais) e pares dentro da UF que cruzam a linha-placebo
    (cada UF partida na mediana da longitude dos centroides)."""
    c = centro.loc[d.index]
    lado = np.where(c.lon > c.groupby("uf").lon.transform("median"), "L", "O")
    d = d.assign(placebo=d.uf + lado)
    pl = pares_entre(arestas, d.placebo)
    pl = pl[d.uf[pl.origem].to_numpy() == d.uf[pl.destino].to_numpy()]
    return d, pares_entre(arestas, d.uf), pl


def bootstrap_fronteira(d, reais, pl, S, n: int, seed: int) -> list:
    """IC de (real − placebo): reamostra divisas inteiras (par de UFs) e, no placebo, UFs inteiras."""
    rng = np.random.default_rng(seed)
    div_real = [tuple(sorted(x)) for x in zip(d.uf[reais.origem], d.uf[reais.destino])]
    div_pl = d.uf[pl.origem].to_numpy()

    def reamostra(p, rotulos):
        grupos = pd.Series(np.arange(len(p))).groupby(pd.Series(rotulos)).apply(list).tolist()
        idx = np.concatenate([grupos[k] for k in rng.integers(0, len(grupos), len(grupos))])
        return p.iloc[idx]

    return [{"real": fronteira(d, reamostra(reais, div_real), S, "uf"),
             "placebo": fronteira(d, reamostra(pl, div_pl), S, "placebo")} for _ in range(n)]


def bootstrap_eixo1_4(d: pd.DataFrame, V: np.ndarray, n: int, seed: int) -> list:
    rng = np.random.default_rng(seed)
    pos_uf = [np.flatnonzero(d.uf.to_numpy() == u) for u in d.uf.unique()]
    reps = []
    for _ in range(n):
        idx = np.concatenate([rng.choice(p, len(p)) for p in pos_uf])
        r = eixo1_e_4(d.iloc[idx], V[idx], None, None, ALVOS_BOOT)
        reps.append({e: {a: {k: r[e][a][k] for k in ("shapley", "unicos", "compartilhado")}
                         for a in ALVOS_BOOT} for e in ("eixo1", "eixo4")})
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
        r["eixo3"] = {"municipio": isolamento_exposicao(d), "local": isolamento_exposicao(loc)}
        boot = bootstrap_municipios(loc, {"eixo2": decompor_variancia, "eixo3": isolamento_exposicao},
                                    N_BOOT, CONFIG["seed"])
        r["eixo2_boot"], r["eixo3_boot"] = boot["eixo2"].to_dict("list"), boot["eixo3"].to_dict("list")
        r["robustez"] = robustez(ano, d, V, arestas)
        r["n_autovetores_mesf"] = int(V.shape[1])
        resultados[ano] = r
    return resultados


TAG = "prereg-v1"
PROTEGIDOS = ["HIPOTESES.md", "config.toml", "src/geovoto"]


def _git(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def prereg_congelado() -> bool:
    return _git("tag", "-l", TAG).stdout.strip() == TAG


def verificar_prereg() -> dict:
    """Bloqueia se a tag não existe, não está no histórico de HEAD ou há mudanças não commitadas
    nos arquivos protegidos. Devolve a proveniência (commit e arquivos alterados desde a tag),
    que vai junto dos resultados para ser declarada na seção "Desvios"."""
    if not prereg_congelado():
        sys.exit(f"Bloqueado: congele o pré-registro (git tag {TAG}) antes de rodar a análise.")
    if _git("merge-base", "--is-ancestor", TAG, "HEAD").returncode != 0:
        sys.exit(f"Bloqueado: HEAD não descende de {TAG}.")
    if _git("status", "--porcelain", "--", *PROTEGIDOS).stdout.strip():
        sys.exit("Bloqueado: há mudanças não commitadas em " + ", ".join(PROTEGIDOS))
    alterados = _git("diff", "--name-only", TAG, "HEAD", "--", *PROTEGIDOS).stdout.split()
    if alterados:
        print("AVISO: arquivos alterados desde o pré-registro (declarar em Desvios):", alterados)
    return {"commit": _git("rev-parse", "HEAD").stdout.strip(), "alterados_desde_prereg": alterados}


if __name__ == "__main__":
    proveniencia = verificar_prereg()
    saida = ROOT / "data" / "output" / "eixos"
    saida.mkdir(parents=True, exist_ok=True)
    resultados = {"_proveniencia": proveniencia} | rodar()
    (saida / "resultados.json").write_text(json.dumps(resultados, indent=1, default=float))
    print("resultados em", saida / "resultados.json")
