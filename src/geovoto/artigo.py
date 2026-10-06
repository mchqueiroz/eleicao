"""Gera as tabelas e macros LaTeX do artigo a partir de data/output (nenhum número digitado à mão).

Saída em paper/gerado/: macros.tex (\\newcommand com os números citados no texto) e tab_*.tex.
Rodar com `make paper`, que também compila paper/artigo.tex.
"""
import json

import numpy as np

import pandas as pd

from geovoto import ROOT
from geovoto.veredito import _ic, veredito

SAIDA = ROOT / "paper" / "gerado"
ALVOS = {"yA": "A", "yB": "B", "votos_A": "A", "votos_B": "B"}
DIMS = {"economica": "Econômica", "educacional": "Educacional", "religiosa": "Religiosa",
        "demografica": "Demográfica", "cor_raca": "Cor/raça"}


def num(x, casas=3, sinal=False) -> str:
    return "" if x is None else f"{x:{'+' if sinal else ''}.{casas}f}".replace(".", "{,}")


def tabela(cabecalho: list[str], linhas: list[list[str]], alinhamento: str) -> str:
    corpo = "\n".join(" & ".join(l) + r" \\" for l in linhas)
    return (f"\\begin{{tabular}}{{{alinhamento}}}\n\\toprule\n{' & '.join(cabecalho)} \\\\\n\\midrule\n"
            f"{corpo}\n\\bottomrule\n\\end{{tabular}}\n")


def rotulo(s: str) -> str:
    return (s.replace("Δ", r"$\Delta$").replace("(yA)", "(bloco A)").replace("(yB)", "(bloco B)")
             .replace("yA", "A").replace("yB", "B"))


def tab_veredito(v: dict) -> str:
    linhas = [[rotulo(k), rotulo(t[0]), num(t[1], sinal=True), num(t[2], sinal=True), num(t[3], sinal=True)]
              for k, t in v.items()]
    return tabela(["Tese", "Veredito", "Estimativa", "IC90\\% inf.", "IC90\\% sup."], linhas, "llrrr")


def tab_eixo1(r: dict) -> str:
    linhas = []
    for a in sorted(r):
        for alvo in ("yA", "yB"):
            e = r[a]["eixo1"][alvo]
            linhas.append([str(a), ALVOS[alvo]] + [num(e["shapley"][k]) for k in ("estrutura", "vizinhanca", "territorio")]
                          + [num(e["compartilhado"]), num(e["total"])])
    return tabela(["Ano", "Bloco", "Estrutura", "Vizinhança", "UF", "Compartilhado", "$R^2_{aj}$"], linhas, "llrrrrr")


def tab_fronteira(r: dict) -> str:
    linhas = []
    for a in sorted(r):
        cel = []
        for k in ("real", "placebo"):
            est, lo, hi = _ic([x[k] for x in r[a]["fronteira_boot"]])
            cel += [num(est, 2), f"[{num(lo, 2)}; {num(hi, 2)}]"]
        linhas.append([str(a)] + cel)
    return tabela(["Ano", "Divisas reais", "IC90\\%", "Placebo", "IC90\\%"], linhas, "lrcrc")


def tab_eixo2(r: dict) -> str:
    ks = ("parcela_uf", "parcela_municipio", "parcela_local", "var_total")
    linhas = [[str(a)] + [num(r[a]["eixo2"][k]) for k in ks] for a in sorted(r)]
    return tabela(["Ano", "UF", "Município", "Local de votação", "Variância total"], linhas, "lrrrr")


def tab_eixo3(r: dict) -> str:
    ks = ("isolamento_A", "isolamento_B", "exposicao_A_B", "exposicao_B_A")
    linhas = [[str(a), rot] + [num(r[a]["eixo3"][esc][k]) for k in ks]
              for a in sorted(r) for esc, rot in (("municipio", "Município"), ("local", "Local"))]
    return tabela(["Ano", "Escala", "Isol. A", "Isol. B", "Expos. A$\\to$B", "Expos. B$\\to$A"], linhas, "llrrrr")


