"""Previsão municipal do 2º turno a partir do 1º turno (alvos neutros: abstenção e |margem|).

Margem (estrutural): os votos dos demais candidatos (O) se dividem com fração π para A,
    s_A2 = (A1 + π·O1) / (A1 + B1 + O1),   π_i = π_nacional + ruído local,
com π_nacional incerto (priori a partir das eleições de treino) e ruído local em logit
com variância τ² + κ²·o1² (mais incerteza onde os demais tiveram mais votos).
Abstenção: logit(ab2) = logit(ab1) + c_nacional + δ_município + ε, com δ = média histórica
do município encolhida para a da UF.
Baseline pré-registrado: abstenção_1T + Δ médio histórico da UF; transferências proporcionais
(s_A2 = s_A1 entre A e B).
"""
from pathlib import Path

import numpy as np
import pandas as pd

from geovoto import CONFIG, PROCESSED, ROOT

PI_SD_MIN = 0.10   # piso da escala de π nacional (só 2–3 eleições para estimar)
C_SD_MIN = 0.05    # piso da incerteza do deslocamento nacional da abstenção (logit)
QS = [0.025, 0.10, 0.50, 0.90, 0.975]


def logit(x):
    return np.log(x / (1 - x))


def expit(x):
    return 1 / (1 + np.exp(-x))


def primeiro_turno(df: pd.DataFrame) -> pd.DataFrame:
    """Variáveis do 1º turno usadas pelo modelo (df = linhas de turno 1)."""
    uf = df["sigla_uf"] if "sigla_uf" in df else df["uf"].str.upper()
    return pd.DataFrame({
        "ano": df.ano.values, "cd_municipio_tse": df.cd_municipio_tse.values,
        "uf": uf.values, "aptos": df.aptos.values,
        "A1": df.votos_A.values, "B1": df.votos_B.values,
        "O1": (df.validos - df.votos_A - df.votos_B).values,
        # apuração parcial (2026 provisório): abstenção só existe nas seções já totalizadas
        "ab1": (df.abstencoes / df.get("aptos_apurados", df.aptos)).values})


def pares(painel: pd.DataFrame) -> pd.DataFrame:
    k = ["ano", "cd_municipio_tse"]
    t1 = primeiro_turno(painel[painel.turno == 1])
    t2 = painel[painel.turno == 2].set_index(k)
    d = t1.set_index(k)
    d["A2"], d["B2"] = t2.votos_A, t2.votos_B
    d["sA2"] = t2.votos_A / (t2.votos_A + t2.votos_B)
    d["ab2"] = t2.abstencoes / t2.aptos
    return d.reset_index()


def pi_implicito(g: pd.DataFrame) -> float:
    """π nacional que reproduz a participação nacional de A no 2º turno (soma de votos)."""
    V = (g.A1 + g.B1 + g.O1).sum()
    sA2 = g.A2.sum() / (g.A2 + g.B2).sum()
    return float((sA2 * V - g.A1.sum()) / g.O1.sum())


def ajustar(treino: pd.DataFrame) -> dict:
    pis, cs, r2, o2, inv_n, ya = [], [], [], [], [], []
    for _, g in treino.groupby("ano"):
        pi = pi_implicito(g)
        pis.append(pi)
        pred = (g.A1 + pi * g.O1) / (g.A1 + g.B1 + g.O1)
        r2.append((logit(g.sA2) - logit(pred)) ** 2)
        o2.append((g.O1 / (g.A1 + g.B1 + g.O1)) ** 2)
        inv_n.append(1 / g.aptos)
        d = logit(g.ab2) - logit(g.ab1)
        cs.append(np.average(d, weights=g.aptos))
        ya.append(g.assign(ya=d - cs[-1])[["cd_municipio_tse", "uf", "ya"]])
    # variância local da margem: base + parte proporcional aos "demais" + parte de tamanho (1/aptos).
    # Sem ponderar: a cobertura é avaliada município a município.
    r2, o2, inv_n = map(np.concatenate, (r2, o2, inv_n))
    X = np.c_[np.ones_like(o2), o2, inv_n]
    tau2, kappa2, nu = np.clip(np.linalg.lstsq(X, r2, rcond=None)[0], 0, None)

    ya = pd.concat(ya)
    uf = ya.groupby("uf").ya.mean()
    m = ya.groupby("cd_municipio_tse").agg(uf=("uf", "first"), media=("ya", "mean"), n=("ya", "size"))
    resid = ya.ya - ya.cd_municipio_tse.map(m.media)
    var_dentro = float(np.mean(resid**2)) * len(ya) / max(len(ya) - len(m), 1)  # ruído por eleição
    var_entre = max(float(m.media.var()) - var_dentro / m.n.mean(), 1e-6)
    peso = var_entre / (var_entre + var_dentro / m.n)            # encolhimento empírico-bayesiano
    delta_mun = peso * m.media + (1 - peso) * m.uf.map(uf)
    # componentes nacionais: preditiva t com n−1 g.l. (poucas eleições), escala com piso
    escala = lambda xs, piso: max(float(np.std(xs, ddof=1)), piso) * np.sqrt(1 + 1 / len(xs))
    return {"pi_mu": float(np.mean(pis)), "pi_sd": escala(pis, PI_SD_MIN),
            "c_mu": float(np.mean(cs)), "c_sd": escala(cs, C_SD_MIN), "df": len(pis) - 1,
            "tau": float(np.sqrt(tau2)), "kappa": float(np.sqrt(kappa2)), "nu": float(nu),
            "eps_ab": float(np.sqrt(var_dentro)), "delta_mun": delta_mun, "delta_uf": uf}


