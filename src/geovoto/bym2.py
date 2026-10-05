"""Modelo BYM2 (Riebler et al., 2016) em PyMC: robustez e inferência dos coeficientes estruturais.

logit p_i = α + X_i β + u_UF(i) + σ (√(ρ/s) φ_i + √(1−ρ) θ_i),   y_i ~ Binomial(n_i, p_i)
φ ~ ICAR(grafo queen ∪ kNN1), θ ~ N(0,1), s = fator de escala do ICAR. SÓ RODA APÓS `prereg-v1`.
"""
import sys

import arviz as az
import numpy as np
import pandas as pd
import pymc as pm

from geovoto import CONFIG, PROCESSED, ROOT


def adjacencia(arestas: pd.DataFrame, ids: pd.Index) -> np.ndarray:
    pos = pd.Series(np.arange(len(ids)), index=ids)
    a = arestas[arestas.origem.isin(ids) & arestas.destino.isin(ids)]
    W = np.zeros((len(ids), len(ids)))
    W[pos[a.origem].to_numpy(), pos[a.destino].to_numpy()] = 1
    return W


def fator_escala(W: np.ndarray) -> float:
    """Média geométrica das variâncias marginais do ICAR (pseudo-inversa de Q = D − W)."""
    Q = np.diag(W.sum(1)) - W
    val, vec = np.linalg.eigh(Q)
    pos = val > 1e-8 * val.max()
    var = (vec[:, pos] ** 2 / val[pos]).sum(1)
    return float(np.exp(np.mean(np.log(var))))


def modelo(y, n, X, uf_idx, W, s) -> pm.Model:
    with pm.Model() as m:
        alfa = pm.Normal("alfa", 0, 2)
        beta = pm.Normal("beta", 0, 1, shape=int(X.shape[1]))
        sd_uf = pm.HalfNormal("sd_uf", 1)
        uf = pm.Deterministic("uf", sd_uf * pm.Normal("uf_z", 0, 1, shape=int(uf_idx.max()) + 1))
        sigma = pm.HalfNormal("sigma", 1)
        rho = pm.Beta("rho", 0.5, 0.5)
        phi = pm.ICAR("phi", W=W)
        theta = pm.Normal("theta", 0, 1, shape=int(len(y)))
        conv = sigma * (pm.math.sqrt(rho / s) * phi + pm.math.sqrt(1 - rho) * theta)
        pm.Binomial("y", n=n, logit_p=alfa + X @ beta + uf[uf_idx] + conv, observed=y)
    return m


def ajustar(y, n, X, uf_idx, W, draws=1000, tune=1000, chains=4, seed=CONFIG["seed"]):
    with modelo(y, n, X, uf_idx, W, fator_escala(W)):
        return pm.sample(draws=draws, tune=tune, chains=chains, random_seed=seed,
                         target_accept=0.9, progressbar=False)


def diagnostico(idata, vars_=("alfa", "beta", "sd_uf", "sigma", "rho")) -> dict:
    s = az.summary(idata, var_names=list(vars_))
    return {"rhat_max": float(s.r_hat.max()), "ess_min": float(s.ess_bulk.min()),
            "divergencias": int(idata.sample_stats.diverging.sum())}


if __name__ == "__main__":
    from geovoto.eixos import DIMENSOES, base, prereg_congelado
    if not prereg_congelado():
        sys.exit("Bloqueado: congele o pré-registro (git tag prereg-v1) antes de rodar o BYM2.")
    arestas = pd.read_parquet(PROCESSED / "vizinhanca.parquet")
    saida = ROOT / "data" / "output" / "bym2"
    saida.mkdir(parents=True, exist_ok=True)
    cols = sum(DIMENSOES.values(), [])
    resumo = []
    for ano in CONFIG["anos"]:
        d = base(ano)
        W = adjacencia(arestas, d.index)
        X = d[cols].to_numpy(float)
        X = (X - X.mean(0)) / X.std(0)
        uf_idx = d.uf.astype("category").cat.codes.to_numpy()
        for alvo in ["votos_A", "votos_B"]:
            idata = ajustar(d[alvo].to_numpy(), d.validos.to_numpy(), X, uf_idx, W)
            idata.to_netcdf(saida / f"{ano}_{alvo}.nc")
            resumo.append({"ano": ano, "alvo": alvo, **diagnostico(idata)})
    pd.DataFrame(resumo).to_csv(saida / "diagnosticos.csv", index=False)
