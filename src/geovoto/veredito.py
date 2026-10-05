"""Aplica mecanicamente os critérios de HIPOTESES.md a data/output/eixos/resultados.json.

Cada função recebe o dicionário {ano: resultados} produzido por geovoto.eixos.rodar e devolve
{tese: (veredito, estimativa, IC90 inferior, IC90 superior)}. Nenhum limiar aqui pode mudar
depois da tag prereg-v1 (mudanças entram na seção "Desvios" do pré-registro).
"""
import json

import numpy as np

from geovoto import ROOT

LIMIAR_TENDENCIA = 0.05   # T1, eixo 2, eixo 4: +5 p.p. (fração de R² ou de variância)
LIMIAR_FRONTEIRA = 3.0    # T2: p.p. de s_A
LIMIAR_ISOLAMENTO = 0.05  # eixo 3
IC = (5, 95)              # IC90%


def _ic(x) -> tuple[float, float, float]:
    lo, hi = np.percentile(x, IC)
    return float(np.median(x)), float(lo), float(hi)


def tendencia(reps_por_ano: dict) -> tuple[float, float, float]:
    """Variação total implícita na tendência linear (inclinação × período), com IC90% por réplica."""
    anos = np.array(sorted(reps_por_ano), float)
    R = np.array([np.asarray(reps_por_ano[a], float) for a in sorted(reps_por_ano)])  # anos × réplicas
    x = anos - anos.mean()
    incl = (x[:, None] * (R - R.mean(0))).sum(0) / (x**2).sum()
    return _ic(incl * (anos[-1] - anos[0]))


def _aumento(est, lo, limiar) -> str:
    if est >= limiar and lo > 0:
        return "suportada"
    return "refutada" if lo <= 0 else "inconclusiva"


def veredito_eixo1(r: dict) -> dict:
    out = {}
    for alvo in ("yA", "yB"):
        reps = {a: [b["eixo1"][alvo]["shapley"]["estrutura"] for b in r[a]["eixo1_4_boot"]] for a in r}
        out[f"T1 estruturação ({alvo})"] = classifica_t1(reps)
    pri, ult = min(r), max(r)
    dif = lambda a: np.array([b["real"] - b["placebo"] for b in r[a]["fronteira_boot"]])
    out["T2 território (real − placebo, p.p.)"] = classifica_t2(dif(ult), dif(pri))
    return out


def classifica_t1(reps_por_ano: dict) -> tuple:
    est, lo, hi = tendencia(reps_por_ano)
    return _aumento(est, lo, LIMIAR_TENDENCIA), est, lo, hi


def classifica_t2(dif_ult: np.ndarray, dif_pri: np.ndarray) -> tuple:
    """dif_* = réplicas de (salto real − placebo) no último e no primeiro ano."""
    est, lo, hi = _ic(dif_ult)
    _, _, queda_hi = _ic(dif_ult - dif_pri)
    if -LIMIAR_FRONTEIRA <= lo and hi <= LIMIAR_FRONTEIRA:
        v = "refutada"
    elif est >= LIMIAR_FRONTEIRA and queda_hi >= 0:      # sem queda significativa desde o 1º ano
        v = "suportada"
    else:
        v = "inconclusiva"
    return v, est, lo, hi


def veredito_eixo2(r: dict) -> dict:
    pri, ult = min(r), max(r)
    boot = lambda a, ks: sum(np.array(r[a]["eixo2_boot"][k]) for k in ks)
    out = {}
    for nome, ks in (("entre lugares", ["parcela_uf", "parcela_municipio"]),
                     ("dentro dos lugares", ["parcela_local"])):
        est, lo, hi = _ic(boot(ult, ks) - boot(pri, ks))
        v = "cresceu" if est >= LIMIAR_TENDENCIA and lo > 0 else "estável ou caiu"
        out[f"Eixo 2 {nome} (Δ parcela)"] = (v, est, lo, hi)
    return out


def veredito_eixo3(r: dict) -> dict:
    pri, ult = min(r), max(r)
    out, meds = {}, []
    for b in "AB":
        d = np.array(r[ult]["eixo3_boot"][f"isolamento_{b}"]) - np.array(r[pri]["eixo3_boot"][f"isolamento_{b}"])
        est, lo, hi = _ic(d)
        meds.append(est)
        out[f"Eixo 3 Δ isolamento {b} (local)"] = ("", est, lo, hi)
    if all(m >= LIMIAR_ISOLAMENTO for m in meds):
        v = "separação"
    elif all(abs(m) <= LIMIAR_ISOLAMENTO for m in meds):
        v = "estabilidade"
    else:
        v = "misto: ver A e B"
    out["Eixo 3 veredito"] = (v, None, None, None)
    return out


def veredito_eixo4(r: dict) -> dict:
    out = {}
    anos = sorted(r)
    for alvo in ("yA", "yB"):
        unicos = {a: r[a]["eixo4"][alvo]["unicos"] for a in anos}
        renda_lider = all(max(u, key=u.get) == "economica" for u in unicos.values())
        deslocou = []
        for dim in unicos[anos[0]]:
            if dim == "economica":
                continue
            reps = {a: [b["eixo4"][alvo]["unicos"][dim] for b in r[a]["eixo1_4_boot"]] for a in anos}
            est, lo, _ = tendencia(reps)
            supera = any(unicos[a][dim] > unicos[a]["economica"] for a in anos[-2:])
            if est >= LIMIAR_TENDENCIA and lo > 0 and supera:
                deslocou.append(dim)
        v = ("deslocamento: " + ", ".join(deslocou)) if deslocou else (
            "renda lidera" if renda_lider else "nenhuma das duas")
        out[f"T4 ({alvo})"] = (v, None, None, None)
    return out


def veredito(r: dict) -> dict:
    r = {int(a): v for a, v in r.items() if not str(a).startswith("_")}
    return veredito_eixo1(r) | veredito_eixo2(r) | veredito_eixo3(r) | veredito_eixo4(r)


def markdown(v: dict) -> str:
    fmt = lambda x: "" if x is None else f"{x:+.3f}"
    linhas = ["| Tese | Veredito | Estimativa | IC90% inf. | IC90% sup. |", "|---|---|---|---|---|"]
    linhas += [f"| {k} | {t[0]} | {fmt(t[1])} | {fmt(t[2])} | {fmt(t[3])} |" for k, t in v.items()]
    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    pasta = ROOT / "data" / "output" / "eixos"
    v = veredito(json.loads((pasta / "resultados.json").read_text()))
    (pasta / "veredito.md").write_text(markdown(v))
    print(markdown(v))
