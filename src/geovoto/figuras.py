"""Figuras do artigo (paper/figuras/*.pdf), geradas de data/output. Rodar via `make paper`.

Séries alinhadas por campo (PT × adversário; ver geovoto.teses_extra). Paleta categórica e
divergente validadas (skill dataviz); identidade nunca só por cor: rótulos diretos e marcadores.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from geovoto import ROOT
from geovoto.teses_extra import campo_pt

SAIDA = ROOT / "paper" / "figuras"
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MARC = ["o", "s", "^", "D", "v"]
TINTA, TINTA2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"
DIMS = {"economica": "Renda", "educacional": "Escolaridade", "religiosa": "Religião",
        "demografica": "Demografia", "cor_raca": "Cor/raça"}
BLOCOS = {"estrutura": "Estrutura social", "vizinhanca": "Vizinhança", "territorio": "UF"}
COVS = {"pct_ate_meio_sm": "% renda ≤ ½ SM", "pct_superior_25mais": "% superior completo",
        "pct_evangelicos": "% evangélicos", "pct_catolicos": "% católicos", "pct_sem_religiao": "% sem religião",
        "pct_urbana": "% urbana", "log_aptos": "log eleitorado", "pct_pretos_pardos": "% pretos e pardos",
        "pct_indigenas": "% indígenas"}

plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA,
                     "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": GRADE,
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "lines.linewidth": 2,
                     "pdf.fonttype": 42, "font.family": "DejaVu Sans"})


def _carregar():
    r = json.loads((ROOT / "data" / "output" / "eixos" / "resultados.json").read_text())
    r = {int(a): x for a, x in r.items() if not a.startswith("_")}
    f = ROOT / "data" / "output" / "exploratorio_teses" / "resultados.json"
    x = {int(a): v for a, v in json.loads(f.read_text()).items()} if f.exists() else None
    return r, x


def _alvo(ano: int, lado: str) -> str:
    pt = campo_pt(ano)
    return f"y{pt}" if lado == "PT" else f"y{'B' if pt == 'A' else 'A'}"


def _serie(r, eixo, chave, item, lado):
    anos = sorted(r)
    est = [r[a][eixo][_alvo(a, lado)][chave][item] for a in anos]
    reps = [[b[eixo][_alvo(a, lado)][chave][item] for b in r[a]["eixo1_4_boot"]] for a in anos]
    lo, hi = zip(*[np.percentile(x, [5, 95]) for x in reps])
    return anos, np.array(est), np.array(lo), np.array(hi)


def _painel_series(r, eixo, chave, itens: dict, ylabel, nome):
    fig, axs = plt.subplots(1, 2, figsize=(6.3, 2.7), sharey=True)
    for ax, lado in zip(axs, ("PT", "Adversário")):
        for k, (item, rot) in enumerate(itens.items()):
            anos, est, lo, hi = _serie(r, eixo, chave, item, lado)
            ax.fill_between(anos, lo, hi, color=CORES[k], alpha=0.15, lw=0)
            ax.plot(anos, est, color=CORES[k], marker=MARC[k], ms=4.5, label=rot)
            ax.annotate(rot, (anos[-1], est[-1]), xytext=(5, 0), textcoords="offset points",
                        va="center", fontsize=7.5, color=TINTA)
        ax.set_title(lado, fontsize=9, color=TINTA, loc="left")
        ax.set_xticks(anos)
        ax.set_xlim(anos[0] - 0.5, anos[-1] + 4.5)
    axs[0].set_ylabel(ylabel)
    axs[1].legend(frameon=False, fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(SAIDA / nome)
    plt.close(fig)


def fig_fronteira(r, x):
    anos = sorted(r)
    fig, axs = plt.subplots(1, len(anos), figsize=(6.3, 2.2), sharey=True)
    for ax, a in zip(np.atleast_1d(axs), anos):
        pl = np.array(x[a]["placebos_aleatorios"])
        ax.hist(pl, bins=20, color=CORES[0], alpha=0.55, edgecolor="white", lw=0.5)
        real = r[a]["fronteira_pp"]["real"]
        ax.axvline(real, color=CORES[1], lw=2)
        ax.annotate(f"divisas\nestaduais\n{real:.1f}".replace(".", ","), (real, ax.get_ylim()[1] * 0.95),
                    xytext=(-4, 0), textcoords="offset points", ha="right", va="top", fontsize=7, color=TINTA)
        ax.set_title(str(a), fontsize=9, color=TINTA, loc="left")
        ax.set_xlabel("salto quadrático médio (p.p.)")
    np.atleast_1d(axs)[0].set_ylabel("linhas-placebo")
    fig.tight_layout()
    fig.savefig(SAIDA / "fig_fronteira.pdf")
    plt.close(fig)


def fig_coeficientes(x):
    anos = sorted(x)
    fig, ax = plt.subplots(figsize=(6.3, 3.2))
    nomes = list(COVS)
    ys = np.arange(len(nomes))[::-1]
    for k, a in enumerate(anos):
        est = np.array([x[a]["coeficientes"][c] for c in nomes])
        boot = np.array([[b[c] for c in nomes] for b in x[a]["coeficientes_boot"]])
        lo, hi = np.percentile(boot, [5, 95], axis=0)
        dy = (k - (len(anos) - 1) / 2) * 0.22
        ax.errorbar(est, ys + dy, xerr=[est - lo, hi - est], fmt=MARC[k], color=CORES[k], ms=4.5,
                    elinewidth=1.2, capsize=0, label=str(a))
    ax.axvline(0, color=TINTA2, lw=0.8)
    ax.set_yticks(ys, [COVS[c] for c in nomes])
    ax.set_xlabel("coeficiente padronizado no voto no PT (logit; modelo completo)")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(SAIDA / "fig_coeficientes.pdf")
    plt.close(fig)


def fig_mapa_uf(x):
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    from geovoto.espacial import malha
    ufs = malha()[["SIGLA_UF", "geometry"]].dissolve("SIGLA_UF").simplify(2000)
    cmap = LinearSegmentedColormap.from_list("div", ["#eb6834", "#f0efec", "#2a78d6"])
    anos = sorted(x)
    lim = max(abs(v) for a in anos for v in x[a]["efeitos_uf_pp"].values())
    fig, axs = plt.subplots(1, len(anos), figsize=(6.3, 2.6))
    for ax, a in zip(np.atleast_1d(axs), anos):
        g = pd.Series(x[a]["efeitos_uf_pp"])
        geo = ufs.to_frame("geometry").assign(v=g.reindex(ufs.index).to_numpy())
        geo.plot(column="v", cmap=cmap, norm=TwoSlopeNorm(0, -lim, lim), ax=ax, edgecolor="white", linewidth=0.4)
        ax.set_title(str(a), fontsize=9, color=TINTA, loc="left")
        ax.set_axis_off()
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=TwoSlopeNorm(0, -lim, lim))
    cb = fig.colorbar(sm, ax=axs, orientation="horizontal", fraction=0.05, pad=0.02, aspect=40)
    cb.set_label("efeito da UF no voto no PT, dada a estrutura social (p.p.)")
    cb.outline.set_visible(False)
    fig.savefig(SAIDA / "fig_mapa_uf.pdf", bbox_inches="tight")
    plt.close(fig)


def gerar() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    r, x = _carregar()
    _painel_series(r, "eixo1", "shapley", BLOCOS, "parcela do $R^2$ (Shapley)", "fig_shapley.pdf")
    _painel_series(r, "eixo4", "unicos", DIMS, "parcela única do $R^2$", "fig_dimensoes.pdf")
    if x:
        fig_fronteira(r, x)
        fig_coeficientes(x)
        fig_mapa_uf(x)
    print("figuras em", SAIDA)


if __name__ == "__main__":
    gerar()
