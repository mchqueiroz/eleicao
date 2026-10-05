"""Hipóteses EXPLORATÓRIAS H1, H3 e H7 (HIPOTESES.md §7): sem critério confirmatório.

Todas: MQO ponderado por aptos, efeito fixo de UF, erro-padrão agrupado por UF, regressores
padronizados (coeficiente = efeito de 1 desvio-padrão), IC90%. Afirmações valem para municípios.
- H3 voto econômico por papel: logit(parcela do candidato do partido do presidente em exercício)
  ~ Δ emprego formal, Δ PIB per capita (t−3→t−1) e Δ famílias no Bolsa Família por habitante (t−2→t).
- H1 continuidade local: |desvio do swing nacional| da parcela do vencedor de 2018 no 2º turno
  (2018→2022; em 2022 ele era o incumbente) ~ continuidade do prefeito 2016→2020, margem 2020,
  emprego público por adulto.
- H7 alienação: logit((abstenção+brancos+nulos)/aptos) ~ distância ao centro regional, nível REGIC,
  escolaridade, renda e razão aptos/adultos (proxy de cadastro desatualizado).
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

from geovoto import CONFIG, PROCESSED, ROOT
from geovoto.eixos import DIMENSOES, base
from geovoto.tse import votos_candidato

CONTROLES = sum(DIMENSOES.values(), [])
SAIDA = ROOT / "data" / "output" / "exploratorio"


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def regressao(y: pd.Series, X: pd.DataFrame, w: pd.Series, uf: pd.Series, interesse: list) -> pd.DataFrame:
    Xs = (X - X.mean()) / X.std()
    M = sm.add_constant(pd.concat([Xs, pd.get_dummies(uf, prefix="uf", drop_first=True, dtype=float)], axis=1))
    ok = y.notna() & M.notna().all(axis=1) & w.notna()
    r = sm.WLS(y[ok], M[ok], weights=w[ok]).fit(cov_type="cluster",
                                                 cov_kwds={"groups": pd.factorize(uf[ok])[0]})
    ic = r.conf_int(alpha=0.10)
    return pd.DataFrame({"variavel": interesse, "coef": r.params[interesse].values,
                         "ic90_inf": ic.loc[interesse, 0].values, "ic90_sup": ic.loc[interesse, 1].values,
                         "n": int(ok.sum())})


def parcela_candidato_partido(ano: int, turno: int, partido: str) -> pd.Series:
    v = votos_candidato(ano).query("turno == @turno")
    tot = v.groupby("cd_municipio_tse").votos.sum()
    return v[v.sg_partido == partido].groupby("cd_municipio_tse").votos.sum().reindex(tot.index, fill_value=0) / tot


def _por_tse(d: pd.DataFrame, s: pd.Series) -> pd.Series:
    return pd.Series(d.cd_municipio_tse.map(s).to_numpy(), index=d.index)


def _serie_mun(df: pd.DataFrame, col: str, ano, chave="ano") -> pd.Series:
    return df[df[chave] == ano].set_index("cd_municipio_ibge")[col]


def h3() -> pd.DataFrame:
    rais = pd.read_parquet(PROCESSED / "rais_municipio.parquet")
    eco = pd.read_parquet(PROCESSED / "economia_anual.parquet")
    bf = pd.read_parquet(PROCESSED / "bolsa_familia.parquet")
    saida = []
    for ano in (2014, 2018, 2022):
        d = base(ano)
        y = logit(_por_tse(d, parcela_candidato_partido(ano, 1, CONFIG["incumbente_partido"][str(ano)])))
        emp = lambda a: np.log1p(_serie_mun(rais, "vinculos_ativos", a))
        pibpc = lambda a: np.log(_serie_mun(eco, "pib_mil_reais", a) / _serie_mun(eco, "pop_estimada", a))
        X = pd.DataFrame({"d_log_emprego_formal": emp(ano - 1) - emp(ano - 3),
                          "d_log_pib_pc": pibpc(ano - 1) - pibpc(ano - 3)}).reindex(d.index)
        # Bolsa Família: só quando o MESMO campo existe nas duas pontas (quebra de série em 2022)
        a, b = bf[bf.anomes == f"{ano - 2}10"], bf[bf.anomes == f"{ano}10"]
        if a.familias_bf_antigo.notna().any() and b.familias_bf_antigo.notna().any():
            pop = _serie_mun(eco, "pop_estimada", ano)
            fam = lambda t: t.set_index("cd_municipio_ibge").familias_bf_antigo.astype(float)
            X["d_familias_bf_por_hab"] = ((fam(b) - fam(a)) / pop).reindex(d.index)
        interesse = list(X.columns)
        X = X.join(d[CONTROLES])
        saida.append(regressao(y, X, d.aptos.astype(float), d.uf, interesse).assign(hipotese="H3", ano=ano))
    return pd.concat(saida)


def h1() -> pd.DataFrame:
    d = base(2022)
    v18 = votos_candidato(2018).query("turno == 2")
    vencedor = v18.groupby("sg_partido").votos.sum().idxmax()     # vencedor de 2018 = incumbente em 2022
    s18 = parcela_candidato_partido(2018, 2, vencedor)
    s22 = parcela_candidato_partido(2022, 2, CONFIG["incumbente_partido"]["2022"])
    delta = _por_tse(d, logit(s22) - logit(s18))
    y = (delta - np.average(delta, weights=d.aptos)).abs()
    pref = pd.read_parquet(PROCESSED / "prefeitos.parquet").set_index("cd_municipio_tse")
    rais = pd.read_parquet(PROCESSED / "rais_municipio.parquet")
    adultos = pd.read_parquet(PROCESSED / "pop_18mais.parquet").set_index("cd_municipio_ibge").pop_18mais_2022
    X = pd.DataFrame({
        "mesmo_partido_2016_2020": _por_tse(d, pref.mesmo_partido_2016_2020.astype(float)),
        "mesma_pessoa_2016_2020": _por_tse(d, pref.mesma_pessoa_2016_2020.astype(float)),
        "margem_prefeito_2020": _por_tse(d, pref.margem_2020),
        "emprego_publico_por_adulto": (_serie_mun(rais, "vinculos_publicos", 2020) / adultos).reindex(d.index)})
    interesse = list(X.columns)
    X = X.join(d[CONTROLES])
    return regressao(y, X, d.aptos.astype(float), d.uf, interesse).assign(hipotese="H1", ano=2022)


def adultos_no_ano(ano: int) -> pd.Series:
    """Adultos em `ano` ≈ população estimada × fração 18+ do censo mais próximo (2022: censo direto)."""
    pop18 = pd.read_parquet(PROCESSED / "pop_18mais.parquet").set_index("cd_municipio_ibge")
    if ano == 2022:
        return pop18.pop_18mais_2022
    censo = pd.read_parquet(PROCESSED / "censo2010_municipio.parquet").set_index("cd_municipio_ibge")
    eco = pd.read_parquet(PROCESSED / "economia_anual.parquet")
    return _serie_mun(eco, "pop_estimada", ano) * (pop18.pop_18mais_2010 / censo.populacao)


def h7() -> tuple[pd.DataFrame, pd.DataFrame]:
    regic = pd.read_parquet(PROCESSED / "acesso_regic.parquet").set_index("cd_municipio_ibge")
    saida, desc = [], []
    for ano in (2014, 2018, 2022):
        d = base(ano)
        alien = (d.abstencoes + d.brancos + d.nulos) / d.aptos
        razao = d.aptos / adultos_no_ano(ano).reindex(d.index)
        X = pd.DataFrame({"log_dist_centro_regional": np.log1p(regic.dist_km_centro_regional),
                          "nivel_regic": regic.nivel_regic.astype(float)}).reindex(d.index)
        X["razao_aptos_adultos"] = razao
        interesse = list(X.columns) + ["pct_superior_25mais", "pct_ate_meio_sm"]
        X = X.join(d[CONTROLES])
        saida.append(regressao(logit(alien), X, d.aptos.astype(float), d.uf, interesse).assign(hipotese="H7", ano=ano))
        desc.append({"ano": ano, "alienacao_nacional": float((d.abstencoes + d.brancos + d.nulos).sum() / d.aptos.sum()),
                     "municipios_aptos_maior_que_adultos": int((razao > 1).sum()),
                     "razao_aptos_adultos_mediana": float(razao.median())})
    return pd.concat(saida), pd.DataFrame(desc)


def relatorio(coefs: pd.DataFrame, desc_h7: pd.DataFrame) -> str:
    fmt = lambda r: f"| {r.ano} | {r.variavel} | {r.coef:+.3f} | [{r.ic90_inf:+.3f}, {r.ic90_sup:+.3f}] | {r.n} |"
    partes = ["# Análises exploratórias (H1, H3, H7)\n",
              "> **EXPLORATÓRIO.** Sem critério confirmatório; servem para gerar hipóteses. Coeficientes = "
              "efeito de 1 desvio-padrão do regressor, MQO ponderado por aptos, efeito fixo de UF, "
              "erro agrupado por UF (27 grupos), IC90%. Afirmações valem para municípios, não para eleitores.\n"]
    titulos = {"H3": "H3 Voto econômico por papel (desfecho: logit da parcela do candidato do partido do presidente em exercício)",
               "H1": "H1 Continuidade local (desfecho: |desvio do swing nacional| 2018→2022, 2º turno)",
               "H7": "H7 Alienação (desfecho: logit de (abstenção + brancos + nulos)/aptos)"}
    for h, t in titulos.items():
        partes += [f"## {t}\n", "| Ano | Variável | Coef. | IC90% | n |", "|---|---|---|---|---|"]
        partes += [fmt(r) for r in coefs[coefs.hipotese == h].itertuples()] + [""]
    partes += ["### H7: descritivo do cadastro\n",
               "| Ano | Alienação nacional | Municípios com aptos > adultos | Razão aptos/adultos (mediana) |",
               "|---|---|---|---|"]
    partes += [f"| {r.ano} | {r.alienacao_nacional:.3f} | {r.municipios_aptos_maior_que_adultos} | "
               f"{r.razao_aptos_adultos_mediana:.3f} |" for r in desc_h7.itertuples()] + [""]
    partes += ["## Limitações\n",
               "- H3: o papel de incumbente troca de lado entre anos, então os coeficientes não se somam entre eleições; "
               "o candidato do partido do presidente em 2018 teve votação marginal (estimativa frágil). "
               "Bolsa Família fica fora de 2022 por quebra de série (Auxílio Brasil).",
               "- H1: uma janela só (2018→2022); continuidade e estabilidade podem ter causa comum.",
               "- H7: a razão aptos/adultos usa população estimada × fração 18+ do censo mais próximo; "
               "aptos inclui eleitores de 16–17 anos (facultativos), então razão > 1 não prova cadastro inflado sozinha."]
    return "\n".join(partes) + "\n"


if __name__ == "__main__":
    SAIDA.mkdir(parents=True, exist_ok=True)
    c7, d7 = h7()
    coefs = pd.concat([h3(), h1(), c7], ignore_index=True)
    coefs.to_csv(SAIDA / "coeficientes.csv", index=False)
    (SAIDA / "relatorio.md").write_text(relatorio(coefs, d7))
    print(relatorio(coefs, d7))