def _nacional(rng, mu: float, escala: float, df: int, n: int, limite: float) -> np.ndarray:
    return mu + np.clip(escala * rng.standard_t(df, (n, 1)), -limite, limite)


def simular(t1: pd.DataFrame, par: dict, n: int = 2000, seed: int = CONFIG["seed"]) -> dict:
    rng = np.random.default_rng(seed)
    V = (t1.A1 + t1.B1 + t1.O1).to_numpy(float)
    o1 = t1.O1.to_numpy(float) / V
    pi = np.clip(_nacional(rng, par["pi_mu"], par["pi_sd"], par["df"], n, 0.5), 0, 1)
    base = (t1.A1.to_numpy(float) + pi * t1.O1.to_numpy(float)) / V
    sd_local = np.sqrt(par["tau"] ** 2 + par["kappa"] ** 2 * o1**2
                       + par["nu"] / t1.aptos.to_numpy(float))
    sA2 = expit(logit(np.clip(base, 1e-6, 1 - 1e-6)) + rng.normal(0, 1, base.shape) * sd_local)

    delta = t1.cd_municipio_tse.map(par["delta_mun"]).fillna(t1.uf.map(par["delta_uf"])).fillna(0)
    c = _nacional(rng, par["c_mu"], par["c_sd"], par["df"], n, 0.5)
    ab2 = expit(logit(t1.ab1.to_numpy(float)) + c + delta.to_numpy(float)
                + rng.normal(0, par["eps_ab"], (n, len(t1))))
    return {"abst": ab2, "margem_abs": np.abs(2 * sA2 - 1)}


def baseline(t1: pd.DataFrame, par: dict) -> dict:
    sA1 = t1.A1 / (t1.A1 + t1.B1)
    ab = expit(logit(t1.ab1) + par["c_mu"] + t1.uf.map(par["delta_uf"]).fillna(0))
    return {"abst": ab.to_numpy(), "margem_abs": np.abs(2 * sA1 - 1).to_numpy()}


def crps(amostras: np.ndarray, y: np.ndarray) -> np.ndarray:
    """CRPS empírico por coluna: E|X−y| − ½E|X−X'| (X' = permutação de X)."""
    x2 = np.random.default_rng(0).permutation(amostras, axis=0)
    return np.mean(np.abs(amostras - y), 0) - 0.5 * np.mean(np.abs(amostras - x2), 0)


def avaliar(sim: dict, base: dict, real: dict, w: np.ndarray) -> list[dict]:
    linhas = []
    for alvo in ["abst", "margem_abs"]:
        s, y = sim[alvo], real[alvo]
        q = np.quantile(s, QS, axis=0)
        linhas.append({
            "alvo": alvo,
            "mae_modelo_pp": 100 * np.average(np.abs(q[2] - y), weights=w),
            "mae_baseline_pp": 100 * np.average(np.abs(base[alvo] - y), weights=w),
            "crps_pp": 100 * np.average(crps(s, y), weights=w),
            "cobertura_80": np.mean((y >= q[1]) & (y <= q[3])),
            "cobertura_95": np.mean((y >= q[0]) & (y <= q[4]))})
    return linhas


