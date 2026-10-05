"""Métricas recuperam valores conhecidos em dados SIMULADOS dentro do teste (não são resultados)."""
import numpy as np
import pandas as pd

from geovoto.metricas import decompor_variancia, isolamento_exposicao


def _simular(sd_uf, sd_mun, sd_local, n_votos, seed=1):
    rng = np.random.default_rng(seed)
    linhas = []
    for u in range(150):
        eu = rng.normal(0, sd_uf)
        for m in range(20):
            em = rng.normal(0, sd_mun)
            for _ in range(rng.integers(1, 9)):  # 1 a 8 locais, como na base real
                p = 1 / (1 + np.exp(-(eu + em + rng.normal(0, sd_local))))
                a = rng.binomial(n_votos, p)
                linhas.append((f"U{u}", f"{u}-{m}", a, n_votos - a))
    return pd.DataFrame(linhas, columns=["uf", "cd_municipio_tse", "votos_A", "votos_B"])


def test_decomposicao_recupera_componentes():
    r = decompor_variancia(_simular(0.4, 0.3, 0.2, n_votos=400))
    alvo = np.array([0.16, 0.09, 0.04]) / 0.29
    est = np.array([r["parcela_uf"], r["parcela_municipio"], r["parcela_local"]])
    assert np.allclose(est, alvo, atol=0.08)


def test_ruido_binomial_e_removido():
    # sem variação real entre locais, a parcela local deve ficar perto de zero mesmo com n pequeno
    r = decompor_variancia(_simular(0.4, 0.3, 0.0, n_votos=60))
    assert r["parcela_local"] < 0.03


def test_isolamento_casos_extremos():
    seg = pd.DataFrame({"votos_A": [10, 0], "votos_B": [0, 10], "validos": [10, 10]})
    r = isolamento_exposicao(seg)
    assert r["isolamento_A"] == r["isolamento_B"] == 1 and r["exposicao_A_B"] == 0
    uni = pd.DataFrame({"votos_A": [6, 3], "votos_B": [4, 2], "validos": [10, 5]})
    r = isolamento_exposicao(uni)
    assert np.isclose(r["isolamento_A"], 0.6) and np.isclose(r["exposicao_A_B"], 0.4)
