"""A regressão exploratória recupera um coeficiente plantado em dados SIMULADOS no teste."""
import numpy as np
import pandas as pd

from geovoto.exploratorio import regressao


def test_regressao_recupera_efeito_padronizado():
    rng = np.random.default_rng(5)
    n = 3000
    uf = pd.Series(rng.choice([f"U{i}" for i in range(27)], n))
    x = pd.Series(rng.normal(0, 2, n))
    y = 0.5 * x + uf.map({f"U{i}": i / 10 for i in range(27)}) + pd.Series(rng.normal(0, 1, n))
    r = regressao(y, pd.DataFrame({"x": x}), pd.Series(np.ones(n)), uf, ["x"])
    # efeito de 1 desvio-padrão de x (dp = 2) = 1,0
    assert abs(r.coef.iloc[0] - 1.0) < 0.1 and r.ic90_inf.iloc[0] < 1.0 < r.ic90_sup.iloc[0]
