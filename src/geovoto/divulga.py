"""Snapshot dos resultados PROVISÓRIOS de 2026 (sistema de divulgação do TSE).

Uso só para a previsão do 2º turno. O artigo usa os arquivos finais (geovoto.tse).
Cada execução grava um snapshot imutável em data/raw/tse/2026/divulga/<timestamp>/.
"""
import hashlib
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd

from geovoto import PROCESSED, RAW

BASE = "https://resultados.tse.jus.br/oficial/ele2026"
ELEICAO = {1: "6257", 2: "6258"}  # presidente, 1º e 2º turno (de comum/config/ele-c.json)
DIR = RAW / "tse" / "2026" / "divulga"


def _get(url: str, tentativas: int = 4) -> bytes:
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "geovoto (pesquisa academica)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception:
            if i == tentativas - 1:
                raise
            time.sleep(2**i)
    raise AssertionError("inalcançável")


def municipios(turno: int = 1) -> pd.DataFrame:
    e = ELEICAO[turno]
    cfg = json.loads(_get(f"{BASE}/{e}/config/mun-e{int(e):06d}-cm.json"))
    linhas = [(u["cd"], int(m["cd"]), int(m["cdi"]), m["nm"])
              for u in cfg["abr"] if u["cd"].lower() != "zz" for m in u["mu"]]
    return pd.DataFrame(linhas, columns=["uf", "cd_municipio_tse", "cd_municipio_ibge", "nome"])


def snapshot(turno: int = 1) -> Path:
    e = ELEICAO[turno]
    mun = municipios(turno)
    destino = DIR / f"t{turno}_{datetime.now():%Y%m%dT%H%M%S}"
    destino.mkdir(parents=True)
    mun.to_csv(destino / "municipios.csv", index=False)

    def baixar(row) -> str:
        nome = f"{row.uf}{row.cd_municipio_tse:05d}-c0001-e{int(e):06d}-u.json"
        conteudo = _get(f"{BASE}/{e}/dados/{row.uf}/{nome}")
        (destino / nome).write_bytes(conteudo)
        return f"{hashlib.sha256(conteudo).hexdigest()}  {nome}"

    with ThreadPoolExecutor(8) as ex:  # ponytail: 8 conexões; suficiente para ~5,6 mil arquivos pequenos
        hashes = list(ex.map(baixar, mun.itertuples()))
    (destino / "SHA256SUMS").write_text("\n".join(sorted(hashes)) + "\n")
    return destino


def _num(x) -> int:
    return int(str(x).replace(".", "") or 0)


def ler(destino: Path, turno: int = 1) -> tuple[pd.DataFrame, pd.DataFrame]:
    mun = pd.read_csv(destino / "municipios.csv")
    linhas, votos = [], []
    for f in sorted(destino.glob("*-u.json")):
        d = json.loads(f.read_bytes())
        cd = int(d["cdabr"])
        linhas.append({
            "cd_municipio_tse": cd, "pct_totalizado": float(d["s"]["pst"].replace(",", ".")),
            "aptos": _num(d["e"]["te"]), "aptos_apurados": _num(d["e"]["est"]),  # c + a = est
            "comparecimento": _num(d["e"]["c"]),
            "abstencoes": _num(d["e"]["a"]), "validos": _num(d["v"]["vv"]),
            "brancos": _num(d["v"]["vb"]), "nulos": _num(d["v"]["tvn"]),
            "snapshot": f'{d["dg"]} {d["hg"]}'})
        for agr in d["carg"][0]["agr"]:
            for par in agr["par"]:
                for c in par["cand"]:
                    votos.append((cd, int(c["n"]), _num(c["vap"])))
    df = pd.DataFrame(linhas).merge(mun[["cd_municipio_tse", "cd_municipio_ibge", "uf"]],
                                    on="cd_municipio_tse", how="left")
    v = pd.DataFrame(votos, columns=["cd_municipio_tse", "nr_candidato", "votos"])
    return df.assign(ano=2026, turno=turno, provisorio=True), v


def painel(destino: Path, turno: int = 1) -> pd.DataFrame:
    df, v = ler(destino, turno)
    ordem = v.groupby("nr_candidato").votos.sum().sort_values(ascending=False)
    bloco = {ordem.index[0]: "A", ordem.index[1]: "B"}  # posicional; nomes não entram no painel
    ab = (v.assign(bloco=v.nr_candidato.map(bloco)).dropna(subset=["bloco"])
            .pivot_table(index="cd_municipio_tse", columns="bloco", values="votos", aggfunc="sum")
            .rename(columns={"A": "votos_A", "B": "votos_B"}).reset_index())
    p = v.votos / v.groupby("cd_municipio_tse").votos.transform("sum")
    nec = (1 / (p**2).groupby(v.cd_municipio_tse).sum()).rename("nec").reset_index()
    out = df.merge(ab, on="cd_municipio_tse", how="left").merge(nec, on="cd_municipio_tse", how="left")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PROCESSED / f"painel_2026_t{turno}_provisorio.parquet", index=False)
    return out


if __name__ == "__main__":
    turno = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    destino = snapshot(turno)
    out = painel(destino, turno)
    print(f"snapshot: {destino}")
    print(out[["aptos", "comparecimento", "validos", "votos_A", "votos_B"]].sum())
    print("municípios:", len(out), "| % totalizado mínimo:", out.pct_totalizado.min())
