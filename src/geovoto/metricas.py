"""Métricas dos eixos 2 e 3 (invariantes ao lado; A e B sempre reportados juntos).

Eixo 2: decomposição da variância de logit(A/(A+B)) em UF → município → local de votação,
ponderada por votos e com o ruído binomial subtraído do nível local.
Eixo 3: isolamento e exposição (índices de segregação) por unidade.
"""
import numpy as np
import pandas as pd


def _logit_share(a, b):
    return np.log((a + 0.5) / (b + 0.5))  # logit de A/(A+B) com correção de continuidade


def _nivel(y: pd.Series, w: pd.Series, e: pd.Series, grupo: pd.Series):
    """Um nível do estimador de momentos ponderado.

    Unidades i (valor y, peso w, variância de erro conhecida e) dentro de grupos g.
    E[Σ w_i (y_i − ȳ_g)²] = Σ w_i (1 − w_i/W_g)(σ² + e_i)  →  resolve σ².
    Devolve σ², e as médias, pesos e variâncias de erro dos grupos (para o nível de cima).
    """
    W = w.groupby(grupo).sum()
    ybar = (y * w).groupby(grupo).sum() / W
    fator = w * (1 - w / grupo.map(W))
    s = float((w * (y - grupo.map(ybar)) ** 2).sum())
    sigma2 = max((s - float((fator * e).sum())) / float(fator.sum()), 0.0)
    e_grupo = ((w**2) * (sigma2 + e)).groupby(grupo).sum() / W**2   # var. da média do grupo
    return sigma2, ybar, W, e_grupo


def decompor_variancia(locais: pd.DataFrame) -> dict:
    """locais: uf, cd_municipio_tse, votos_A, votos_B (uma linha por local de votação).

    Modelo: logit_l = μ + u_uf + v_mun + w_local + ruído binomial; estima σ²_uf, σ²_mun, σ²_local
    por momentos, corrigindo o viés de poucos locais por município e o ruído amostral.
    """
    d = locais.assign(n=locais.votos_A + locais.votos_B)
    d = d[d.n > 0].reset_index(drop=True)
    y = _logit_share(d.votos_A, d.votos_B)
    p = (d.votos_A + 0.5) / (d.n + 1)
    ruido = 1 / (d.n * p * (1 - p))                              # var. amostral do logit
    w = d.n.astype(float)
    s_local, y_m, w_m, e_m = _nivel(y, w, ruido, d.cd_municipio_tse)
    uf_m = d.groupby("cd_municipio_tse").uf.first().loc[y_m.index]
    s_mun, y_u, w_u, e_u = _nivel(y_m, w_m, e_m, uf_m)
    s_uf, *_ = _nivel(y_u, w_u, e_u, pd.Series("BR", index=y_u.index))
    comp = {"uf": s_uf, "municipio": s_mun, "local": s_local}
    total = sum(comp.values())
    return {f"parcela_{k}": v / total for k, v in comp.items()} | {"var_total": total}


def isolamento_exposicao(u: pd.DataFrame) -> dict:
    """u: votos_A, votos_B, validos por unidade (município ou local)."""
    a, b, t = (u[c].to_numpy(float) for c in ("votos_A", "votos_B", "validos"))
    ok = t > 0
    a, b, t = a[ok], b[ok], t[ok]
    return {"isolamento_A": float(np.sum(a / a.sum() * a / t)),
            "isolamento_B": float(np.sum(b / b.sum() * b / t)),
            "exposicao_A_B": float(np.sum(a / a.sum() * b / t)),
            "exposicao_B_A": float(np.sum(b / b.sum() * a / t))}


def bootstrap_municipios(df: pd.DataFrame, fs: dict, n: int = 200, seed: int = 0) -> dict:
    """Reamostra municípios (clusters) dentro de cada UF e aplica cada f de fs à mesma réplica.

    Devolve {nome: DataFrame com uma linha por réplica}. Cada cópia sorteada de um município
    recebe um rótulo novo, para não se fundir com outra cópia do mesmo município.
    """
    rng = np.random.default_rng(seed)
    df = df.reset_index(drop=True)
    linhas_mun = df.groupby("cd_municipio_tse").indices          # município → posições das linhas
    por_uf = df.groupby("uf").cd_municipio_tse.unique()
    saida = {k: [] for k in fs}
    for _ in range(n):
        sorteio = np.concatenate([rng.choice(m, len(m)) for m in por_uf])
        partes = [linhas_mun[m] for m in sorteio]
        idx = np.concatenate(partes)
        rotulo = np.repeat(np.arange(len(partes)), [len(p) for p in partes])
        rep = df.iloc[idx].assign(cd_municipio_tse=rotulo)
        for k, f in fs.items():
            saida[k].append(f(rep))
    return {k: pd.DataFrame(v) for k, v in saida.items()}
