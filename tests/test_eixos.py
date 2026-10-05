"""Eixos: lógica verificada em dados SIMULADOS dentro do teste (não são resultados)."""
import subprocess

import numpy as np
import pandas as pd

from geovoto import ROOT
from geovoto.eixos import fronteira, mesf, pares_entre, prereg_congelado, shapley

rng = np.random.default_rng(7)


def test_shapley_blocos_independentes_e_redundantes():
    n = 4000
    x1, x2 = rng.normal(size=(n, 1)), rng.normal(size=(n, 1))
    y = 2 * x1[:, 0] + rng.normal(size=n)
    w = np.ones(n)
    r = shapley(y, {"a": x1, "b": x2}, w)
    assert abs(r["shapley"]["a"] - 0.8) < 0.03 and abs(r["shapley"]["b"]) < 0.01
    r = shapley(y, {"a": x1, "a_copia": x1.copy()}, w)        # redundância total
    assert abs(r["shapley"]["a"] - r["shapley"]["a_copia"]) < 1e-9
    assert abs(r["compartilhado"] - r["total"]) < 1e-3 and r["min"]["a"] < 1e-3


def _grade(salto_pp):
    """Grade 30x30; colunas ≥ 15 formam a 'UF' R. s_A = 40 + 3·x + salto·[R] + ruído."""
    ids = np.arange(900) + 1_000_000
    lin, col = np.divmod(np.arange(900), 30)
    x = rng.normal(size=900)
    uf = np.where(col >= 15, "R", "L")
    d = pd.DataFrame({"uf": uf, "sA_pp": 40 + 3 * x + salto_pp * (uf == "R") + rng.normal(0, 1, 900)},
                     index=ids)
    arestas = [(ids[a], ids[b], "queen") for a in range(900) for b in range(900)
               if a != b and max(abs(lin[a] - lin[b]), abs(col[a] - col[b])) == 1]
    return d, pd.DataFrame(arestas, columns=["origem", "destino", "tipo"]), x[:, None]


def test_fronteira_recupera_salto():
    d, a, X = _grade(5.0)
    assert abs(fronteira(d, pares_entre(a, d.uf), X, "uf") - 5.0) < 0.5
    d, a, X = _grade(0.0)
    assert fronteira(d, pares_entre(a, d.uf), X, "uf") < 0.5


def test_mesf_ortogonal_a_constante():
    d, a, _ = _grade(0.0)
    V = mesf(a, d.index, [0.25])[0.25]
    assert V.shape[1] > 0 and np.allclose(V.sum(0), 0, atol=1e-8)


def test_eixos_bloqueado_sem_prereg():
    if prereg_congelado():
        return
    r = subprocess.run(["uv", "run", "python", "-m", "geovoto.eixos"], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode != 0 and "Bloqueado" in r.stderr


def test_r2_por_gram_igual_a_regressao_direta():
    from geovoto.eixos import _r2_por_subconjunto, r2_ajustado
    n = 800
    blocos = {"a": rng.normal(size=(n, 3)), "b": rng.normal(size=(n, 5)), "c": rng.normal(size=(n, 2))}
    y = blocos["a"] @ [1, -1, .5] + blocos["c"][:, 0] + rng.normal(size=n)
    w = rng.uniform(1, 50, n)
    r2 = _r2_por_subconjunto(y, blocos, w)
    for S in [("a",), ("a", "c"), ("a", "b", "c"), ("b",)]:
        direto = r2_ajustado(y, np.hstack([blocos[b] for b in S]), w)
        assert abs(r2(S) - direto) < 1e-9
