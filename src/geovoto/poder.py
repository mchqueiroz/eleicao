"""Poder do desenho, ANTES do congelamento: desfechos SIMULADOS sobre a estrutura real.

Usa as covariáveis, UFs, filtro espacial, pesos e divisas reais, mas gera os desfechos com efeitos
conhecidos. Para cada cenário repete: simula 4 eleições → bootstrap igual ao de geovoto.eixos →
mesma regra de veredito (geovoto.veredito). Mede P(suportada), P(refutada), P(inconclusiva).
Nenhum desfecho eleitoral real é usado: as colunas de voto de base() são ignoradas ou sobrescritas.
"""
import numpy as np
import pandas as pd

from geovoto import CONFIG, PROCESSED, ROOT
from geovoto.eixos import MESF_LIMIAR, base, blocos, bootstrap_fronteira, mesf, pares_fronteira, shapley
from geovoto.veredito import classifica_t1, classifica_t2

ANOS = {2014: 2014, 2018: 2018, 2022: 2022, 2026: 2022}   # 2026 usa a estrutura do Censo 2022
N_REP, N_BOOT = 20, 60
SAIDA = ROOT / "data" / "output" / "poder"


def _z(x, w):
    m = np.average(x, weights=w)
    return (x - m) / np.sqrt(np.average((x - m) ** 2, weights=w))


def _estrutura():
    arestas = pd.read_parquet(PROCESSED / "vizinhanca.parquet")
    centro = pd.read_parquet(PROCESSED / "centroides.parquet").set_index("cd_municipio_ibge")
    cache, V = {}, None
    for censo in sorted(set(ANOS.values())):
        d = base(censo)
        V = mesf(arestas, d.index)[MESF_LIMIAR] if V is None else V
        cache[censo] = (d, blocos(d, V)[0])
    return {ano: cache[c] for ano, c in ANOS.items()}, arestas, centro


def _bootstrap_estrutura(y, b1, w, uf, rng, n):
    pos = [np.flatnonzero(uf == u) for u in np.unique(uf)]
    reps = []
    for _ in range(n):
        i = np.concatenate([rng.choice(p, len(p)) for p in pos])
        reps.append(shapley(y[i], {k: v[i] for k, v in b1.items()}, w[i])["shapley"]["estrutura"])
    return reps


def poder_t1(est, k_final: float, ruido: float, rng) -> dict:
    """Escala do sinal estrutural cresce linearmente de 1 a k_final entre 2014 e 2026."""
    anos = sorted(est)
    fatores = dict(zip(anos, np.linspace(1, k_final, len(anos))))
    efeitos = {}
    for ano in anos:                         # efeitos fixos por cenário (mesma "realidade" em cada réplica)
        d, b1 = est[ano]
        w = d.aptos.to_numpy(float)
        sinal = {k: _z(v @ rng.normal(size=v.shape[1]), w) for k, v in b1.items()}
        efeitos[ano] = (d, b1, w, sinal)
    veredictos, verdadeiro = [], []
    for _ in range(N_REP):
        reps, medias = {}, {}
        for ano in anos:
            d, b1, w, s = efeitos[ano]
            y = fatores[ano] * s["estrutura"] + s["territorio"] + s["vizinhanca"] + ruido * rng.normal(size=len(w))
            reps[ano] = _bootstrap_estrutura(y, b1, w, d.uf.to_numpy(), rng, N_BOOT)
            medias[ano] = shapley(y, b1, w)["shapley"]["estrutura"]
        veredictos.append(classifica_t1(reps)[0])
        verdadeiro.append(medias[anos[-1]] - medias[anos[0]])
    return {"delta_verdadeiro": float(np.mean(verdadeiro)), **_proporcoes(veredictos)}


