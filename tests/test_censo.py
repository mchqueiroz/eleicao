"""Covariáveis censitárias: cobertura, faixas e conferência com valores divulgados pelo IBGE."""
import pandas as pd
import pytest

from geovoto import PROCESSED


@pytest.fixture(scope="module", params=[2010, 2022])
def censo(request) -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / f"censo{request.param}_municipio.parquet")


def test_cobertura(censo):
    assert censo.cd_municipio_ibge.nunique() == 5570
    pcts = censo.filter(like="pct_")
    assert pcts.notna().all().all()
    assert ((pcts >= 0) & (pcts <= 100)).all().all()


def test_extremos_de_renda_2022():
    # Divulgação do Censo 2022 (out/2025): maior renda pc em Nova Lima/MG, menor em Uiramutã/RR
    c = pd.read_parquet(PROCESSED / "censo2022_municipio.parquet").set_index("cd_municipio_ibge")
    assert c.renda_pc_media.idxmax() == 3144805 and round(c.renda_pc_media.max()) == 4300
    assert c.renda_pc_media.idxmin() == 1400704 and round(c.renda_pc_media.min(), 2) == 288.65
