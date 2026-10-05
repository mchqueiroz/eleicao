"""A lógica do modelo recupera parâmetros conhecidos em dados construídos à mão."""
import numpy as np
import pandas as pd

from geovoto.previsao import pi_implicito, simular


def _municipios(pi: float) -> pd.DataFrame:
    A1, B1, O1 = np.array([500, 300, 100]), np.array([300, 500, 100]), np.array([200, 200, 800])
    return pd.DataFrame({"cd_municipio_tse": [1, 2, 3], "uf": "XX", "aptos": 1000,
                         "A1": A1, "B1": B1, "O1": O1, "ab1": 0.2,
                         "sA2": (A1 + pi * O1) / (A1 + B1 + O1),
                         "A2": A1 + pi * O1, "B2": B1 + (1 - pi) * O1})


def test_pi_implicito_recupera_pi():
    assert abs(pi_implicito(_municipios(0.3)) - 0.3) < 1e-9


def test_simular_sem_ruido_e_deterministico():
    t = _municipios(0.3)
    par = {"pi_mu": 0.3, "pi_sd": 0.0, "df": 2, "tau": 0.0, "kappa": 0.0, "nu": 0.0,
           "c_mu": 0.0, "c_sd": 0.0, "eps_ab": 0.0,
           "delta_mun": pd.Series(dtype=float), "delta_uf": pd.Series(dtype=float)}
    s = simular(t, par, n=50)
    assert np.allclose(s["margem_abs"], np.abs(2 * t.sA2 - 1))
    assert np.allclose(s["abst"], 0.2)