def tab_eixo4(r: dict) -> str:
    linhas = [[str(a), ALVOS[alvo]] + [num(r[a]["eixo4"][alvo]["unicos"][d]) for d in DIMS]
              + [num(r[a]["eixo4"][alvo]["compartilhado"])] for a in sorted(r) for alvo in ("yA", "yB")]
    return tabela(["Ano", "Bloco"] + list(DIMS.values()) + ["Compart."], linhas, "ll" + "r" * (len(DIMS) + 1))


def tab_bym2() -> str | None:
    fs = sorted((ROOT / "data" / "output" / "bym2").glob("diagnosticos_*.csv"))
    if not fs:
        return None
    linhas = [[str(x.ano), ALVOS.get(x.alvo, x.alvo), num(x.rhat_max), f"{x.ess_min:.0f}", str(x.divergencias)]
              for x in pd.concat(map(pd.read_csv, fs)).itertuples()]
    return tabela(["Ano", "Bloco", "$\\hat R$ máx.", "ESS mín.", "Divergências"], linhas, "llrrr")


def macros(r: dict, v: dict, bym2: bool) -> str:
    anos = sorted(r)
    t2, plac = v["T2 território (salto corrigido, p.p.)"], v["T2 placebo (validação)"]
    m = {
        "anosAnalise": ", ".join(map(str, anos)), "anoIni": anos[0], "anoFim": anos[-1],
        "nAutovetores": r[anos[-1]]["n_autovetores_mesf"],
        "tUmA": num(v["T1 estruturação (yA)"][1] * 100, 1, True),
        "tUmB": num(v["T1 estruturação (yB)"][1] * 100, 1, True),
        "tDoisSalto": num(t2[1], 1), "tDoisLo": num(t2[2], 1), "tDoisHi": num(t2[3], 1),
        "tDoisPlacebo": num(plac[1], 1), "tDoisPlaceboLo": num(plac[2], 1), "tDoisPlaceboHi": num(plac[3], 1),
        "tDoisVeredito": t2[0], "tDoisValidacao": plac[0],
        "eDoisEntre": num(v["Eixo 2 entre lugares (Δ parcela)"][1] * 100, 1, True),
        "eDoisDentro": num(v["Eixo 2 dentro dos lugares (Δ parcela)"][1] * 100, 1, True),
        "eTresA": num(v["Eixo 3 Δ isolamento A (local)"][1], 3, True),
        "eTresB": num(v["Eixo 3 Δ isolamento B (local)"][1], 3, True),
        "tQuatroA": v["T4 (yA)"][0], "tQuatroB": v["T4 (yB)"][0],
        "tUmVA": v["T1 estruturação (yA)"][0], "tUmVB": v["T1 estruturação (yB)"][0],
        "eDoisVEntre": v["Eixo 2 entre lugares (Δ parcela)"][0],
        "eDoisVDentro": v["Eixo 2 dentro dos lugares (Δ parcela)"][0],
        "eTresV": v["Eixo 3 veredito"][0],
    }
    linhas = [f"\\newcommand{{\\{k}}}{{{x}}}" for k, x in m.items()]
    linhas.append(f"\\newif\\ifparcial\\parcial{'true' if anos[-1] < 2026 else 'false'}")
    linhas.append(f"\\newif\\ifplacebook\\placebook{'true' if plac[0] == 'ok' else 'false'}")
    linhas.append(f"\\newif\\ifbymdois\\bymdois{'true' if bym2 else 'false'}")
    return "\n".join(linhas) + "\n"


