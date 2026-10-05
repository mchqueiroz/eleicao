"""Saídas públicas não podem conter siglas de partidos nem nomes de urna de candidatos."""
import json
import re

import pandas as pd
import pytest

from geovoto import PROCESSED, RAW, ROOT

PUBLICAS = [*ROOT.glob("reports/mapa/*"), *ROOT.glob("reports/previsao_2T_2026/*"), *ROOT.glob("reports/*.md"),
            *ROOT.glob("data/output/exploratorio/*")]


def _proibidos() -> set:
    termos = set()
    cand = PROCESSED / "candidatos_presidente.parquet"
    if cand.exists():
        termos |= set(pd.read_parquet(cand).sg_partido)
    snaps = sorted((RAW / "tse" / "2026" / "divulga").glob("t1_*"))
    if snaps:
        j = json.loads(next(snaps[-1].glob("*-u.json")).read_text())
        for agr in j["carg"][0]["agr"]:
            for par in agr["par"]:
                termos.add(par["sg"])
                termos |= {c["nmu"] for c in par["cand"]}
    return {t for t in termos if t and len(t) >= 2}


@pytest.mark.skipif(not PUBLICAS, reason="sem saídas públicas geradas")
def test_saidas_publicas_sem_partidos_nem_candidatos():
    proibidos = _proibidos()
    if not proibidos:
        pytest.skip("sem lista de partidos/candidatos (dados ausentes)")
    padrao = re.compile(r"(?<![\wÀ-ÿ])(" + "|".join(map(re.escape, sorted(proibidos, key=len, reverse=True))) + r")(?![\wÀ-ÿ])")
    achados = {}
    for f in PUBLICAS:
        if f.suffix in {".geojson"}:            # só nomes de municípios
            continue
        m = padrao.findall(f.read_text(errors="ignore"))
        if m:
            achados[f.name] = sorted(set(m))[:5]
    assert not achados, achados
