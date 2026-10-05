"""Linhagens partidárias e indicadores de continuidade dos prefeitos."""
import pandas as pd
import pytest

from geovoto import PROCESSED

pytestmark = pytest.mark.skipif(not (PROCESSED / "prefeitos.parquet").exists(),
                                reason="dados processados ausentes (rode o Makefile)")
from geovoto.municipal import SUCESSORA, linhagem


def test_linhagem_segue_fusoes_ate_o_fim():
    assert linhagem("PEN") == "PRD" and linhagem("DEM") == "UNIÃO" and linhagem("PT") == "PT"
    assert all(linhagem(s) not in SUCESSORA for s in SUCESSORA)   # toda cadeia termina numa sigla vigente


def test_prefeitos_sem_siglas_extintas():
    c = pd.read_parquet(PROCESSED / "prefeitos.parquet")
    linhagens = set(c.filter(like="linhagem_").stack().dropna())
    assert not linhagens & set(SUCESSORA)          # nenhuma sigla antiga sobrou sem sucessora
    assert c.cd_municipio_tse.nunique() == 5569    # sem DF e Fernando de Noronha; com Boa Esperança do Norte
    assert c.filter(like="margem_").stack().dropna().between(0, 1).all()   # NaN: votos válidos zerados (sub judice)
