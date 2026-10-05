# legacy/ — NÃO USAR COMO EVIDÊNCIA

Código e saídas da versão anterior, mantidos só como referência.

- `notebooks/gerar_dados_reais.py` e `notebooks/02_03_testes_avancados.py` geram variáveis
  **sintéticas** (`np.random`): `idhm`, `coronelismo_idx`, `pedersen`, `var_renda_real`,
  `taxa_desemprego`, `voto_vizinhanca_lag`, `voto_incumbente`.
- Todos os modelos, coeficientes e mapas em `legacy/data/` derivam desses dados e
  apenas recuperam os parâmetros embutidos no gerador. Não são resultados empíricos.
- A pipeline nova está em `src/geovoto/` (ver `PLAN.md`).
