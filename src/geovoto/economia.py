"""Séries econômicas municipais para as hipóteses EXPLORATÓRIAS (H1, H3).

RAIS (estabelecimentos): vínculos formais ativos em 31/12, públicos (natureza jurídica 1xxx)
e agropecuários (CNAE divisões 01–03), anos pares 2012–2024.
Bolsa Família (MI Social/MDS): famílias beneficiárias no mês de outubro. A série tem quebra:
o campo antigo vai até 2020 e reaparece em 2024; o campo novo cobre 2022 (Auxílio Brasil) e 2024,
com valores diferentes do antigo. Variações devem usar o MESMO campo nas duas pontas.
"""
import json
import subprocess

import pandas as pd

from geovoto import PROCESSED, RAW, http_get

ANOS_RAIS = list(range(2011, 2025))   # anos ímpares: janelas (t−3, t−1) da H3; pares: H1
MESES_BF = [f"{a}10" for a in range(2012, 2026, 2)] + ["202509"]
MISOCIAL = "https://aplicacoes.mds.gov.br/sagi/servicos/misocial/"
CAMPOS_BF = {"qtd_familias_beneficiarias_bolsa_familia_i": "familias_bf_antigo",
             "pbf_qtd_familias_benef_i": "familias_bf_novo"}


def _cod7(cod6: pd.Series) -> pd.Series:
    bd = pd.read_csv(RAW / "bd" / "municipio.csv.gz", usecols=["id_municipio", "id_municipio_6"])
    extra = pd.Series({510183: 5101837})          # Boa Esperança do Norte (fora do diretório BD)
    mapa = pd.concat([bd.set_index("id_municipio_6").id_municipio, extra])
    return cod6.astype(int).map(mapa)


# prefixo do nome da coluna → nome canônico (2012–2022: "Município"; 2024: "Município - Código")
COLS_RAIS = {"Município": "mun", "Natureza Jurídica": "nat", "CNAE 2.0 Subclasse": "cnae",
             "Qtd Vínculos Ativos": "vinc"}


def _abrir_7z(arq):
    return subprocess.Popen(["7z", "e", "-so", str(arq)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


def rais(ano: int) -> pd.DataFrame:
    arq = RAW / "rais" / str(ano) / "estab.7z"
    p = _abrir_7z(arq)                                   # só o cabeçalho, para detectar o layout
    cab = p.stdout.readline().decode("latin1").strip()
    p.kill()
    sep = "," if cab.startswith('"') else ";"
    nomes = [c.strip('"') for c in cab.split(sep)]
    usar = {n: canon for n in nomes for pref, canon in COLS_RAIS.items() if n.startswith(pref)}
    assert sorted(usar.values()) == sorted(COLS_RAIS.values()), (ano, nomes)
    proc = _abrir_7z(arq)
    partes = []
    for ch in pd.read_csv(proc.stdout, sep=sep, encoding="latin1", usecols=list(usar), dtype=str,
                          chunksize=2_000_000):
        ch = ch.rename(columns=usar)
        v = pd.to_numeric(ch.vinc, errors="coerce").fillna(0)
        nat = ch.nat.str.strip()
        cnae = ch.cnae.str.strip().str.zfill(7)          # subclasse CNAE 2.0, 7 dígitos
        partes.append(pd.DataFrame({
            "mun": ch.mun.str.strip(), "vinculos_ativos": v,
            "vinculos_publicos": v.where(nat.str.startswith("1"), 0),
            "vinculos_agro": v.where(cnae.str[:2].isin(["01", "02", "03"]), 0),
        }).groupby("mun").sum())
    if proc.wait() != 0:
        raise RuntimeError(f"7z falhou em {arq}")
    df = pd.concat(partes).groupby(level=0).sum().reset_index()
    df = df[df.mun.str.fullmatch(r"\d{6}")]            # descarta "ignorado" e códigos inválidos
    return df.assign(cd_municipio_ibge=_cod7(df.mun), ano=ano).drop(columns="mun").dropna(
        subset=["cd_municipio_ibge"]).astype({"cd_municipio_ibge": int})


def bolsa_familia(anomes: str) -> pd.DataFrame:
    arq = RAW / "mds" / f"misocial_{anomes}.json"
    if not arq.exists():
        url = (f"{MISOCIAL}?q=*:*&fq=anomes_s:{anomes}&rows=6000&wt=json"
               f"&fl=codigo_ibge,anomes_s,{','.join(CAMPOS_BF)}")
        dados = json.loads(http_get(url, timeout=120))["response"]["docs"]
        if not dados:
            raise ValueError(f"MI Social sem dados para {anomes}")
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(json.dumps(dados))
    df = pd.DataFrame(json.loads(arq.read_text())).rename(columns=CAMPOS_BF)
    for c in CAMPOS_BF.values():
        if c not in df:
            df[c] = pd.NA
    return pd.DataFrame({"cd_municipio_ibge": _cod7(df.codigo_ibge), "anomes": anomes,
                         **{c: df[c] for c in CAMPOS_BF.values()}})


if __name__ == "__main__":
    r = pd.concat([rais(a) for a in ANOS_RAIS], ignore_index=True)
    r.to_parquet(PROCESSED / "rais_municipio.parquet", index=False)
    print(r.groupby("ano")[["vinculos_ativos", "vinculos_publicos", "vinculos_agro"]].sum().astype(int))
    print("municípios por ano:", r.groupby("ano").size().to_dict())
    b = pd.concat([bolsa_familia(m) for m in MESES_BF], ignore_index=True)
    b.to_parquet(PROCESSED / "bolsa_familia.parquet", index=False)
    print(b.groupby("anomes")[list(CAMPOS_BF.values())].agg(["count", "sum"]))