def backtest(d: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for ano in sorted(d.ano.unique()):
        teste, par = d[d.ano == ano], ajustar(d[d.ano != ano])
        real = {"abst": teste.ab2.to_numpy(), "margem_abs": np.abs(2 * teste.sA2 - 1).to_numpy()}
        for r in avaliar(simular(teste, par), baseline(teste, par), real, teste.aptos.to_numpy()):
            linhas.append({"ano_teste": ano, **r})
    return pd.DataFrame(linhas)


def prever(t1_2026: pd.DataFrame, par: dict) -> pd.DataFrame:
    sem_dados = (t1_2026.A1 + t1_2026.B1 + t1_2026.O1 == 0) | t1_2026.ab1.isna()
    if sem_dados.any():
        print(f"AVISO: {sem_dados.sum()} município(s) sem seções apuradas no 1º turno: previsão vazia")
    t = t1_2026.assign(A1=t1_2026.A1.where(~sem_dados, 1), B1=t1_2026.B1.where(~sem_dados, 1),
                       ab1=t1_2026.ab1.where(~sem_dados, 0.5))   # valores neutros, descartados abaixo
    sim = {k: np.where(sem_dados.to_numpy(), np.nan, v) for k, v in simular(t, par).items()}
    out = t1_2026[["cd_municipio_tse"]].assign(sem_dados_1t=sem_dados.to_numpy())
    base = baseline(t, par)
    for alvo, s in sim.items():
        for q, v in zip(QS, np.nanquantile(s, QS, axis=0) if np.isnan(s).any() else np.quantile(s, QS, axis=0)):
            out[f"{alvo}_q{q * 100:g}"] = v.round(4)
        out[f"{alvo}_baseline"] = np.where(sem_dados, np.nan, base[alvo]).round(4)   # congelado junto
    return out


# ---------- publicação e avaliação (protocolo de HIPOTESES.md §6) ----------

PACOTE = ROOT / "reports" / "previsao_2T_2026"


def pacote(prev: pd.DataFrame, par: dict, bt: pd.DataFrame) -> Path:
    """Grava o pacote congelável: CSV, LEIAME (protocolo, parâmetros, backtest, proveniência) e hashes."""
    import hashlib
    import subprocess
    from datetime import datetime
    PACOTE.mkdir(parents=True, exist_ok=True)
    csv = PACOTE / "previsao_2T_2026.csv"
    prev.to_csv(csv, index=False)
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sujo = bool(git("status", "--porcelain", "--", "src", "config.toml"))
    params = {k: round(float(v), 4) for k, v in par.items() if np.isscalar(v)}
    leia = [
        "# Previsão municipal do 2º turno presidencial de 2026\n",
        f"- Gerado em: {datetime.now():%Y-%m-%d %H:%M} (horário local)",
        f"- Dados do 1º turno: sistema de divulgação do TSE, snapshot {prev.snapshot.max()} "
        f"({int((prev.pct_totalizado < 100).sum())} municípios abaixo de 100% apurados)",
        f"- Código: commit {git('rev-parse', 'HEAD')}{' (com alterações não commitadas!)' if sujo else ''}",
        "- Alvos: abstenção no 2º turno (abstenções ÷ aptos) e |margem| = |votos do 1º − do 2º colocado do "
        "1º turno| ÷ válidos do 2º turno. Sem nomes e sem sinal.",
        "- Colunas `_q2.5 … _q97.5`: quantis da distribuição prevista; `_baseline`: regra simples "
        "pré-registrada (HIPOTESES.md §6), congelada aqui para a comparação.",
        "- Avaliação pré-escrita: `python -m geovoto.previsao avaliar` (MAE ponderado por aptos contra o "
        "baseline, perda pinball média nos quantis e cobertura dos intervalos de 80% e 95%).\n",
        "## Parâmetros estimados\n", "| Parâmetro | Valor |", "|---|---|",
        *[f"| {k} | {v} |" for k, v in params.items()], "",
        "## Backtest (cada eleição prevista com as outras duas)\n",
        "| Ano | Alvo | MAE modelo (p.p.) | MAE baseline (p.p.) | Cobertura 80% | Cobertura 95% |", "|---|---|---|---|---|---|",
        *[f"| {r.ano_teste} | {r.alvo} | {r.mae_modelo_pp:.2f} | {r.mae_baseline_pp:.2f} | {r.cobertura_80:.2f} | "
          f"{r.cobertura_95:.2f} |" for r in bt.itertuples()], "",
    ]
    (PACOTE / "LEIAME.md").write_text("\n".join(leia) + "\n")
    hashes = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in (csv, PACOTE / "LEIAME.md")]
    (PACOTE / "SHA256SUMS").write_text("\n".join(hashes) + "\n")
    return PACOTE


