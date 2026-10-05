"""Prefeitos eleitos em 2016, 2020 e 2024 → indicadores de continuidade local (H1, EXPLORATÓRIA).

Saída por município (código TSE): partido do eleito em cada ano (harmonizado por linhagem),
margem do eleito no turno decisivo e indicadores de continuidade. A identidade da pessoa é
comparada pelo nome normalizado e NÃO é gravada.
"""
import unicodedata
import zipfile

import pandas as pd

from geovoto import PROCESSED, RAW

ANOS = [2016, 2020, 2024]
PREFEITO, ORDINARIA = 11, 2
# Renomeações e fusões até 2024: sigla → sucessora (aplicada até o ponto fixo).
SUCESSORA = {"PMDB": "MDB", "PR": "PL", "PRB": "REPUBLICANOS", "PPS": "CIDADANIA", "PTN": "PODE",
             "PT do B": "AVANTE", "PEN": "PATRIOTA", "PSDC": "DC", "SD": "SOLIDARIEDADE",
             "PHS": "PODE", "PRP": "PATRIOTA", "PPL": "PC do B", "DEM": "UNIÃO", "PSL": "UNIÃO",
             "PATRIOTA": "PRD", "PTB": "PRD", "PROS": "SOLIDARIEDADE", "PSC": "PODE",
             "PTC": "AGIR", "PMN": "MOBILIZA"}


def linhagem(sigla: str) -> str:
    while sigla in SUCESSORA:
        sigla = SUCESSORA[sigla]
    return sigla


def _normaliza(nome: str) -> str:
    s = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def eleitos(ano: int) -> pd.DataFrame:
    cols = ["CD_TIPO_ELEICAO", "NR_TURNO", "CD_MUNICIPIO", "CD_CARGO", "SQ_CANDIDATO",
            "NM_CANDIDATO", "SG_PARTIDO", "QT_VOTOS_NOMINAIS_VALIDOS"]
    with zipfile.ZipFile(RAW / "tse" / str(ano) / f"votacao_candidato_munzona_{ano}.zip") as z, \
            z.open(f"votacao_candidato_munzona_{ano}_BRASIL.csv") as f:
        partes = [c[(c.CD_CARGO == PREFEITO) & (c.CD_TIPO_ELEICAO == ORDINARIA)]
                  for c in pd.read_csv(f, sep=";", encoding="latin1", usecols=cols, chunksize=2_000_000)]
    v = (pd.concat(partes).groupby(["CD_MUNICIPIO", "NR_TURNO", "SQ_CANDIDATO", "NM_CANDIDATO",
                                    "SG_PARTIDO"], as_index=False).QT_VOTOS_NOMINAIS_VALIDOS.sum())
    v = v[v.NR_TURNO == v.groupby("CD_MUNICIPIO").NR_TURNO.transform("max")]   # turno decisivo
    v = v.sort_values(["CD_MUNICIPIO", "QT_VOTOS_NOMINAIS_VALIDOS"], ascending=[True, False])
    v["pos"] = v.groupby("CD_MUNICIPIO").cumcount()
    total = v.groupby("CD_MUNICIPIO").QT_VOTOS_NOMINAIS_VALIDOS.sum()
    p1 = v[v.pos == 0].set_index("CD_MUNICIPIO")
    p2 = v[v.pos == 1].set_index("CD_MUNICIPIO").QT_VOTOS_NOMINAIS_VALIDOS.reindex(p1.index).fillna(0)
    return pd.DataFrame({
        "cd_municipio_tse": p1.index, "ano": ano, "partido": p1.SG_PARTIDO.values,
        "linhagem": p1.SG_PARTIDO.map(linhagem).values,
        "pessoa": p1.NM_CANDIDATO.map(_normaliza).values,
        "margem": ((p1.QT_VOTOS_NOMINAIS_VALIDOS - p2) / total.reindex(p1.index)).values})


def continuidade() -> pd.DataFrame:
    e = pd.concat([eleitos(a) for a in ANOS]).pivot(index="cd_municipio_tse", columns="ano")
    out = pd.DataFrame(index=e.index)
    for a, b in [(2016, 2020), (2020, 2024)]:
        ok = e.linhagem[[a, b]].notna().all(axis=1)
        out[f"mesmo_partido_{a}_{b}"] = (e.linhagem[a] == e.linhagem[b]).where(ok)
        out[f"mesma_pessoa_{a}_{b}"] = (e.pessoa[a] == e.pessoa[b]).where(ok)
    for a in ANOS:
        out[f"margem_{a}"] = e.margem[a]
        out[f"linhagem_{a}"] = e.linhagem[a]
    out["continuidade_partidaria"] = out[["mesmo_partido_2016_2020", "mesmo_partido_2020_2024"]].astype(
        float).sum(axis=1, min_count=2)
    return out.reset_index()


if __name__ == "__main__":
    c = continuidade()
    c.to_parquet(PROCESSED / "prefeitos.parquet", index=False)
    print(c.shape)
    print(c.filter(like="mesm").astype(float).mean().round(3))
    print(c.continuidade_partidaria.value_counts(dropna=False).sort_index())
    siglas = sorted(set(c.filter(like="linhagem_").stack().dropna()))
    print("linhagens:", siglas)
