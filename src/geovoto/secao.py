"""Votos presidenciais por LOCAL de votação (unidade intramunicipal dos eixos 2 e 3).

Usa-se o local (escola), não a seção: seções de um mesmo local são subdivisões quase
arbitrárias do eleitorado, e o local aproxima o bairro. A/B seguem a posição nacional no
1º turno (candidatos_presidente.parquet, gerado por geovoto.tse).
"""
import zipfile

import pandas as pd

from geovoto import CONFIG, PROCESSED, RAW

NAO_VALIDOS = {95, 96, 97}  # branco, nulo, anulado e apurado em separado
COLS = ["ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NR_ZONA", "CD_CARGO",
        "NR_VOTAVEL", "QT_VOTOS", "NR_LOCAL_VOTACAO"]
CHAVE = ["ano", "turno", "cd_municipio_tse", "nr_zona", "nr_local"]


def locais(ano: int) -> pd.DataFrame:
    cand = pd.read_parquet(PROCESSED / "candidatos_presidente.parquet").query("ano == @ano")
    bloco = dict(zip(cand.nr_candidato, cand.posicao_1t.map({1: "A", 2: "B"})))
    partes = []
    with zipfile.ZipFile(RAW / "tse" / str(ano) / f"votacao_secao_{ano}_BR.zip") as z, \
            z.open(f"votacao_secao_{ano}_BR.csv") as f:
        for ch in pd.read_csv(f, sep=";", encoding="latin1", usecols=COLS, chunksize=5_000_000):
            ch = ch[(ch.CD_CARGO == 1) & (ch.SG_UF != "ZZ")]
            g = ch.rename(columns={"ANO_ELEICAO": "ano", "NR_TURNO": "turno",
                                   "CD_MUNICIPIO": "cd_municipio_tse", "NR_ZONA": "nr_zona",
                                   "NR_LOCAL_VOTACAO": "nr_local"})
            b = g.NR_VOTAVEL.map(bloco)
            agg = pd.DataFrame({
                "votos_A": g.QT_VOTOS.where(b == "A", 0),
                "votos_B": g.QT_VOTOS.where(b == "B", 0),
                "validos": g.QT_VOTOS.where(~g.NR_VOTAVEL.isin(NAO_VALIDOS), 0),
            }).groupby([g[c] for c in CHAVE]).sum()
            partes.append(agg)
    return pd.concat(partes).groupby(level=CHAVE).sum().reset_index()


if __name__ == "__main__":
    df = pd.concat([locais(a) for a in CONFIG["anos"]], ignore_index=True)
    df.to_parquet(PROCESSED / "locais_presidente.parquet", index=False)
    print(df.groupby(["ano", "turno"]).agg(locais=("nr_local", "size"),
                                           municipios=("cd_municipio_tse", "nunique"),
                                           A=("votos_A", "sum"), B=("votos_B", "sum")))
