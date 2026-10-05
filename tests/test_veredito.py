"""Critérios do pré-registro aplicados a resultados CONSTRUÍDOS À MÃO (respostas conhecidas)."""
import numpy as np

from geovoto.veredito import veredito

DIMS = ["economica", "educacional", "religiosa", "demografica", "cor_raca"]


def _resultados(estrutura, salto, local, iso, educ):
    """estrutura/local/iso/educ: valor por ano; salto: salto corrigido (p.p.) por ano."""
    rng = np.random.default_rng(0)
    ru = lambda m, n=200, sd=0.01: list(m + rng.normal(0, sd, n))
    r = {}
    for k, ano in enumerate([2014, 2018, 2022]):
        un = {d: 0.02 for d in DIMS} | {"economica": 0.10, "educacional": educ[k]}
        boot = [{e: {a: {"shapley": {"estrutura": estrutura[k] + rng.normal(0, 0.01)},
                         "unicos": {d: v + rng.normal(0, 0.005) for d, v in un.items()},
                         "compartilhado": 0.1} for a in ("yA", "yB")} for e in ("eixo1", "eixo4")}
                for _ in range(200)]
        r[ano] = {"eixo1_4_boot": boot,
                  "fronteira_boot": [{"real": salto[k] + rng.normal(0, 0.3), "placebo": rng.normal(0, 0.3)}
                                     for _ in range(200)],
                  "eixo2_boot": {"parcela_uf": ru(0.5 - local[k]), "parcela_municipio": ru(0.3),
                                 "parcela_local": ru(0.2 + local[k])},
                  "eixo3_boot": {"isolamento_A": ru(0.5 + iso[k]), "isolamento_B": ru(0.5 + iso[k])},
                  "eixo4": {a: {"unicos": un} for a in ("yA", "yB")}}
    return r


def test_tudo_suportado():
    v = veredito(_resultados([.1, .2, .3], [5, 5, 5], [0, .05, .1], [0, .05, .1], [.02, .08, .15]))
    assert v["T1 estruturação (yA)"][0] == "suportada"
    assert v["T2 território (salto corrigido, p.p.)"][0] == "suportada"
    assert v["T2 placebo (validação)"][0] == "ok"
    assert v["Eixo 2 dentro dos lugares (Δ parcela)"][0] == "cresceu"
    assert v["Eixo 3 veredito"][0] == "separação"
    assert v["T4 (yA)"][0] == "deslocamento: educacional"


def test_tudo_nulo():
    v = veredito(_resultados([.2, .2, .2], [0, 0, 0], [0, 0, 0], [0, 0, 0], [.02, .02, .02]))
    assert v["T1 estruturação (yA)"][0] == "refutada"
    assert v["T2 território (salto corrigido, p.p.)"][0] == "refutada"
    assert v["Eixo 2 entre lugares (Δ parcela)"][0] == "estável ou caiu"
    assert v["Eixo 3 veredito"][0] == "estabilidade"
    assert v["T4 (yA)"][0] == "renda lidera"
