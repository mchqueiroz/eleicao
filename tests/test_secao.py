"""A soma dos locais de votação reproduz o painel municipal, município a município."""
import pandas as pd

from geovoto import PROCESSED


def test_locais_somam_o_municipio():
    k = ["ano", "turno", "cd_municipio_tse"]
    loc = pd.read_parquet(PROCESSED / "locais_presidente.parquet").groupby(k)[
        ["votos_A", "votos_B", "validos"]].sum()
    mun = pd.read_parquet(PROCESSED / "painel_presidente.parquet").set_index(k)[
        ["votos_A", "votos_B", "validos"]]
    assert loc.sort_index().equals(mun.sort_index().astype(loc.dtypes.iloc[0]))
