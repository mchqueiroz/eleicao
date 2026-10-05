"""Grafo de vizinhança: cobre os 5.571 municípios, é simétrico e conexo (requisito do BYM2)."""
import pandas as pd

from geovoto import PROCESSED
from geovoto.espacial import amc, componentes


def test_grafo():
    a = pd.read_parquet(PROCESSED / "vizinhanca.parquet")
    nos = pd.Index(a.origem.unique())
    assert len(nos) == 5571 and set(a.destino) <= set(nos)
    pares = set(zip(a.origem, a.destino))
    assert all((j, i) in pares for i, j in pares)
    assert componentes(a, nos) == 1


def test_amc_boa_esperanca_do_norte():
    s = amc(pd.Series([5101837, 5106240, 5107925, 3550308]))
    assert s.tolist() == [5107925, 5107925, 5107925, 3550308]
