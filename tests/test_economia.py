"""Séries econômicas: cobertura e conferência com totais nacionais divulgados da RAIS."""
import pandas as pd

from geovoto import PROCESSED


def test_rais_totais_e_cobertura():
    r = pd.read_parquet(PROCESSED / "rais_municipio.parquet")
    tot = r.groupby("ano").vinculos_ativos.sum() / 1e6
    # RAIS (MTE): estoque em 31/12 de 49,6 mi (2014), 46,1 mi (2016) e 52,8 mi (2022)
    assert abs(tot[2014] - 49.6) < 0.2 and abs(tot[2016] - 46.1) < 0.2 and abs(tot[2022] - 52.8) < 0.2
    assert (r.groupby("ano").size().loc[2014:] >= 5570).all()
    assert (r.vinculos_publicos <= r.vinculos_ativos).all() and (r.vinculos_agro <= r.vinculos_ativos).all()


def test_bolsa_familia_quebra_de_serie_documentada():
    b = pd.read_parquet(PROCESSED / "bolsa_familia.parquet")
    por_mes = b.groupby("anomes")[["familias_bf_antigo", "familias_bf_novo"]].count()
    assert por_mes.loc["202210", "familias_bf_antigo"] == 0       # só o campo novo em 2022
    assert por_mes.loc["202010", "familias_bf_novo"] == 0         # só o antigo até 2020
