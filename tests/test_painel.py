"""Testes de consistência do painel presidencial (rodar após `make painel`)."""
import pandas as pd
import pytest

from geovoto import PROCESSED

N_MUNICIPIOS = 5570  # estável de 2013 a 2024; 2026 terá 5571 (Boa Esperança do Norte/MT)


@pytest.fixture(scope="module")
def painel() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "painel_presidente.parquet")


def test_cobertura_e_depara_1_para_1(painel):
    por_turno = painel.groupby(["ano", "turno"])
    assert (por_turno.cd_municipio_tse.nunique() == N_MUNICIPIOS).all()
    assert painel.cd_municipio_ibge.notna().all()
    assert (por_turno.cd_municipio_ibge.nunique() == N_MUNICIPIOS).all()
    assert not painel.duplicated(["ano", "turno", "cd_municipio_tse"]).any()


# Inconsistências do próprio arquivo do TSE (detalhe_votacao_munzona_2014_BR.csv):
# comparecimento + abstenção = aptos − 2, sem seções não instaladas que expliquem.
EXCECOES_APTOS = {(2014, 31054), (2014, 31950)}  # ambos SE, 2 eleitores, nos dois turnos


def test_identidades_contabeis(painel):
    p = painel
    dif = p.comparecimento + p.abstencoes + p.aptos_secoes_nao_instaladas - p.aptos
    falhas = set(zip(p.ano[dif != 0], p.cd_municipio_tse[dif != 0]))
    assert falhas == EXCECOES_APTOS
    assert dif.abs().max() <= 2
    assert (p.validos + p.brancos + p.nulos + p.anulados_apuracao_separada
            == p.comparecimento).all()
    assert (painel.votos_A + painel.votos_B <= painel.validos).all()


def test_segundo_turno_so_tem_A_e_B(painel):
    t2 = painel[painel.turno == 2]
    assert (t2.votos_A + t2.votos_B == t2.validos).all()


def test_nec(painel):
    t2 = painel[painel.turno == 2]
    assert painel.nec.between(1, 15).all()
    assert (t2.nec <= 2 + 1e-9).all()