def dados_exploratorios(r: dict) -> str:
    """\\dado{chave} para os números das análises exploratórias (geovoto.teses_extra), por ano."""
    from geovoto.teses_extra import campo_pt
    f = ROOT / "data" / "output" / "exploratorio_teses" / "resultados.json"
    x = {int(a): v for a, v in json.loads(f.read_text()).items()} if f.exists() else {}
    d = {}
    med = lambda reps: float(np.median(reps))
    for a in sorted(r):
        pt = campo_pt(a)
        lados = {"PT": f"y{pt}", "Adv": f"y{'B' if pt == 'A' else 'A'}"}
        for lado, alvo in lados.items():
            boot = r[a]["eixo1_4_boot"]
            for k, rot in (("estrutura", "est"), ("territorio", "uf")):
                d[f"{rot}{lado}{a}"] = num(med([b["eixo1"][alvo]["shapley"][k] for b in boot]), 2)
            for k, rot in (("religiosa", "rel"), ("economica", "renda"), ("educacional", "educ")):
                d[f"{rot}{lado}{a}"] = num(med([b["eixo4"][alvo]["unicos"][k] for b in boot]), 3)
        d[f"real{a}"] = num(r[a]["fronteira_pp"]["real"], 1)
        if a in x:
            pl = np.array(x[a]["placebos_aleatorios"])
            d[f"plMed{a}"], d[f"plMax{a}"] = num(np.median(pl), 1), num(pl.max(), 1)
            d[f"plAcima{a}"] = str(int((pl >= r[a]["fronteira_pp"]["real"]).sum()))
            for c, rot in (("pct_evangelicos", "ev"), ("pct_catolicos", "cat"), ("pct_sem_religiao", "sem"),
                           ("pct_ate_meio_sm", "pobre"), ("pct_superior_25mais", "sup")):
                d[f"{rot}{a}"] = num(x[a]["coeficientes"][c], 2, True)
    fc = ROOT / "data" / "output" / "exploratorio_teses" / "censo2010_em_2022.json"
    if fc.exists():
        for lado, v in json.loads(fc.read_text()).items():
            for k, rot in (("religiosa", "rel"), ("economica", "renda")):
                b = [x[k] for x in v["unicos_boot"]]
                d[f"{rot}{lado}Censo"] = num(med(b), 3)
                d[f"{rot}{lado}CensoLo"], d[f"{rot}{lado}CensoHi"] = (num(q, 3) for q in np.percentile(b, [5, 95]))
    d["nPlacebos"] = str(len(next(iter(x.values()))["placebos_aleatorios"])) if x else "0"
    linhas = ["\\newcommand{\\dado}[1]{\\ifcsname dado@#1\\endcsname\\csname dado@#1\\endcsname"
              "\\else\\textcolor{red}{??#1}\\fi}"]
    linhas += [f"\\expandafter\\def\\csname dado@{k}\\endcsname{{{v}}}" for k, v in d.items()]
    linhas.append(f"\\newif\\ifexploratorio\\exploratorio{'true' if x else 'false'}")
    return "\n".join(linhas) + "\n"


def gerar() -> None:
    r = json.loads((ROOT / "data" / "output" / "eixos" / "resultados.json").read_text())
    r = {int(a): x for a, x in r.items() if not str(a).startswith("_")}
    v, bym2 = veredito(r), tab_bym2()
    SAIDA.mkdir(parents=True, exist_ok=True)
    arquivos = {"macros": macros(r, v, bym2 is not None) + dados_exploratorios(r), "tab_veredito": tab_veredito(v),
                "tab_eixo1": tab_eixo1(r), "tab_fronteira": tab_fronteira(r), "tab_eixo2": tab_eixo2(r),
                "tab_eixo3": tab_eixo3(r), "tab_eixo4": tab_eixo4(r), "tab_bym2": bym2 or "% BYM2 ainda não rodou\n"}
    for nome, txt in arquivos.items():
        (SAIDA / f"{nome}.tex").write_text(txt)
    print(f"{len(arquivos)} arquivos em {SAIDA}")


if __name__ == "__main__":
    assert num(0.1234) == "0{,}123" and num(-1.0, 1, True) == "-1{,}0"
    gerar()
