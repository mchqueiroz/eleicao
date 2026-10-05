"""Covariáveis municipais do Censo (API SIDRA v3 do IBGE).

Cada indicador é uma consulta declarada em CONSULTAS: (tabela, variável, {classificação: [categorias]}).
Com uma categoria por classificação, o valor é lido direto; com duas, a primeira é o numerador
(pode ser uma lista, somada) e a segunda o denominador (razão × 100).
Respostas brutas ficam em data/raw/ibge/sidra/.
"""
import json
import time
import urllib.request

import pandas as pd

from geovoto import PROCESSED, RAW

API = "https://servicodados.ibge.gov.br/api/v3/agregados"
CACHE = RAW / "ibge" / "sidra"
TOT = {"2": [6794], "86": [95251], "58": [95253], "2661": [32776], "1": [6795]}  # categorias "Total"

# Dimensões do eixo 4. Fonte: catálogo /api/v3/agregados (Censo 2022), conferido nos metadados.
CONSULTAS_2022 = {
    # econômica
    "renda_pc_media":       (10295, 13431, {"2": TOT["2"], "86": TOT["86"], "58": TOT["58"]}),
    "renda_pc_mediana":     (10295, 13534, {"2": TOT["2"], "86": TOT["86"], "58": TOT["58"]}),
    "pct_renda_outras_fontes": (10297, 13504, {"11308": [79452]}),   # aposentadorias, transferências etc.
    "pct_ate_meio_sm":      (10296, 13604, {"386": [[9692, 9681, 9682], 9680], "2": TOT["2"], "86": TOT["86"]}),
    # educacional
    "anos_estudo_11mais":   (10062, 13285, {"58": TOT["58"], "2": TOT["2"], "86": TOT["86"]}),
    "pct_superior_25mais":  (10061, 2667, {"1568": [99713, 120704], "58": [108866], "2": TOT["2"], "86": TOT["86"]}),
    "pct_alfabetizados_15mais": (10091, 2513, {"2": TOT["2"], "58": TOT["58"], "2661": TOT["2661"], "1": TOT["1"]}),
    # religiosa
    "pct_evangelicos":      (9537, 140, {"133": [95277, 95278], "2": TOT["2"], "58": TOT["58"]}),
    "pct_catolicos":        (9537, 140, {"133": [95263, 95278], "2": TOT["2"], "58": TOT["58"]}),
    "pct_sem_religiao":     (9537, 140, {"133": [2836, 95278], "2": TOT["2"], "58": TOT["58"]}),
    # demográfica
    "idade_mediana":        (10097, 10613, {"2661": TOT["2661"], "1": TOT["1"]}),
    "pct_urbana":           (10089, 93, {"1": [1, 6795], "2": TOT["2"], "58": TOT["58"], "2661": TOT["2661"]}),
    "populacao":            (10089, 93, {"1": TOT["1"], "2": TOT["2"], "58": TOT["58"], "2661": TOT["2661"]}),
    # cor/raça
    "pct_pretos_pardos":    (9605, 93, {"86": [[2777, 2779], 95251]}),
    "pct_indigenas":        (9605, 93, {"86": [2780, 95251]}),
    # acesso
    "pct_domicilios_internet": (9936, 381, {"2072": [77585, 77584], "63": [95826], "125": [2932]}),
}


# Censo 2010 (base de 2014 e 2018): só indicadores com definição igual à de 2022.
# Nas tabelas de 2010, a categoria "Total" tem id 0. Renda municipal média não existe com a
# mesma definição; a medida comparável é a % de moradores com renda pc ≤ ½ salário mínimo.
CONSULTAS_2010 = {
    "pct_ate_meio_sm":      (3462, 1426, {"386": [[9692, 12009, 12010, 9682], 0], "86": [0], "2": [0]}),
    "pct_superior_25mais":  (3547, 1643, {"1568": [99713, 0], "2": [0]}),
    "pct_evangelicos":      (137, 93, {"133": [95277, 0]}),
    "pct_catolicos":        (137, 93, {"133": [95263, 0]}),
    "pct_sem_religiao":     (137, 93, {"133": [2836, 0]}),
    "pct_urbana":           (608, 93, {"1": [1, 0], "2": [0]}),
    "populacao":            (608, 93, {"1": [0], "2": [0]}),
    "pct_pretos_pardos":    (9605, 93, {"86": [[2777, 2779], 95251]}),
    "pct_indigenas":        (9605, 93, {"86": [2780, 95251]}),
}


