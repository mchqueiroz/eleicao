"""Ingestão dos resultados presidenciais do TSE e montagem do painel municipal.

Blocos A/B são posicionais: A = 1º colocado nacional no 1º turno, B = 2º.
Nenhum nome de candidato entra no painel; o vínculo número→partido fica em
`candidatos_presidente.parquet` só para auditoria.
"""
import zipfile

import pandas as pd

from geovoto import CONFIG, PROCESSED, RAW

CARGO_PRESIDENTE = 1
CHAVE = ["ano", "turno", "cd_municipio_tse"]


def _ler(ano: int, tabela: str, colunas: list[str]) -> pd.DataFrame:
    """Lê o CSV `_BR` (cargo presidente, abrangência federal) de dentro do zip."""
    caminho = RAW / "tse" / str(ano) / f"{tabela}_{ano}.zip"
    with zipfile.ZipFile(caminho) as z, z.open(f"{tabela}_{ano}_BR.csv") as f:
        df = pd.read_csv(f, sep=";", encoding="latin1", usecols=colunas)
    df = df[(df.CD_CARGO == CARGO_PRESIDENTE) & (df.SG_UF != "ZZ")]  # exterior fora do painel
    return df.rename(columns={"ANO_ELEICAO": "ano", "NR_TURNO": "turno",
                              "CD_MUNICIPIO": "cd_municipio_tse", "SG_UF": "sg_uf"})


def votos_candidato(ano: int) -> pd.DataFrame:
    df = _ler(ano, "votacao_candidato_munzona",
              ["ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO", "CD_CARGO",
               "NR_CANDIDATO", "SG_PARTIDO", "QT_VOTOS_NOMINAIS"])
    # soma zonas e voto em trânsito (contado no município onde foi dado)
    return (df.groupby(CHAVE + ["NR_CANDIDATO", "SG_PARTIDO"], as_index=False)
              .QT_VOTOS_NOMINAIS.sum()
              .rename(columns={"NR_CANDIDATO": "nr_candidato", "SG_PARTIDO": "sg_partido",
                               "QT_VOTOS_NOMINAIS": "votos"}))


def detalhe(ano: int) -> pd.DataFrame:
    cols = {"QT_APTOS": "aptos", "QT_COMPARECIMENTO": "comparecimento",
            "QT_ABSTENCOES": "abstencoes", "QT_TOTAL_VOTOS_VALIDOS": "validos",
            "QT_VOTOS_BRANCOS": "brancos", "QT_TOTAL_VOTOS_NULOS": "nulos",
            # categorias residuais que fecham as identidades contábeis
            "QT_ELEITORES_SECOES_NAO_INSTALADAS": "aptos_secoes_nao_instaladas",
            "QT_VOTOS_ANULADOS_APU_SEP": "anulados_apuracao_separada"}
    df = _ler(ano, "detalhe_votacao_munzona",
              ["ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO", "CD_CARGO", *cols])
    return df.groupby(CHAVE, as_index=False)[list(cols)].sum().rename(columns=cols)


def depara() -> pd.DataFrame:
    df = pd.read_csv(RAW / "bd" / "municipio.csv.gz",
                     usecols=["id_municipio", "id_municipio_tse", "sigla_uf", "nome_regiao"])
    return df.rename(columns={"id_municipio": "cd_municipio_ibge",
                              "id_municipio_tse": "cd_municipio_tse", "nome_regiao": "regiao"})


def painel_ano(ano: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    v = votos_candidato(ano)
    t1 = v[v.turno == 1].groupby(["nr_candidato", "sg_partido"]).votos.sum()
    ordem = t1.sort_values(ascending=False).reset_index()
    a, b = ordem.nr_candidato.iloc[0], ordem.nr_candidato.iloc[1]
    cand = ordem.assign(ano=ano, posicao_1t=range(1, len(ordem) + 1))

    df = detalhe(ano).merge(blocos_e_nec(v, CHAVE, {a: "A", b: "B"}), on=CHAVE, how="left")
    return df, cand


def blocos_e_nec(v: pd.DataFrame, chave: list, bloco: dict) -> pd.DataFrame:
    """Votos de A e B (0 se ausentes) e número efetivo de candidatos (Laakso-Taagepera) por chave."""
    ab = (v.assign(bloco=v.nr_candidato.map(bloco)).dropna(subset=["bloco"])
            .pivot_table(index=chave, columns="bloco", values="votos", aggfunc="sum", fill_value=0)
            .reindex(columns=["A", "B"], fill_value=0)
            .rename(columns={"A": "votos_A", "B": "votos_B"}))
    p = v.votos / v.groupby(chave).votos.transform("sum")
    nec = (1 / (p**2).groupby([v[c] for c in chave]).sum()).rename("nec")
    return ab.join(nec, how="outer").fillna({"votos_A": 0, "votos_B": 0}).reset_index()


def construir() -> pd.DataFrame:
    partes, cands = zip(*(painel_ano(a) for a in CONFIG["anos"]))
    df = pd.concat(partes, ignore_index=True).merge(depara(), on="cd_municipio_tse", how="left")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED / "painel_presidente.parquet", index=False)
    pd.concat(cands).to_parquet(PROCESSED / "candidatos_presidente.parquet", index=False)
    return df


if __name__ == "__main__":
    df = construir()
    print(df.groupby(["ano", "turno"]).agg(municipios=("cd_municipio_tse", "nunique"),
                                           aptos=("aptos", "sum"), A=("votos_A", "sum"),
                                           B=("votos_B", "sum")))
