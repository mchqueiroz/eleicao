"""BYM2 recupera o coeficiente em uma grade SIMULADA dentro do teste (não é resultado)."""
import numpy as np

from geovoto.bym2 import ajustar, diagnostico, fator_escala


def test_bym2_recupera_beta():
    rng = np.random.default_rng(3)
    k = 12
    lin, col = np.divmod(np.arange(k * k), k)
    W = ((np.abs(lin[:, None] - lin) + np.abs(col[:, None] - col)) == 1).astype(float)
    x = rng.normal(size=(k * k, 1))
    uf = (col >= k // 2).astype(int)
    suave = np.sin(lin / 3) + np.cos(col / 3)                 # padrão espacial
    eta = -0.2 + 0.5 * x[:, 0] + 0.3 * uf + 0.4 * (suave - suave.mean()) + rng.normal(0, 0.1, k * k)
    n = np.full(k * k, 500)
    y = rng.binomial(n, 1 / (1 + np.exp(-eta)))
    assert fator_escala(W) > 0
    idata = ajustar(y, n, x, uf, W, draws=400, tune=600, chains=2)
    beta = float(idata.posterior.beta.mean())
    d = diagnostico(idata)
    assert abs(beta - 0.5) < 0.1
    assert d["rhat_max"] < 1.05