def _get(url: str) -> list:
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read())
        except Exception:
            if i == 3:
                raise
            time.sleep(2**i)
    raise AssertionError("inalcançável")


def _num(v: str) -> float:
    if v == "-":            # convenção do IBGE: zero absoluto
        return 0.0
    try:
        return float(v)
    except ValueError:      # "...", "..", "X" (sigilo): não disponível
        return float("nan")


def _serie(tabela: int, var: int, cls: dict, periodo: int) -> pd.Series:
    """Uma consulta com UMA categoria por classificação → Series indexada por município."""
    c = "|".join(f"{k}[{','.join(map(str, v))}]" for k, v in cls.items())
    url = f"{API}/{tabela}/periodos/{periodo}/variaveis/{var}?localidades=N6[all]"
    url += f"&classificacao={c}" if c else ""
    nome = f"t{tabela}_v{var}_{periodo}_" + c.replace("|", "_").replace("[", "-").replace("]", "")
    arq = CACHE / f"{nome}.json"
    if not arq.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        arq.write_text(json.dumps(_get(url)))
    series = json.loads(arq.read_text())[0]["resultados"][0]["series"]
    return pd.Series({int(s["localidade"]["id"]): _num(s["serie"][str(periodo)]) for s in series})


def indicador(tabela: int, var: int, cls: dict, periodo: int) -> pd.Series:
    duplas = {k: v for k, v in cls.items() if len(v) == 2}
    if not duplas:
        return _serie(tabela, var, cls, periodo)
    (k, (num, den)), = duplas.items()
    soma = lambda cats: sum(_serie(tabela, var, {**cls, k: [c]}, periodo)
                            for c in (cats if isinstance(cats, list) else [cats]))
    return 100 * soma(num) / soma(den)


# Municípios instalados em 2013 (sem dados no Censo 2010) → município de origem.
# Paraíso das Águas saiu de Costa Rica, Água Clara e Chapadão do Sul; usa-se o principal.
ORIGEM_2010 = {1504752: 1506807,  # Mojuí dos Campos ← Santarém (PA)
               4212650: 4209409,  # Pescaria Brava ← Laguna (SC)
               4220000: 4207007,  # Balneário Rincão ← Içara (SC)
               4314548: 4302105,  # Pinto Bandeira ← Bento Gonçalves (RS)
               5006275: 5003256}  # Paraíso das Águas ← Costa Rica (MS)


def censo(consultas: dict, periodo: int) -> pd.DataFrame:
    df = pd.DataFrame({nome: indicador(*q, periodo) for nome, q in consultas.items()})
    df.index.name = "cd_municipio_ibge"
    df["imputado_origem"] = False
    if periodo == 2010:
        for novo, origem in ORIGEM_2010.items():
            df.loc[novo] = df.loc[origem]
            df.loc[novo, "imputado_origem"] = True
            if "populacao" in df:   # tamanho não se herda; usar log(aptos) do TSE
                df.loc[novo, "populacao"] = float("nan")
    return df.reset_index()


def anual(tabela: int, var: int, anos) -> pd.DataFrame:
    """Série municipal anual sem classificações (ex.: PIB 5938/37, população estimada 6579/9324)."""
    linhas = []
    for ano in anos:
        try:
            s = _serie(tabela, var, {}, ano)
        except Exception:      # ano sem dado na tabela (ex.: estimativas não saem em ano de censo)
            continue
        linhas.append(s.rename("valor").rename_axis("cd_municipio_ibge").reset_index().assign(ano=ano))
    return pd.concat(linhas, ignore_index=True)


if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    for ano, consultas in [(2010, CONSULTAS_2010), (2022, CONSULTAS_2022)]:
        df = censo(consultas, ano)
        df.to_parquet(PROCESSED / f"censo{ano}_municipio.parquet", index=False)
        print(ano, df.shape)
        print(df.describe().T[["count", "mean", "min", "max"]].round(2))
    anos = range(2010, 2027)
    pib = anual(5938, 37, anos).rename(columns={"valor": "pib_mil_reais"})
    pop = anual(6579, 9324, anos).rename(columns={"valor": "pop_estimada"})
    eco = pib.merge(pop, on=["cd_municipio_ibge", "ano"], how="outer")
    # pop_estimada falta em 2010 e 2022 (anos de censo: usar censo) e 2023 (IBGE não publicou)
    eco.to_parquet(PROCESSED / "economia_anual.parquet", index=False)
    print(eco.groupby("ano")[["pib_mil_reais", "pop_estimada"]].count().T)