def pinball(quantis: dict, y: np.ndarray, w: np.ndarray) -> float:
    """Perda pinball média sobre os quantis publicados (aproxima o CRPS), ponderada por w."""
    perdas = [np.average(np.maximum(q * (y - v), (q - 1) * (y - v)), weights=w) for q, v in quantis.items()]
    return float(np.mean(perdas))


def avaliar_previsao(prev: pd.DataFrame, real: pd.DataFrame) -> pd.DataFrame:
    """prev: CSV do pacote; real: painel do 2º turno (votos_A, votos_B, abstencoes, aptos_apurados,
    pct_totalizado). Só municípios 100% apurados e com previsão entram."""
    r = real[real.pct_totalizado >= 100].assign(
        abst=lambda x: x.abstencoes / x.aptos_apurados,
        margem_abs=lambda x: (x.votos_A - x.votos_B).abs() / (x.votos_A + x.votos_B))
    m = prev.merge(r[["cd_municipio_tse", "abst", "margem_abs", "aptos_apurados"]], on="cd_municipio_tse",
                   suffixes=("", "_real"))
    m = m[~m.sem_dados_1t]
    w = m.aptos_apurados.to_numpy(float)
    linhas = []
    for alvo in ("abst", "margem_abs"):
        y = m[alvo + "_real" if alvo + "_real" in m else alvo].to_numpy(float)
        q = {qq: m[f"{alvo}_q{qq * 100:g}"].to_numpy(float) for qq in QS}
        linhas.append({
            "alvo": alvo, "n": len(m),
            "mae_modelo_pp": 100 * np.average(np.abs(q[0.5] - y), weights=w),
            "mae_baseline_pp": 100 * np.average(np.abs(m[f"{alvo}_baseline"].to_numpy(float) - y), weights=w),
            "pinball_pp": 100 * pinball(q, y, w),
            "cobertura_80": float(np.mean((y >= q[0.1]) & (y <= q[0.9]))),
            "cobertura_95": float(np.mean((y >= q[0.025]) & (y <= q[0.975])))})
    return pd.DataFrame(linhas)


def _avaliar_cli() -> None:
    prev = pd.read_csv(PACOTE / "previsao_2T_2026.csv")
    real = pd.read_parquet(PROCESSED / "painel_2026_t2_provisorio.parquet")
    av = avaliar_previsao(prev, real)
    linhas = ["# Avaliação da previsão do 2º turno de 2026\n",
              f"Pacote avaliado: `{PACOTE}` (confira `SHA256SUMS`). Resultado: snapshot {real.snapshot.max()}.\n",
              "| Alvo | n | MAE modelo | MAE baseline | Pinball | Cobertura 80% | Cobertura 95% |", "|---|---|---|---|---|---|---|",
              *[f"| {r.alvo} | {r.n} | {r.mae_modelo_pp:.2f} | {r.mae_baseline_pp:.2f} | {r.pinball_pp:.3f} | "
                f"{r.cobertura_80:.2f} | {r.cobertura_95:.2f} |" for r in av.itertuples()]]
    (PACOTE / "AVALIACAO.md").write_text("\n".join(linhas) + "\n")
    print("\n".join(linhas))


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["avaliar"]:
        _avaliar_cli()
        sys.exit()
    d = pares(pd.read_parquet(PROCESSED / "painel_presidente.parquet"))
    bt = backtest(d)
    bt.to_csv(PROCESSED / "backtest.csv", index=False)
    print(bt.round(3).to_string(index=False))
    f = PROCESSED / "painel_2026_t1_provisorio.parquet"
    if f.exists():
        p26 = pd.read_parquet(f)
        par = ajustar(d)
        prev = prever(primeiro_turno(p26), par).merge(
            p26[["cd_municipio_tse", "cd_municipio_ibge", "pct_totalizado", "snapshot"]], on="cd_municipio_tse")
        prev.to_csv(PROCESSED / "previsao_2T_2026.csv", index=False)
        if sys.argv[1:] == ["pacote"]:
            print("pacote em", pacote(prev, par, bt))
        print({k: round(v, 4) for k, v in par.items() if isinstance(v, float)})
        print(prev.drop(columns=["snapshot"]).describe().T[["mean", "min", "max"]].round(3))
