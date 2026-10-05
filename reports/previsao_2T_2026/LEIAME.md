# Previsão municipal do 2º turno presidencial de 2026

- Gerado em: 2026-10-05 15:42 (horário local)
- Dados do 1º turno: sistema de divulgação do TSE, snapshot 05/10/2026 12:53:07 (0 municípios abaixo de 100% apurados)
- Código: commit 1d54a581f7845a327758fec80c453b7bc95e88f0
- Alvos: abstenção no 2º turno (abstenções ÷ aptos) e |margem| = |votos do 1º − do 2º colocado do 1º turno| ÷ válidos do 2º turno. Sem nomes e sem sinal.
- Colunas `_q2.5 … _q97.5`: quantis da distribuição prevista; `_baseline`: regra simples pré-registrada (HIPOTESES.md §6), congelada aqui para a comparação.
- Avaliação pré-escrita: `python -m geovoto.previsao avaliar` (MAE ponderado por aptos contra o baseline, perda pinball média nos quantis e cobertura dos intervalos de 80% e 95%).

## Parâmetros estimados

| Parâmetro | Valor |
|---|---|
| pi_mu | 0.356 |
| pi_sd | 0.1155 |
| c_mu | 0.0472 |
| c_sd | 0.0771 |
| df | 2.0 |
| tau | 0.0 |
| kappa | 1.009 |
| nu | 27.2533 |
| eps_ab | 0.0699 |

## Backtest (cada eleição prevista com as outras duas)

| Ano | Alvo | MAE modelo (p.p.) | MAE baseline (p.p.) | Cobertura 80% | Cobertura 95% |
|---|---|---|---|---|---|
| 2014 | abst | 1.44 | 1.40 | 0.97 | 1.00 |
| 2014 | margem_abs | 6.15 | 7.66 | 0.90 | 0.97 |
| 2018 | abst | 0.68 | 0.87 | 1.00 | 1.00 |
| 2018 | margem_abs | 5.61 | 13.17 | 0.96 | 0.99 |
| 2022 | abst | 1.94 | 2.28 | 0.89 | 1.00 |
| 2022 | margem_abs | 2.00 | 3.30 | 0.96 | 0.99 |