def poder_t2(est, arestas, centro, salto_pp: float, ruido_pp: float, rng) -> dict:
    """Efeito de UF ~ N(0, J²) com E|γa − γb| = salto_pp; mesmo J no primeiro e no último ano."""
    J = salto_pp / (2 / np.sqrt(np.pi))
    veredictos = []
    for _ in range(N_REP):
        difs = {}
        for ano in (min(est), max(est)):
            d, b1 = est[ano]
            w = d.aptos.to_numpy(float)
            gama = pd.Series(rng.normal(0, J, d.uf.nunique()), index=sorted(d.uf.unique()))
            S = b1["estrutura"]
            d = d.assign(sA_pp=45 + 3 * _z(S @ rng.normal(size=S.shape[1]), w) + d.uf.map(gama).to_numpy()
                         + ruido_pp * rng.normal(size=len(d)))
            dd, reais, pl = pares_fronteira(d, arestas, centro)
            b = bootstrap_fronteira(dd, reais, pl, S, N_BOOT, int(rng.integers(1e9)))
            difs[ano] = np.array([x["real"] - x["placebo"] for x in b])
        veredictos.append(classifica_t2(difs[max(est)], difs[min(est)])[0])
    return {"delta_verdadeiro": salto_pp, **_proporcoes(veredictos)}


def _proporcoes(v: list) -> dict:
    v = pd.Series(v)
    return {f"p_{k}": float((v == k).mean()) for k in ("suportada", "refutada", "inconclusiva")} | {"n_rep": len(v)}


CENARIOS = ([("T1", ruido, k) for ruido in (0.8, 1.6) for k in (1.0, 1.15, 1.3, 1.6)]      # R² ~0,8 e ~0,55
            + [("T2", ruido, salto) for ruido in (6.0, 10.0) for salto in (0.0, 2.0, 3.0, 5.0)])
_EST: tuple = ()     # estrutura compartilhada com os processos filhos (fork)


def _cenario(i: int) -> dict:
    teste, ruido, efeito = CENARIOS[i]
    rng = np.random.default_rng([CONFIG["seed"], i])    # semente por cenário: independe da ordem
    est, arestas, centro = _EST
    if teste == "T1":
        return {"teste": "T1", "cenario": f"ruído {ruido}, sinal estrutural ×{efeito}",
                **poder_t1(est, efeito, ruido, rng)}
    return {"teste": "T2", "cenario": f"ruído {ruido} p.p., salto {efeito} p.p.",
            **poder_t2(est, arestas, centro, efeito, ruido, rng)}


def rodar() -> pd.DataFrame:
    """Um processo por cenário. Rode com OMP_NUM_THREADS=1 (o Makefile faz isso): com várias threads
    de BLAS por processo, matrizes desse tamanho ficam ~3× mais lentas."""
    import multiprocessing as mp
    global _EST
    _EST = _estrutura()
    with mp.get_context("fork").Pool(min(len(CENARIOS), mp.cpu_count())) as pool:
        return pd.DataFrame(pool.map(_cenario, range(len(CENARIOS))))


if __name__ == "__main__":
    SAIDA.mkdir(parents=True, exist_ok=True)
    r = rodar()
    r.to_csv(SAIDA / "poder.csv", index=False)
    linhas = ["# Poder do desenho (desfechos simulados sobre a estrutura real)\n",
              f"{N_REP} réplicas por cenário, {N_BOOT} réplicas de bootstrap, regras de `geovoto.veredito`.\n",
              "| Teste | Cenário | Δ verdadeiro | P(suportada) | P(refutada) | P(inconclusiva) |", "|---|---|---|---|---|---|"]
    linhas += [f"| {x.teste} | {x.cenario} | {x.delta_verdadeiro:+.3f} | {x.p_suportada:.2f} | {x.p_refutada:.2f} | "
               f"{x.p_inconclusiva:.2f} |" for x in r.itertuples()]
    (SAIDA / "poder.md").write_text("\n".join(linhas) + "\n")
    print("\n".join(linhas))
