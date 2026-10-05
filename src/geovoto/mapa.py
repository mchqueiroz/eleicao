"""Dados do mapa público: só métricas invariantes ao lado (|margem|, abstenção, NEC).

Gera reports/mapa/municipios.geojson (malha 2025 simplificada) e reports/mapa/metricas.json
{ano: {turno: {cd_ibge: [margem_abs, abstencao, nec]}}}. 2026 entra como provisório.
"""
import json

import pandas as pd
import shapely

from geovoto import PROCESSED, ROOT
from geovoto.espacial import malha

SAIDA = ROOT / "reports" / "mapa"
TOLERANCIA_GRAUS = 0.01   # ~1 km; mantém a topologia e deixa o arquivo em poucos MB


def metricas(p: pd.DataFrame) -> dict:
    p = p[p.validos > 0]
    vals = pd.DataFrame({
        "margem_abs": ((p.votos_A - p.votos_B).abs() / p.validos).round(4),
        "abstencao": (p.abstencoes / p.get("aptos_apurados", p.aptos)).round(4),
        "nec": p.nec.round(2)}).set_index(p.cd_municipio_ibge.astype(int))
    return {str(k): v for k, v in vals.T.to_dict("list").items()}


def construir() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    g = malha().to_crs(4326).reset_index()
    geom = g.geometry.simplify(TOLERANCIA_GRAUS, preserve_topology=True)
    g["geometry"] = shapely.set_precision(geom.values, 0.001)
    g = g.rename(columns={"cd_municipio_ibge": "id", "nome": "n"})[["id", "n", "uf", "geometry"]]
    (SAIDA / "municipios.geojson").write_text(g.to_json(drop_id=True))
    painel = pd.read_parquet(PROCESSED / "painel_presidente.parquet")
    out = {str(a): {str(t): metricas(painel[(painel.ano == a) & (painel.turno == t)])
                    for t in (1, 2)} for a in sorted(painel.ano.unique())}
    prov = PROCESSED / "painel_2026_t1_provisorio.parquet"
    if prov.exists():
        p26 = pd.read_parquet(prov)
        out["2026"] = {"1": metricas(p26), "provisorio_ate": str(p26.snapshot.max())}
    (SAIDA / "metricas.json").write_text(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    construir()
    for f in SAIDA.glob("*.json*"):
        print(f.name, f"{f.stat().st_size / 1e6:.1f} MB")
